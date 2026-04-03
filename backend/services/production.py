"""
services/production.py
======================
Production resolution engine.

Scope: raw materials → finished components only.
No drone assembly happens here — assembly is a sales-phase decision.

resolve_production(db, team, cycle, rng)
    1. Load PENDING production-phase Events.
    2. Apply team-wide event effects (strike, poach, skilled labour).
    3. Apply per-component event effects (machine sabotage, infra delay,
       fast-track, R&D sabotage/investment).
    4. Per component:
         a. Optionally buy a new machine (buy_machine decision).
         b. Apply maintenance to all active machines of this component.
         c. Degrade all active machines.
         d. Compute total throughput and effective output parameters.
         e. Consume raw_stock up to units_to_produce (player-chosen, clamped).
         f. Draw finished component output array.
         g. Merge into ComponentSlot.finished_stock.
    5. Deduct wages and maintenance costs.
    6. Mark all consumed events APPLIED.

seed_production_memory(db, team)
seed_machine(db, team, slot, tier, cycle_number, source)
    Seeding helpers called by cycle_service.add_team().
"""
import math
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from core.config import (
    AUTOMATION_LABOUR_MULT, AUTOMATION_SIGMA_MULT,
    AUTOMATION_UPGRADE_COST, BASE_SIGMA,
    CONDITION_GRADE_EXPONENT, MACHINE_MAX_CONDITION,
    MACHINE_TIERS, MAINTENANCE_COST, MAINTENANCE_DEGRADE_MULT,
    MAX_RND_LEVEL, MORALE_HIGH, MORALE_LOW, MORALE_RIOT,
    OVERHAUL_RECOVERY_CAP, QUALITY_MAX,
    RND_CONSISTENCY_BONUS, RND_CYCLES_PER_LEVEL,
    RND_QUALITY_BONUS, RND_YIELD_BONUS,
    RIOT_SURVIVAL, RM_WEIGHT, SKILL_GAIN_HIGH_MORALE,
    SKILL_GAIN_LOW_MORALE, SKILL_SIGMA_REDUCTION,
    STRIKE_SURVIVAL, UNDERSTAFFING_MORALE_PENALTY,
    WAGE_COST_PER_WORKER, WAGE_MORALE_DELTA,
    AUTOMATION_UPGRADE_COST,
)
from core.enums import (
    AutomationLevel, ComponentType,
    EventPhase, EventStatus, EventType,
)
from models.deals import Event
from models.game import Cycle, Game
from models.production import MemoryProduction
from models.procurement import ComponentSlot, Inventory, Machine


# ── Seeding ───────────────────────────────────────────────────────────────────

def seed_production_memory(db: Session, team) -> MemoryProduction:
    """Create MemoryProduction with safe defaults for a new team."""
    default_decisions: Dict = {
        "wage_level":         "market",
        "target_headcount":   50,
        "upgrade_automation": None,
    }
    for comp in ComponentType:
        default_decisions[comp.value] = {
            "maintenance":      "none",
            "units_to_produce": None,   # None = use max throughput
            "rnd_invest":       None,
            "buy_machine":      None,
        }
    mem = MemoryProduction(team_id=team.id, decisions=default_decisions)
    db.add(mem)
    db.flush()
    return mem


def seed_machine(
    db:           Session,
    team,
    slot:         ComponentSlot,
    tier:         str         = "standard",
    cycle_number: int         = 0,
    source:       str         = "seed",
) -> Machine:
    """Create one Machine row. Called by add_team (one per component) and auction."""
    machine = Machine(
        team_id         = team.id,
        slot_id         = slot.id,
        component       = slot.component,
        tier            = tier,
        condition       = MACHINE_MAX_CONDITION,
        is_active       = True,
        purchased_cycle = cycle_number,
        source          = source,
    )
    db.add(machine)
    db.flush()
    return machine


# ── Event loading ─────────────────────────────────────────────────────────────

def _load_production_events(
    db: Session, team_id: int, cycle_id: int
) -> List[Event]:
    return (
        db.query(Event)
        .filter(
            Event.cycle_id       == cycle_id,
            Event.target_team_id == team_id,
            Event.phase          == EventPhase.PRODUCTION,
            Event.status         == EventStatus.PENDING,
        )
        .all()
    )


