"""
services/production.py
======================
Production resolution engine.

resolve_production(db, team, cycle, rng)
    1. Load all PENDING production-phase Events for this team+cycle.
    2. Apply event modifiers before output is calculated:
         - machine sabotage (condition hit)
         - infra delay (block upgrades)
         - fast track infra (bonus on new machines)
         - labour strike / poach (survival rate, skill hit)
         - R&D sabotage (level reduction)
         - skilled labour bonus
         - R&D investment arrival (increment R&D levels)
    3. Per component: maintenance, machine upgrade (if not delayed),
       degradation, sigma computation, raw stock consumption, output draw.
    4. Assemble drones from finished_stock.
    5. Deduct wages and maintenance costs.
    6. Mark all consumed events APPLIED.

seed_production_memory(db, team)
    Seeding helper.
"""
import math
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from core.config import (
    ASSEMBLY_BETA, ASSEMBLY_LAMBDA,
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
)
from core.enums import (
    AutomationLevel, ComponentType,
    EventPhase, EventStatus, EventType,
)
from models.deals import Event
from models.game import Cycle, Game
from models.production import MemoryProduction
from models.procurement import ComponentSlot, Inventory


# ── Seeding ───────────────────────────────────────────────────────────────────

def seed_production_memory(db: Session, team) -> MemoryProduction:
    default_decisions: Dict = {
        "wage_level":         "market",
        "target_headcount":   50,
        "upgrade_automation": None,
    }
    for comp in ComponentType:
        default_decisions[comp.value] = {
            "maintenance": "none",
            "rnd_invest":  None,
            "upgrade_to":  None,
        }
    mem = MemoryProduction(team_id=team.id, decisions=default_decisions)
    db.add(mem)
    db.flush()
    return mem


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


# ── Production helpers ────────────────────────────────────────────────────────

def _effective_machine_grade(base_grade: float, condition: float) -> float:
    factor = (condition / MACHINE_MAX_CONDITION) ** CONDITION_GRADE_EXPONENT
    return base_grade * factor


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


def _draw_component_array(
    mean: float, sigma: float, count: int, rng: np.random.Generator
) -> List[int]:
    if count <= 0:
        return [0] * 101
    draws = rng.normal(loc=mean, scale=max(0.5, sigma), size=count)
    arr   = [0] * 101
    for v in draws:
        g = int(np.clip(v, 0, QUALITY_MAX))
        arr[g] += 1
    arr[0] += arr[0]  # grades below 1 → scrap
    return arr


def _consume_raw_stock(
    raw_stock: List[int], units_needed: int, yield_reduction: float
) -> Tuple[List[int], int, float]:
    """Pull units from raw_stock, return (updated_stock, consumed, rm_mean)."""
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


def _assemble_drones(component_arrays: Dict[str, List[int]]) -> List[int]:
    """Combine six finished_stock arrays into a drone quality array."""
    drone_array  = [0] * 101
    min_produced = min(sum(arr[1:]) for arr in component_arrays.values())
    if min_produced == 0:
        return drone_array

    for _ in range(min_produced):
        grades = []
        for comp_arr in component_arrays.values():
            total = sum(comp_arr[1:])
            if total == 0:
                grades.append(0)
                continue
            r = random.randint(1, total)
            cumulative = 0
            for g in range(1, 101):
                cumulative += comp_arr[g]
                if cumulative >= r:
                    grades.append(g)
                    break

        simple_avg = sum(grades) / len(grades)
        min_g      = min(grades)
        weights    = [math.exp(-ASSEMBLY_BETA * (g - min_g)) for g in grades]
        wl_avg     = sum(w * g for w, g in zip(weights, grades)) / sum(weights)
        final      = (1 - ASSEMBLY_LAMBDA) * simple_avg + ASSEMBLY_LAMBDA * wl_avg
        drone_grade = int(np.clip(final, 0, QUALITY_MAX))
        drone_array[drone_grade] += 1

    return drone_array


