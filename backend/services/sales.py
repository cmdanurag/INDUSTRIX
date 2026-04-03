"""
services/sales.py
=================
Sales resolution engine.

Scope (updated):
  Phase 1 — Assembly: pull finished components from stock, assemble drones.
             Player controls units_to_assemble (0 to max possible).
             Max possible = min(finished_stock total) across all six components.
  Phase 2 — Selling: classify assembled + carried drone stock into tiers,
             apply per-tier actions, run market allocation.
  Phase 3 — Financial: loan interest, fines, tax refunds (end of sales).

seed_sales_memory(db, team)
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
    BASE_MARKET_CAPACITY, BLACK_MKT_DISCOVERY_BASE, BLACK_MKT_FINE_MULTIPLIER,
    BRAND_DECAY, BRAND_DELTA_BLACK_MKT_FOUND, BRAND_DELTA_BLACK_MKT_HIDDEN,
    BRAND_DELTA_PREMIUM_SELL, BRAND_DELTA_STANDARD_SELL,
    BRAND_DELTA_SUBSTANDARD_SELL, BRAND_DEMAND_EXPONENT, BRAND_TIERS,
    HOLDING_COST_PER_UNIT, MAX_MARKET_SHARE, PRICE_ELASTICITY,
    PRICE_PREMIUM_NORMAL, PRICE_PREMIUM_SELL, PRICE_REJECT_BLACK_MKT,
    PRICE_REJECT_SCRAP, PRICE_STANDARD, PRICE_SUBSTANDARD, QUALITY_MAX,
)
from core.enums import (
    BrandTier, ComponentType, EventPhase, EventStatus, EventType,
    QualityTier, SalesAction,
)
from models.deals import Event
from models.game import Game
from models.procurement import ComponentSlot, Inventory
from models.sales import MemorySales


# ── Seeding ───────────────────────────────────────────────────────────────────

DEFAULT_SALES_DECISIONS = {
    "units_to_assemble": None,   # None = assemble maximum possible
    "reject":      {"action": "scrap",          "price_override": None},
    "substandard": {"action": "sell_discounted", "price_override": None},
    "standard":    {"action": "sell_market",     "price_override": None},
    "premium":     {"action": "sell_premium",    "price_override": None},
}


def seed_sales_memory(db: Session, team) -> MemorySales:
    mem = MemorySales(team_id=team.id, decisions=DEFAULT_SALES_DECISIONS.copy())
    db.add(mem)
    db.flush()
    return mem


# ── Event loading ─────────────────────────────────────────────────────────────

def _load_phase_events(
    db: Session, team_id: int, cycle_id: int, phase: EventPhase
) -> List[Event]:
    return (
        db.query(Event)
        .filter(
            Event.cycle_id       == cycle_id,
            Event.target_team_id == team_id,
            Event.phase          == phase,
            Event.status         == EventStatus.PENDING,
        )
        .all()
    )


def _load_global_financial_events(
    db: Session, cycle_id: int
) -> List[Event]:
    return (
        db.query(Event)
        .filter(
            Event.cycle_id       == cycle_id,
            Event.target_team_id == None,
            Event.phase          == EventPhase.FINANCIAL,
            Event.event_type     == EventType.GLOBAL_MARKET_SHIFT,
            Event.status         == EventStatus.PENDING,
        )
        .all()
    )


def _mark_applied(events: List[Event]) -> None:
    now = datetime.utcnow()
    for ev in events:
        ev.status     = EventStatus.APPLIED
        ev.applied_at = now


# ── Brand ─────────────────────────────────────────────────────────────────────

def compute_brand_tier(score: float) -> BrandTier:
    tier = BrandTier.POOR
    for t, threshold in sorted(BRAND_TIERS.items(), key=lambda x: x[1]):
        if score >= threshold:
            tier = BrandTier(t)
    return tier


def _update_brand(
    inventory:        Inventory,
    tier_sold:        Dict[str, int],
    black_mkt_found:  bool,
    black_mkt_hidden: bool,
) -> None:
    delta = 0.0
    if tier_sold.get("premium", 0) > 0:
        delta += BRAND_DELTA_PREMIUM_SELL
    if tier_sold.get("standard", 0) > 0:
        delta += BRAND_DELTA_STANDARD_SELL
    if tier_sold.get("substandard", 0) > 0:
        delta += BRAND_DELTA_SUBSTANDARD_SELL
    if black_mkt_found:
        delta += BRAND_DELTA_BLACK_MKT_FOUND
    elif black_mkt_hidden:
        delta += BRAND_DELTA_BLACK_MKT_HIDDEN

    inventory.brand_score *= BRAND_DECAY
    inventory.brand_score  = max(0.0, min(100.0, inventory.brand_score + delta))
    inventory.brand_tier   = compute_brand_tier(inventory.brand_score)


# ── Tier classification ───────────────────────────────────────────────────────

def classify_drones(
    drone_stock: List[int],
    qr_hard:     float,
    qr_soft:     float,
    qr_premium:  float,
) -> Dict[str, int]:
    counts = {"reject": 0, "substandard": 0, "standard": 0, "premium": 0}
    for g in range(1, 101):
        n = drone_stock[g]
        if n == 0:
            continue
        if g < qr_hard:
            counts["reject"]      += n
        elif g < qr_soft:
            counts["substandard"] += n
        elif g < qr_premium:
            counts["standard"]    += n
        else:
            counts["premium"]     += n
    return counts


# ── Assembly ──────────────────────────────────────────────────────────────────

def _assemble_drones(
    slots:           Dict[str, ComponentSlot],
    units_requested: int,
    rng:             np.random.Generator,
) -> Tuple[List[int], Dict[str, List[int]]]:
    """
    Assemble up to units_requested drones from finished component stocks.

    Maximum possible = min(total finished stock) across all six components.
    If units_requested > max_possible, clamp to max_possible.

    Uses the weakest-link + simple-average blend formula from config.

    Returns:
        drone_array       : int[101] — newly assembled drones
        updated_fin_stocks: {comp_val: int[101]} — remaining finished stock
                            after assembly consumed components
    """
    all_comps = [c.value for c in ComponentType]

    fin_stocks: Dict[str, List[int]] = {
        comp_val: list(slots[comp_val].finished_stock or [0] * 101)
        for comp_val in all_comps
        if comp_val in slots
    }

    # Max assembleable = constrained by the scarcest component
    max_possible = min(sum(arr[1:]) for arr in fin_stocks.values()) \
                   if fin_stocks else 0
    to_assemble  = max(0, min(units_requested, max_possible))

    drone_array = [0] * 101

    for _ in range(to_assemble):
        grades = []
        for comp_val in all_comps:
            arr   = fin_stocks.get(comp_val, [0] * 101)
            total = sum(arr[1:])
            if total == 0:
                grades.append(0)
                continue
            r = random.randint(1, total)
            cumulative = 0
            for g in range(1, 101):
                cumulative += arr[g]
                if cumulative >= r:
                    arr[g] -= 1   # consume one unit
                    grades.append(g)
                    break

        # Weakest-link blend
        simple_avg = sum(grades) / len(grades)
        min_g      = min(grades)
        weights    = [math.exp(-ASSEMBLY_BETA * (g - min_g)) for g in grades]
        wl_avg     = sum(w * g for w, g in zip(weights, grades)) / sum(weights)
        final      = (1 - ASSEMBLY_LAMBDA) * simple_avg + ASSEMBLY_LAMBDA * wl_avg
        drone_grade = int(np.clip(final, 0, QUALITY_MAX))
        drone_array[drone_grade] += 1

    return drone_array, fin_stocks


# ── Market allocation ─────────────────────────────────────────────────────────

def _market_allocation(
    team_inputs:     List[Dict],
    market_capacity: int,
) -> Dict[int, int]:
    if not team_inputs:
        return {}

    weights = {
        inp["team_id"]: max(
            0.0,
            (inp["brand_score"] ** BRAND_DEMAND_EXPONENT)
            * inp.get("demand_multiplier", 1.0),
        )
        for inp in team_inputs
    }
    total_weight = sum(weights.values()) or 1.0

    allocation = {}
    for inp in team_inputs:
        share = weights[inp["team_id"]] / total_weight
        share = min(share, MAX_MARKET_SHARE)
        cap   = int(market_capacity * share)
        allocation[inp["team_id"]] = min(cap, inp["units_offered"])

    return allocation


# ── Sales event modifiers ─────────────────────────────────────────────────────

def _aggregate_sales_events(events: List[Event]) -> Dict:
    mods = {
        "block_fraction":     0.0,
        "demand_multiplier":  1.0,
        "price_pressure":     False,
        "threshold_reduction": 0.0,
        "gov_purchase_units": 0,
        "gov_purchase_price": 0.0,
        "audit_immune":       False,
    }
    for ev in events:
        p = ev.payload or {}
        if ev.event_type == EventType.MARKET_LIMIT:
            mods["block_fraction"] = min(
                0.95, mods["block_fraction"] + p.get("block_fraction", 0.0)
            )
        elif ev.event_type == EventType.DEMAND_SUPPRESSION:
            mods["demand_multiplier"] *= p.get("demand_multiplier", 1.0)
        elif ev.event_type == EventType.DEMAND_BOOST:
            mods["demand_multiplier"] *= p.get("demand_multiplier", 1.0)
        elif ev.event_type == EventType.PRICE_PRESSURE:
            mods["price_pressure"] = True
        elif ev.event_type == EventType.QUALITY_WAIVER:
            mods["threshold_reduction"] += p.get("threshold_reduction", 0.0)
        elif ev.event_type == EventType.GOV_PURCHASE:
            mods["gov_purchase_units"] += p.get("units", 0)
            mods["gov_purchase_price"]  = p.get("price_per_unit", 2_800.0)
        elif ev.event_type == EventType.AUDIT_IMMUNITY:
            mods["audit_immune"] = True
    return mods


# ── Financial events ──────────────────────────────────────────────────────────

def _resolve_financial_events(
    db:          Session,
    team,
    cycle,
    inventory:   Inventory,
    total_costs: float,
) -> Tuple[float, List[Event]]:
    fin_events = _load_phase_events(db, team.id, cycle.id, EventPhase.FINANCIAL)
    adjustment = 0.0

    for ev in fin_events:
        p = ev.payload or {}
        if ev.event_type == EventType.LOAN_INTEREST:
            amount    = p.get("amount", 0.0)
            lender_id = p.get("lender_team_id")
            inventory.funds -= amount
            adjustment      -= amount
            if lender_id:
                lender_inv = (
                    db.query(Inventory)
                    .filter(Inventory.team_id == lender_id)
                    .first()
                )
                if lender_inv:
                    lender_inv.funds += amount
        elif ev.event_type == EventType.ARBITRARY_FINE:
            fine             = p.get("fine_amount", 0.0)
            inventory.funds -= fine
            adjustment      -= fine
        elif ev.event_type == EventType.TAX_EVASION_REFUND:
            refund           = total_costs * p.get("refund_fraction", 0.0)
            inventory.funds += refund
            adjustment      += refund

    return adjustment, fin_events


def _resolve_global_financial_events(
    db: Session, game: Game, cycle
) -> List[Event]:
    global_events = _load_global_financial_events(db, cycle.id)
    for ev in global_events:
        p = ev.payload or {}
        if "market_demand_multiplier_delta" in p:
            game.market_demand_multiplier = max(
                0.1,
                game.market_demand_multiplier
                + p["market_demand_multiplier_delta"],
            )
        for field in ("qr_hard", "qr_soft", "qr_premium"):
            delta_key = f"{field}_delta"
            if delta_key in p:
                current = getattr(game, field, 50.0)
                setattr(game, field,
                        max(0.0, min(100.0, current + p[delta_key])))
    return global_events


# ── Main resolution ───────────────────────────────────────────────────────────

def resolve_sales(
    db:        Session,
    team,
    cycle,
    all_teams: List,
    rng:       Optional[np.random.Generator] = None,
) -> Dict:
    """
    Full sales + financial resolution for one team.

    Steps:
      1. Load sales-phase events, aggregate modifiers.
      2. Assemble drones from finished_stock (player-controlled quantity).
      3. Classify assembled + carried drone_stock into quality tiers.
      4. Market allocation across all teams.
      5. Per-tier selling actions.
      6. Black market, holding costs, brand update.
      7. Financial events (loans, fines, refunds).
      8. Update inventory, mark events applied.
    """
    if rng is None:
        rng = np.random.default_rng()

    inventory: Inventory = (
        db.query(Inventory).filter(Inventory.team_id == team.id).first()
    )
    mem: MemorySales = (
        db.query(MemorySales).filter(MemorySales.team_id == team.id).first()
    )
    decisions = mem.decisions if mem else DEFAULT_SALES_DECISIONS.copy()

    # ── Sales events ──────────────────────────────────────────────────────────
    sales_events = _load_phase_events(db, team.id, cycle.id, EventPhase.SALES)
    mods         = _aggregate_sales_events(sales_events)

    effective_qr_hard = max(0.0, cycle.qr_hard - mods["threshold_reduction"])

    # ── Load component slots for assembly ─────────────────────────────────────
    slots: Dict[str, ComponentSlot] = {
        s.component.value: s
        for s in db.query(ComponentSlot)
        .filter(ComponentSlot.team_id == team.id)
        .all()
    }

    # ── Assembly ──────────────────────────────────────────────────────────────
    raw_units_to_assemble = decisions.get("units_to_assemble")

    # Max possible = min finished stock across all components
    max_possible = min(
        sum(s.finished_stock[1:]) if s.finished_stock else 0
        for s in slots.values()
    ) if slots else 0

    if raw_units_to_assemble is None:
        units_to_assemble = max_possible       # assemble everything possible
    else:
        units_to_assemble = max(0, min(raw_units_to_assemble, max_possible))

    drone_arr, updated_fin_stocks = _assemble_drones(slots, units_to_assemble, rng)

    # Write updated finished stocks back
    for comp_val, new_stock in updated_fin_stocks.items():
        if comp_val in slots:
            slots[comp_val].finished_stock = new_stock

    drones_assembled = sum(drone_arr[1:])

    # Merge newly assembled drones into existing drone_stock
    existing_drone_stock = inventory.drone_stock or [0] * 101
    combined_stock = [existing_drone_stock[i] + drone_arr[i] for i in range(101)]

    # ── Classify drones ───────────────────────────────────────────────────────
    tier_counts = classify_drones(
        combined_stock, effective_qr_hard, cycle.qr_soft, cycle.qr_premium
    )

    # ── Market allocation ─────────────────────────────────────────────────────
    sell_actions = {"sell_market", "sell_premium", "sell_discounted"}

    units_offered = sum(
        count for tier, count in tier_counts.items()
        if decisions.get(tier, {}).get("action") in sell_actions
    )
    if mods["block_fraction"] > 0:
        units_offered = max(0, int(units_offered * (1.0 - mods["block_fraction"])))

    all_inputs = []
    for t in all_teams:
        inv_t = db.query(Inventory).filter(Inventory.team_id == t.id).first()
        mem_t = db.query(MemorySales).filter(MemorySales.team_id == t.id).first()
        if not inv_t:
            continue
        stock_t = inv_t.drone_stock or [0] * 101
        tiers_t = classify_drones(
            stock_t, cycle.qr_hard, cycle.qr_soft, cycle.qr_premium
        )
        dec_t   = mem_t.decisions if mem_t else DEFAULT_SALES_DECISIONS.copy()
        offered_t = sum(
            cnt for tier, cnt in tiers_t.items()
            if dec_t.get(tier, {}).get("action") in sell_actions
        )
        t_events = _load_phase_events(db, t.id, cycle.id, EventPhase.SALES)
        t_mods   = _aggregate_sales_events(t_events)
        all_inputs.append({
            "team_id":          t.id,
            "brand_score":      inv_t.brand_score,
            "units_offered":    offered_t,
            "demand_multiplier": t_mods["demand_multiplier"],
        })

    market_capacity = int(BASE_MARKET_CAPACITY * cycle.market_demand_multiplier)
    allocation      = _market_allocation(all_inputs, market_capacity)
    can_sell        = allocation.get(team.id, 0)

    # ── Government guaranteed purchase ────────────────────────────────────────
    gov_revenue = 0.0
    if mods["gov_purchase_units"] > 0:
        gov_revenue = mods["gov_purchase_units"] * mods["gov_purchase_price"]

    # ── Per-tier resolution ───────────────────────────────────────────────────
    total_revenue   = gov_revenue
    total_held      = 0
    total_scrapped  = 0
    black_mkt_units = 0
    black_mkt_rev   = 0.0
    tier_sold:      Dict[str, int] = {}
    new_drone_stock = [0] * 101
    sold_so_far     = 0
    grade_ptr       = list(combined_stock)

    for tier_val in ["premium", "standard", "substandard", "reject"]:
        count  = tier_counts[tier_val]
        dec    = decisions.get(tier_val, {})
        action = dec.get("action", "scrap")
        p_over = dec.get("price_override")

        if count == 0:
            continue

        if action == "scrap":
            total_revenue  += count * PRICE_REJECT_SCRAP
            total_scrapped += count

        elif action == "black_market":
            black_mkt_units += count
            black_mkt_rev   += count * PRICE_REJECT_BLACK_MKT

        elif action == "hold":
            total_held += count
            remaining   = count
            for g in range(QUALITY_MAX, 0, -1):
                if remaining <= 0:
                    break
                take = min(grade_ptr[g], remaining)
                new_drone_stock[g] += take
                grade_ptr[g]       -= take
                remaining          -= take

        else:
            can_take = min(count, max(0, can_sell - sold_so_far))
            unsold   = count - can_take

            if can_take > 0:
                if mods["price_pressure"]:
                    price = min(p_over or PRICE_STANDARD, PRICE_SUBSTANDARD)
                elif action == "sell_premium" and tier_val == "premium":
                    price = p_over or PRICE_PREMIUM_SELL
                elif action == "sell_discounted":
                    price = p_over or PRICE_SUBSTANDARD
                elif tier_val == "premium":
                    price = p_over or PRICE_PREMIUM_NORMAL
                elif tier_val == "standard":
                    price = p_over or PRICE_STANDARD
                elif tier_val == "substandard":
                    price = p_over or PRICE_SUBSTANDARD
                else:
                    price = PRICE_REJECT_SCRAP

                total_revenue       += can_take * price
                sold_so_far         += can_take
                tier_sold[tier_val]  = can_take

            if unsold > 0:
                total_held += unsold
                remaining   = unsold
                for g in range(QUALITY_MAX, 0, -1):
                    if remaining <= 0:
                        break
                    take = min(grade_ptr[g], remaining)
                    new_drone_stock[g] += take
                    grade_ptr[g]       -= take
                    remaining          -= take

    # ── Black market ──────────────────────────────────────────────────────────
    black_mkt_found  = False
    black_mkt_hidden = False
    black_mkt_fine   = 0.0

    if black_mkt_units > 0:
        total_produced = sum(combined_stock[1:]) or 1
        p_discover = BLACK_MKT_DISCOVERY_BASE * (black_mkt_units / total_produced)
        if random.random() < p_discover:
            black_mkt_fine  = black_mkt_rev * BLACK_MKT_FINE_MULTIPLIER
            black_mkt_found = True
        else:
            total_revenue   += black_mkt_rev
            black_mkt_hidden = True

    # ── Costs ─────────────────────────────────────────────────────────────────
    holding_cost           = total_held * HOLDING_COST_PER_UNIT
    sales_costs_this_cycle = holding_cost + black_mkt_fine
    total_revenue         -= sales_costs_this_cycle

    # ── Mark sales events applied ─────────────────────────────────────────────
    _mark_applied(sales_events)

    # ── Financial events ──────────────────────────────────────────────────────
    fin_adjustment, fin_events = _resolve_financial_events(
        db, team, cycle, inventory, sales_costs_this_cycle
    )
    _mark_applied(fin_events)

    # ── Brand update ──────────────────────────────────────────────────────────
    _update_brand(inventory, tier_sold, black_mkt_found, black_mkt_hidden)

    # ── Update inventory ──────────────────────────────────────────────────────
    inventory.drone_stock      = new_drone_stock
    inventory.funds            = round(inventory.funds + total_revenue, 2)
    inventory.cumulative_profit = round(
        inventory.cumulative_profit + total_revenue, 2
    )

    db.flush()

    return {
        "drones_assembled":  drones_assembled,
        "max_possible":      max_possible,
        "units_sold":        sold_so_far,
        "units_held":        total_held,
        "units_scrapped":    total_scrapped,
        "gov_purchase_rev":  round(gov_revenue, 2),
        "black_mkt_units":   black_mkt_units,
        "black_mkt_found":   black_mkt_found,
        "black_mkt_fine":    round(black_mkt_fine, 2),
        "total_revenue":     round(total_revenue, 2),
        "holding_cost":      round(holding_cost, 2),
        "fin_adjustment":    round(fin_adjustment, 2),
        "brand_score":       round(inventory.brand_score, 2),
        "closing_funds":     round(inventory.funds, 2),
        "tier_sold":         tier_sold,
    }


def resolve_global_financial_events(db: Session, game: Game, cycle) -> None:
    events = _resolve_global_financial_events(db, game, cycle)
    _mark_applied(events)
    db.flush()