def _mark_applied(events: List[Event]) -> None:
    now = datetime.utcnow()
    for ev in events:
        ev.status     = EventStatus.APPLIED
        ev.applied_at = now


# ── Machine helpers ───────────────────────────────────────────────────────────

def get_active_machines(
    db: Session, team_id: int, component: str
) -> List[Machine]:
    """Return all active Machine rows for a team+component, ordered by id."""
    return (
        db.query(Machine)
        .filter(
            Machine.team_id   == team_id,
            Machine.component == component,
            Machine.is_active == True,
        )
        .order_by(Machine.id)
        .all()
    )


def total_throughput(machines: List[Machine]) -> int:
    """Sum the throughput of all active machines."""
    return sum(
        MACHINE_TIERS.get(m.tier, MACHINE_TIERS["standard"])["throughput"]
        for m in machines
    )


def _effective_grade_for_machines(
    machines:       List[Machine],
    rnd_quality:    int,
) -> float:
    """
    Weighted average effective output grade across all active machines.
    Weight = throughput of each machine (higher throughput machines
    contribute more to the blended grade).

    effective_grade = Σ(throughput_i × base_grade_i × condition_factor_i) / Σthroughput_i
    Then add R&D quality bonus on top.
    """
    total_tp   = 0
    grade_sum  = 0.0

    for m in machines:
        cfg = MACHINE_TIERS.get(m.tier, MACHINE_TIERS["standard"])
        tp  = cfg["throughput"]
        factor = (m.condition / MACHINE_MAX_CONDITION) ** CONDITION_GRADE_EXPONENT
        grade_sum += tp * cfg["grade"] * factor
        total_tp  += tp

    base = grade_sum / total_tp if total_tp > 0 else 0.0
    return base + rnd_quality * RND_QUALITY_BONUS


def _compute_sigma(
    automation_level: str,
    skill:            float,
    rnd_consistency:  int,
) -> float:
    sigma = BASE_SIGMA * AUTOMATION_SIGMA_MULT.get(automation_level, 1.0)
    skill_factor = max(0.1, min(1.0, skill / 100.0))
    sigma *= (1.0 - skill_factor * SKILL_SIGMA_REDUCTION)
    sigma -= rnd_consistency * RND_CONSISTENCY_BONUS
    return max(2.0, sigma)


def _apply_maintenance_and_degrade(
    machines:    List[Machine],
    maintenance: str,
) -> float:
    """
    Apply one maintenance level to ALL machines of a component uniformly.
    Returns total maintenance cost for this component.
    """
    maint_cost_per_machine = MAINTENANCE_COST.get(maintenance, 0.0)
    degrade_mult           = MAINTENANCE_DEGRADE_MULT.get(maintenance, 1.0)
    total_cost             = 0.0

    for m in machines:
        cfg        = MACHINE_TIERS.get(m.tier, MACHINE_TIERS["standard"])
        degrade    = cfg["degrade"] * degrade_mult
        total_cost += maint_cost_per_machine

        if maintenance == "overhaul":
            recovery    = min(OVERHAUL_RECOVERY_CAP,
                              MACHINE_MAX_CONDITION - m.condition)
            m.condition = min(MACHINE_MAX_CONDITION, m.condition + recovery)
        else:
            m.condition = max(0.0, m.condition - degrade)
            if m.condition <= 0.0:
                m.is_active = False   # Machine destroyed

    return total_cost


# ── Stock consumption ─────────────────────────────────────────────────────────

def _consume_raw_stock(
    raw_stock:       List[int],
    units_needed:    int,
    yield_reduction: float,
) -> Tuple[List[int], int, float]:
    """Pull units from raw_stock. Returns (updated_stock, consumed, rm_mean)."""
    effective_needed = max(1, int(units_needed * (1.0 - yield_reduction)))
    total_available  = sum(raw_stock[1:])
    to_consume       = min(effective_needed, total_available)

    updated   = list(raw_stock)
    consumed  = 0
    grade_sum = 0.0

    for g in range(QUALITY_MAX, 0, -1):
        if consumed >= to_consume:
            break
        take        = min(updated[g], to_consume - consumed)
        updated[g] -= take
        grade_sum   += take * g
        consumed    += take

    rm_mean = grade_sum / consumed if consumed > 0 else 0.0
    return updated, consumed, rm_mean