def _required_labour(slots: Dict[str, ComponentSlot], automation_level: str) -> int:
    total = 0
    for slot in slots.values():
        tier_cfg = MACHINE_TIERS.get(slot.machine_tier_str, MACHINE_TIERS["standard"])
        total   += int(tier_cfg["labour"] * AUTOMATION_LABOUR_MULT.get(automation_level, 1.0))
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

    # ── Load production events ────────────────────────────────────────────────
    events = _load_production_events(db, team.id, cycle.id)

    # ── Apply team-wide event effects BEFORE output calculation ───────────────
    production_survival = 1.0
    forced_strike       = False
    infra_delayed_comps = set()  # components whose upgrades are blocked

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
                # No component specified → delay all
                infra_delayed_comps.update(slots.keys())

        elif ev.event_type == EventType.RND_SABOTAGE:
            comp   = p.get("component")
            focus  = p.get("focus")
            levels = p.get("levels_stolen", 1)
            if comp and focus and comp in slots:
                slot  = slots[comp]
                attr  = f"rnd_{focus}"
                setattr(slot, attr, max(0, getattr(slot, attr) - levels))

        elif ev.event_type == EventType.RND_INVESTMENT:
            # R&D arrives this cycle
            comp   = p.get("component")
            focus  = p.get("focus")
            levels = p.get("level_arriving", 1)
            if comp and focus and comp in slots:
                slot = slots[comp]
                attr = f"rnd_{focus}"
                setattr(slot, attr, min(MAX_RND_LEVEL, getattr(slot, attr) + levels))

    # ── Automation upgrade ────────────────────────────────────────────────────
    upgrade_auto = decisions.get("upgrade_automation")
    automation_level = (
        inventory.automation_level.value
        if hasattr(inventory.automation_level, "value")
        else str(inventory.automation_level)
    )
    if upgrade_auto and upgrade_auto != automation_level:
        cost = AUTOMATION_UPGRADE_COST.get(upgrade_auto, 0.0)
        inventory.funds -= cost
        inventory.automation_level = AutomationLevel(upgrade_auto)
        automation_level = upgrade_auto

    # ── Labour ────────────────────────────────────────────────────────────────
    target_headcount        = decisions.get("target_headcount", inventory.workforce_size)
    wage_level              = decisions.get("wage_level", "market")
    inventory.workforce_size = max(0, target_headcount)

    morale_delta = WAGE_MORALE_DELTA.get(wage_level, 0.0)
    required     = _required_labour(slots, automation_level)
    actual       = inventory.workforce_size
    if required > 0 and actual < required:
        understaffed_pct = (required - actual) / required * 100
        morale_delta    -= understaffed_pct * UNDERSTAFFING_MORALE_PENALTY

    inventory.morale = max(0.0, min(100.0, inventory.morale + morale_delta))

    if inventory.morale <= MORALE_RIOT and not forced_strike:
        production_survival = RIOT_SURVIVAL

    if inventory.morale >= MORALE_HIGH:
        inventory.skill_level = min(
            100.0, inventory.skill_level + SKILL_GAIN_HIGH_MORALE
        )
    elif inventory.morale <= MORALE_LOW:
        inventory.skill_level = max(
            0.0, inventory.skill_level + SKILL_GAIN_LOW_MORALE
        )

    # ── Per-component processing ──────────────────────────────────────────────
    component_summaries: Dict = {}
    component_arrays:    Dict[str, List[int]] = {}
    total_maint_cost    = 0.0

    for comp_val, slot in slots.items():
        comp_decisions = decisions.get(comp_val, {})
        maintenance    = comp_decisions.get("maintenance", "none")
        upgrade_to     = comp_decisions.get("upgrade_to")
        rnd_invest     = comp_decisions.get("rnd_invest")

        # ── Apply per-component events ────────────────────────────────────────
        for ev in events:
            p = ev.payload or {}
            if ev.event_type == EventType.MACHINE_SABOTAGE:
                if p.get("component", comp_val) == comp_val:
                    slot.machine_condition = max(
                        0.0,
                        slot.machine_condition - p.get("condition_hit", 0.0),
                    )

        # ── Machine upgrade (if not infra-delayed) ────────────────────────────
        fast_track_condition_bonus = 0.0
        fast_track_quality_bonus   = 0.0

        for ev in events:
            p = ev.payload or {}
            if (ev.event_type == EventType.FAST_TRACK_INFRA
                    and p.get("component", comp_val) == comp_val):
                fast_track_condition_bonus += p.get("condition_bonus", 0.0)
                fast_track_quality_bonus   += p.get("quality_bonus", 0.0)

        if upgrade_to and comp_val not in infra_delayed_comps:
            tier_cfg = MACHINE_TIERS.get(upgrade_to, {})
            slot.machine_tier_str  = upgrade_to
            slot.machine_condition = min(
                MACHINE_MAX_CONDITION,
                MACHINE_MAX_CONDITION + fast_track_condition_bonus,
            )
            inventory.funds -= tier_cfg.get("buy", 0.0)
        # Note: fast_track_quality_bonus is applied below to eff_grade

        # ── Maintenance & degradation ─────────────────────────────────────────
        tier_cfg    = MACHINE_TIERS.get(slot.machine_tier_str, MACHINE_TIERS["standard"])
        maint_cost  = MAINTENANCE_COST.get(maintenance, 0.0)
        degrade_mult = MAINTENANCE_DEGRADE_MULT.get(maintenance, 1.0)
        degrade_amt  = tier_cfg["degrade"] * degrade_mult

        if maintenance == "overhaul":
            recovery = min(
                OVERHAUL_RECOVERY_CAP,
                MACHINE_MAX_CONDITION - slot.machine_condition,
            )
            slot.machine_condition = min(
                MACHINE_MAX_CONDITION,
                slot.machine_condition + recovery,
            )
        else:
            slot.machine_condition = max(
                0.0, slot.machine_condition - degrade_amt
            )

        inventory.funds  -= maint_cost
        total_maint_cost += maint_cost

        # ── R&D investment → create Event for future cycle ────────────────────
        if rnd_invest:
            focus  = rnd_invest.get("focus")
            levels = rnd_invest.get("levels", 1)
            cost   = levels * 10_000.0
            inventory.funds -= cost
            _schedule_rnd_event(db, team, cycle, comp_val, focus, levels, cost)

        # ── Effective machine grade ───────────────────────────────────────────
        base_grade = tier_cfg["grade"] + fast_track_quality_bonus
        eff_grade  = _effective_machine_grade(base_grade, slot.machine_condition)
        eff_grade += slot.rnd_quality * RND_QUALITY_BONUS

        # ── Sigma ─────────────────────────────────────────────────────────────
        sigma = _compute_sigma(automation_level, inventory.skill_level,
                                slot.rnd_consistency)

        # ── Yield reduction ───────────────────────────────────────────────────
        yield_reduction = slot.rnd_yield * RND_YIELD_BONUS

        # ── Throughput ────────────────────────────────────────────────────────
        throughput = tier_cfg["throughput"]
        if actual < required and required > 0:
            throughput = int(throughput * (actual / required))

        # ── Consume raw stock ─────────────────────────────────────────────────
        slot.raw_stock, consumed, rm_mean = _consume_raw_stock(
            slot.raw_stock, throughput, yield_reduction
        )

        # ── Blend grade and draw output ───────────────────────────────────────
        blended_mean = RM_WEIGHT * rm_mean + (1 - RM_WEIGHT) * eff_grade
        units_to_produce = int(consumed * production_survival)
        comp_arr = _draw_component_array(blended_mean, sigma, units_to_produce, rng)

        # Merge into finished_stock
        existing            = slot.finished_stock or [0] * 101
        slot.finished_stock = [existing[i] + comp_arr[i] for i in range(101)]

        component_arrays[comp_val] = slot.finished_stock
        component_summaries[comp_val] = {
            "units_produced":    sum(comp_arr[1:]),
            "machine_condition": round(slot.machine_condition, 1),
            "effective_grade":   round(eff_grade, 1),
            "sigma":             round(sigma, 2),
            "rm_consumed":       consumed,
        }

    # ── Assemble drones ───────────────────────────────────────────────────────
    drone_array  = _assemble_drones(component_arrays)
    drones_built = sum(drone_array[1:])

    # Consume the finished_stock used for assembly
    for comp_val, slot in slots.items():
        remaining = list(slot.finished_stock)
        built     = drones_built
        for g in range(QUALITY_MAX, 0, -1):
            if built <= 0:
                break
            take        = min(remaining[g], built)
            remaining[g] -= take
            built        -= take
        slot.finished_stock = remaining

    existing_drones       = inventory.drone_stock or [0] * 101
    inventory.drone_stock = [existing_drones[i] + drone_array[i] for i in range(101)]

    # ── Wages ─────────────────────────────────────────────────────────────────
    wage_total      = inventory.workforce_size * WAGE_COST_PER_WORKER.get(wage_level, 500.0)
    inventory.funds -= round(wage_total, 2)

    # ── Mark events applied ───────────────────────────────────────────────────
    _mark_applied(events)
    db.flush()

    return {
        "drones_built":    drones_built,
        "forced_strike":   forced_strike,
        "riot":            inventory.morale <= MORALE_RIOT,
        "components":      component_summaries,
        "wage_total":      round(wage_total, 2),
        "maint_total":     round(total_maint_cost, 2),
        "current_funds":   round(inventory.funds, 2),
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
    """Find the cycle that is RND_CYCLES_PER_LEVEL away and create an event."""
    from models.game import Cycle as CycleModel
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
    # If the target cycle doesn't exist yet we store a placeholder with
    # cycle_id = current cycle and note it. cycle_service will re-assign
    # when the target cycle is created. For simplicity, we create the event
    # pointing at the current cycle and let the organiser know via notes.
    # A more robust approach is to store a "pending_rnd" table, but for the
    # event-based model, if the cycle exists we use it; otherwise we defer.
    if target_cycle is None:
        # Store as a deferred event on the current cycle with a special note.
        # When the target cycle is eventually created, a migration/script can
        # re-assign these. For now, we skip to avoid invalid FK.
        return

    game = db.query(type(team)).filter(type(team).id == team.game_id).first()
    # Simpler: import Game
    from industrix.models.game import Game
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