def _draw_component_array(
    mean:  float,
    sigma: float,
    count: int,
    rng:   np.random.Generator,
) -> List[int]:
    if count <= 0:
        return [0] * 101
    draws = rng.normal(loc=mean, scale=max(0.5, sigma), size=count)
    arr   = [0] * 101
    for v in draws:
        g = int(np.clip(v, 0, QUALITY_MAX))
        arr[g] += 1
    arr[0] += arr[0]
    return arr


def _required_labour(
    slots:            Dict[str, ComponentSlot],
    all_machines:     Dict[str, List[Machine]],
    automation_level: str,
) -> int:
    """Total headcount required across all components."""
    total = 0
    for comp_val, machines in all_machines.items():
        for m in machines:
            cfg    = MACHINE_TIERS.get(m.tier, MACHINE_TIERS["standard"])
            labour = cfg["labour"]
            mult   = AUTOMATION_LABOUR_MULT.get(automation_level, 1.0)
            total += int(labour * mult)
    return total


# ── Main resolution ───────────────────────────────────────────────────────────

def resolve_production(
    db:    Session,
    team,
    cycle: Cycle,
    rng:   Optional[np.random.Generator] = None,
) -> Dict:
    """
    Full production resolution for one team.
    Converts raw materials → finished components.
    Does NOT assemble drones — that happens in sales resolution.
    """
    if rng is None:
        rng = np.random.default_rng()

    mem: MemoryProduction = (
        db.query(MemoryProduction)
        .filter(MemoryProduction.team_id == team.id)
        .first()
    )
    decisions = mem.decisions if mem else {}

    inventory: Inventory = (
        db.query(Inventory).filter(Inventory.team_id == team.id).first()
    )
    if inventory is None:
        return {}

    slots: Dict[str, ComponentSlot] = {
        s.component.value: s
        for s in db.query(ComponentSlot)
        .filter(ComponentSlot.team_id == team.id)
        .all()
    }

    # Load all active machines grouped by component
    all_machines: Dict[str, List[Machine]] = {
        comp_val: get_active_machines(db, team.id, comp_val)
        for comp_val in slots
    }

    # ── Load production events ────────────────────────────────────────────────
    events = _load_production_events(db, team.id, cycle.id)

    # ── Automation level ──────────────────────────────────────────────────────
    automation_level = (
        inventory.automation_level.value
        if hasattr(inventory.automation_level, "value")
        else str(inventory.automation_level)
    )

    # ── Automation upgrade ────────────────────────────────────────────────────
    upgrade_auto = decisions.get("upgrade_automation")
    if upgrade_auto and upgrade_auto != automation_level:
        cost = AUTOMATION_UPGRADE_COST.get(upgrade_auto, 0.0)
        inventory.funds -= cost
        inventory.automation_level = AutomationLevel(upgrade_auto)
        automation_level = upgrade_auto

    # ── Team-wide event effects ───────────────────────────────────────────────
    production_survival = 1.0
    forced_strike       = False
    infra_delayed_comps: set = set()

    for ev in events:
        p = ev.payload or {}

        if ev.event_type == EventType.LABOUR_STRIKE:
            forced_strike       = True
            production_survival = STRIKE_SURVIVAL

        elif ev.event_type == EventType.LABOUR_POACH:
            inventory.skill_level = max(
                0.0, inventory.skill_level - p.get("skill_hit", 0.0)
            )

        elif ev.event_type == EventType.SKILLED_LABOUR:
            inventory.skill_level = min(
                100.0, inventory.skill_level + p.get("skill_bonus", 0.0)
            )

        elif ev.event_type == EventType.INFRA_DELAY:
            comp = p.get("component")
            if comp:
                infra_delayed_comps.add(comp)
            else:
                infra_delayed_comps.update(slots.keys())

        elif ev.event_type == EventType.RND_SABOTAGE:
            comp   = p.get("component")
            focus  = p.get("focus")
            levels = p.get("levels_stolen", 1)
            if comp and focus and comp in slots:
                attr = f"rnd_{focus}"
                setattr(slots[comp], attr,
                        max(0, getattr(slots[comp], attr) - levels))

        elif ev.event_type == EventType.RND_INVESTMENT:
            comp   = p.get("component")
            focus  = p.get("focus")
            levels = p.get("level_arriving", 1)
            if comp and focus and comp in slots:
                attr = f"rnd_{focus}"
                setattr(slots[comp], attr,
                        min(MAX_RND_LEVEL, getattr(slots[comp], attr) + levels))

    # ── Labour update ─────────────────────────────────────────────────────────
    target_headcount         = decisions.get("target_headcount", inventory.workforce_size)
    wage_level               = decisions.get("wage_level", "market")
    inventory.workforce_size = max(0, target_headcount)

    required_labour = _required_labour(slots, all_machines, automation_level)
    actual_labour   = inventory.workforce_size

    morale_delta = WAGE_MORALE_DELTA.get(wage_level, 0.0)
    if required_labour > 0 and actual_labour < required_labour:
        understaffed_pct  = (required_labour - actual_labour) / required_labour * 100
        morale_delta     -= understaffed_pct * UNDERSTAFFING_MORALE_PENALTY

    inventory.morale = max(0.0, min(100.0, inventory.morale + morale_delta))

    if not forced_strike and inventory.morale <= MORALE_RIOT:
        production_survival = RIOT_SURVIVAL

    if inventory.morale >= MORALE_HIGH:
        inventory.skill_level = min(
            100.0, inventory.skill_level + SKILL_GAIN_HIGH_MORALE
        )
    elif inventory.morale <= MORALE_LOW:
        inventory.skill_level = max(
            0.0, inventory.skill_level + SKILL_GAIN_LOW_MORALE
        )

    # ── Labour efficiency factor (affects throughput when understaffed) ───────
    labour_factor = 1.0
    if required_labour > 0 and actual_labour < required_labour:
        labour_factor = actual_labour / required_labour

    # ── Per-component processing ──────────────────────────────────────────────
    component_summaries: Dict = {}
    total_maint_cost    = 0.0

    for comp_val, slot in slots.items():
        comp_decisions = decisions.get(comp_val, {})
        maintenance    = comp_decisions.get("maintenance", "none")
        buy_machine    = comp_decisions.get("buy_machine")
        rnd_invest     = comp_decisions.get("rnd_invest")
        units_to_produce = comp_decisions.get("units_to_produce")  # None = max

        machines = all_machines.get(comp_val, [])

        # ── Per-component machine sabotage event ──────────────────────────────
        for ev in events:
            p = ev.payload or {}
            if ev.event_type == EventType.MACHINE_SABOTAGE:
                if p.get("component", comp_val) == comp_val and machines:
                    # Hit the machine with the lowest condition
                    victim = min(machines, key=lambda m: m.condition)
                    victim.condition = max(
                        0.0, victim.condition - p.get("condition_hit", 0.0)
                    )
                    if victim.condition <= 0.0:
                        victim.is_active = False
                        machines = [m for m in machines if m.is_active]

        # ── Fast-track bonus (applies to the new machine bought this cycle) ───
        fast_condition_bonus = 0.0
        fast_quality_bonus   = 0.0
        for ev in events:
            p = ev.payload or {}
            if (ev.event_type == EventType.FAST_TRACK_INFRA
                    and p.get("component", comp_val) == comp_val):
                fast_condition_bonus += p.get("condition_bonus", 0.0)
                fast_quality_bonus   += p.get("quality_bonus", 0.0)

        # ── Buy new machine (if not infra-delayed) ────────────────────────────
        if buy_machine and comp_val not in infra_delayed_comps:
            tier = buy_machine.get("tier") if isinstance(buy_machine, dict) \
                   else buy_machine
            if tier:
                tier_cfg = MACHINE_TIERS.get(tier, {})
                cost     = tier_cfg.get("buy", 0.0)
                inventory.funds -= cost

                new_machine = Machine(
                    team_id         = team.id,
                    slot_id         = slot.id,
                    component       = comp_val,
                    tier            = tier,
                    condition       = min(
                        MACHINE_MAX_CONDITION,
                        MACHINE_MAX_CONDITION + fast_condition_bonus,
                    ),
                    is_active       = True,
                    purchased_cycle = cycle.cycle_number,
                    source          = "bought",
                )
                db.add(new_machine)
                db.flush()
                machines.append(new_machine)
                all_machines[comp_val] = machines

        # ── Maintenance and degradation (applied to all machines equally) ─────
        if machines:
            maint_cost        = _apply_maintenance_and_degrade(machines, maintenance)
            inventory.funds  -= maint_cost
            total_maint_cost += maint_cost
            # Refresh active list after degradation (some may have been destroyed)
            machines = [m for m in machines if m.is_active]
            all_machines[comp_val] = machines

        # ── R&D investment ────────────────────────────────────────────────────
        if rnd_invest:
            focus  = rnd_invest.get("focus") if isinstance(rnd_invest, dict) \
                     else rnd_invest.focus
            levels = rnd_invest.get("levels", 1) if isinstance(rnd_invest, dict) \
                     else rnd_invest.levels
            cost   = levels * 10_000.0
            inventory.funds -= cost
            _schedule_rnd_event(db, team, cycle, comp_val, focus, levels, cost)

        if not machines:
            component_summaries[comp_val] = {
                "units_produced":  0,
                "total_throughput": 0,
                "note":            "no active machines",
            }
            continue

        # ── Compute throughput and output parameters ──────────────────────────
        tp_total  = int(total_throughput(machines) * labour_factor * production_survival)
        eff_grade = _effective_grade_for_machines(machines, slot.rnd_quality)
        eff_grade += fast_quality_bonus   # bonus only if a machine was bought
        sigma     = _compute_sigma(automation_level, inventory.skill_level,
                                    slot.rnd_consistency)
        yield_reduction = slot.rnd_yield * RND_YIELD_BONUS

        # ── Player-chosen units_to_produce ────────────────────────────────────
        # Clamp to [0, tp_total]. None means use full throughput.
        if units_to_produce is None:
            requested = tp_total
        else:
            requested = max(0, min(units_to_produce, tp_total))

        # ── Consume raw stock ─────────────────────────────────────────────────
        slot.raw_stock, consumed, rm_mean = _consume_raw_stock(
            slot.raw_stock, requested, yield_reduction
        )

        # ── Draw finished component output ────────────────────────────────────
        blended_mean = RM_WEIGHT * rm_mean + (1 - RM_WEIGHT) * eff_grade
        comp_arr     = _draw_component_array(blended_mean, sigma, consumed, rng)

        # Merge into finished_stock (carry-over stays)
        existing            = slot.finished_stock or [0] * 101
        slot.finished_stock = [existing[i] + comp_arr[i] for i in range(101)]

        component_summaries[comp_val] = {
            "units_produced":   sum(comp_arr[1:]),
            "total_throughput": tp_total,
            "requested":        requested,
            "machines_active":  len(machines),
            "effective_grade":  round(eff_grade, 1),
            "sigma":            round(sigma, 2),
            "rm_consumed":      consumed,
            "fin_stock_total":  sum(slot.finished_stock[1:]),
        }

    # ── Wages ─────────────────────────────────────────────────────────────────
    wage_total      = inventory.workforce_size * WAGE_COST_PER_WORKER.get(wage_level, 500.0)
    inventory.funds -= round(wage_total, 2)

    # ── Mark events applied ───────────────────────────────────────────────────
    _mark_applied(events)
    db.flush()

    return {
        "components":    component_summaries,
        "forced_strike": forced_strike,
        "riot":          inventory.morale <= MORALE_RIOT,
        "wage_total":    round(wage_total, 2),
        "maint_total":   round(total_maint_cost, 2),
        "current_funds": round(inventory.funds, 2),
    }


def _schedule_rnd_event(
    db:        Session,
    team,
    cycle:     Cycle,
    component: str,
    focus:     str,
    levels:    int,
    cost:      float,
) -> None:
    """Find the arrival cycle and create an RND_INVESTMENT event."""
    from models.game import Cycle as CycleModel, Game
    from services.deals import create_rnd_event

    target_number = cycle.cycle_number + RND_CYCLES_PER_LEVEL
    target_cycle  = (
        db.query(CycleModel)
        .filter(
            CycleModel.game_id      == team.game_id,
            CycleModel.cycle_number == target_number,
        )
        .first()
    )
    if target_cycle is None:
        return   # Cycle doesn't exist yet — deferred

    game_obj = db.query(Game).filter(Game.id == team.game_id).first()
    create_rnd_event(
        db           = db,
        game         = game_obj,
        team         = team,
        target_cycle = target_cycle,
        component    = component,
        focus        = focus,
        levels       = levels,
        cost         = cost,
    )
