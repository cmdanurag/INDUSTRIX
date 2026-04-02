"""
services/sales.py
=================
Sales resolution engine.

resolve_sales(db, team, cycle, all_teams, rng)
    1. Load PENDING sales-phase Events for this team+cycle.
       Apply modifiers BEFORE tier actions run:
         - market_limit       → block fraction of sellable drones
         - demand_suppression → reduce brand weight in market allocation
         - demand_boost       → increase brand weight
         - price_pressure     → cap sell price at PRICE_SUBSTANDARD
         - quality_waiver     → lower effective qr_hard
         - gov_purchase       → add guaranteed revenue
         - audit_immunity     → (tracked; no mechanical effect in sales)
    2. Classify drone_stock into quality tiers.
    3. Run market allocation across all teams.
    4. Apply per-tier sales actions and compute revenue.
    5. Run financial-phase Events for this team+cycle:
         - loan_interest      → deduct from funds, credit lender
         - arbitrary_fine     → deduct from funds
         - tax_evasion_refund → refund fraction of total costs this cycle
         - global_market_shift→ update game-level parameters
    6. Update inventory, brand, and cumulative_profit.
    7. Mark all consumed events APPLIED.

seed_sales_memory(db, team)
    Seeding helper.
"""
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from core.config import (
    BASE_MARKET_CAPACITY, BLACK_MKT_DISCOVERY_BASE, BLACK_MKT_FINE_MULTIPLIER,
    BRAND_DECAY, BRAND_DELTA_BLACK_MKT_FOUND, BRAND_DELTA_BLACK_MKT_HIDDEN,
    BRAND_DELTA_PREMIUM_SELL, BRAND_DELTA_STANDARD_SELL,
    BRAND_DELTA_SUBSTANDARD_SELL, BRAND_DEMAND_EXPONENT, BRAND_TIERS,
    HOLDING_COST_PER_UNIT, MAX_MARKET_SHARE, PRICE_ELASTICITY,
    PRICE_PREMIUM_NORMAL, PRICE_PREMIUM_SELL, PRICE_REJECT_BLACK_MKT,
    PRICE_REJECT_SCRAP, PRICE_STANDARD, PRICE_SUBSTANDARD, QUALITY_MAX,
)
from core.enums import (
    BrandTier, EventPhase, EventStatus, EventType,
    QualityTier, SalesAction,
)
from models.deals import Event
from models.game import Game
from models.procurement import Inventory
from models.sales import MemorySales


# ── Seeding ───────────────────────────────────────────────────────────────────

DEFAULT_SALES_DECISIONS = {
    "reject":      {"action": "scrap",           "price_override": None},
    "substandard": {"action": "sell_discounted",  "price_override": None},
    "standard":    {"action": "sell_market",      "price_override": None},
    "premium":     {"action": "sell_premium",     "price_override": None},
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
    """Global market shift events have target_team_id = NULL."""
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


# ── Brand helpers ─────────────────────────────────────────────────────────────

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


# ── Market allocation ─────────────────────────────────────────────────────────

def _market_allocation(
    team_inputs:     List[Dict],
    market_capacity: int,
) -> Dict[int, int]:
    """Allocate demand proportionally by brand weight. Returns {team_id: can_sell}."""
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
    """
    Aggregate all sales-phase event modifiers for this team.
    Returns a dict of effective modifiers.
    """
    mods = {
        "block_fraction":    0.0,
        "demand_multiplier": 1.0,
        "price_pressure":    False,
        "threshold_reduction": 0.0,
        "gov_purchase_units": 0,
        "gov_purchase_price": 0.0,
        "audit_immune":      False,
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


# ── Financial event resolution ────────────────────────────────────────────────

def _resolve_financial_events(
    db:          Session,
    team,
    cycle,
    inventory:   Inventory,
    total_costs: float,
) -> Tuple[float, List[Event]]:
    """
    Resolve all FINANCIAL-phase events for this team.
    Returns (net_financial_adjustment, events_applied).
    """
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
    """Apply GLOBAL_MARKET_SHIFT events to the game object."""
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
    Global market shift events are applied once per cycle by this function
    (called for the first team only via the cycle service).
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

    # ── Load and aggregate sales events ──────────────────────────────────────
    sales_events = _load_phase_events(db, team.id, cycle.id, EventPhase.SALES)
    mods         = _aggregate_sales_events(sales_events)

    # ── Effective qr thresholds ───────────────────────────────────────────────
    effective_qr_hard = max(0.0, cycle.qr_hard - mods["threshold_reduction"])

    # ── Classify drones ───────────────────────────────────────────────────────
    drone_stock = inventory.drone_stock or [0] * 101
    tier_counts = classify_drones(
        drone_stock, effective_qr_hard, cycle.qr_soft, cycle.qr_premium
    )

    # ── Count units offered to market ─────────────────────────────────────────
    sell_actions = {"sell_market", "sell_premium", "sell_discounted"}
    units_offered = sum(
        count for tier, count in tier_counts.items()
        if decisions.get(tier, {}).get("action") in sell_actions
    )

    # Apply market access block
    if mods["block_fraction"] > 0:
        units_offered = max(0, int(units_offered * (1.0 - mods["block_fraction"])))

    # ── Market allocation across all teams ────────────────────────────────────
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
        # Get sales events for this team's demand multiplier
        t_sales_events = _load_phase_events(db, t.id, cycle.id, EventPhase.SALES)
        t_mods         = _aggregate_sales_events(t_sales_events)
        all_inputs.append({
            "team_id":          t.id,
            "brand_score":      inv_t.brand_score,
            "units_offered":    offered_t,
            "demand_multiplier": t_mods["demand_multiplier"],
        })

    market_capacity = int(BASE_MARKET_CAPACITY * cycle.market_demand_multiplier)
    allocation      = _market_allocation(all_inputs, market_capacity)
    can_sell        = allocation.get(team.id, 0)

    # ── Government guaranteed purchase (added before market) ──────────────────
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
    grade_ptr       = list(drone_stock)

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
            # Selling actions
            can_take = min(count, max(0, can_sell - sold_so_far))
            unsold   = count - can_take

            if can_take > 0:
                if mods["price_pressure"]:
                    price = min(
                        p_over or PRICE_STANDARD,
                        PRICE_SUBSTANDARD,
                    )
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

            # Unsold → hold
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

    # ── Black market discovery ────────────────────────────────────────────────
    black_mkt_found  = False
    black_mkt_hidden = False
    black_mkt_fine   = 0.0

    if black_mkt_units > 0:
        total_produced = sum(drone_stock[1:]) or 1
        p_discover     = (
            BLACK_MKT_DISCOVERY_BASE * (black_mkt_units / total_produced)
        )
        if random.random() < p_discover:
            black_mkt_fine  = black_mkt_rev * BLACK_MKT_FINE_MULTIPLIER
            black_mkt_found = True
        else:
            total_revenue   += black_mkt_rev
            black_mkt_hidden = True

    # ── Holding cost ──────────────────────────────────────────────────────────
    holding_cost   = total_held * HOLDING_COST_PER_UNIT
    total_costs_this_cycle = holding_cost + black_mkt_fine
    # (procurement and production costs were already deducted earlier)
    total_revenue -= total_costs_this_cycle

    # ── Apply sales events, mark applied ─────────────────────────────────────
    _mark_applied(sales_events)

    # ── Financial events (loans, fines, refunds) ──────────────────────────────
    fin_adjustment, fin_events = _resolve_financial_events(
        db, team, cycle, inventory, total_costs_this_cycle
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
        "units_sold":       sold_so_far,
        "units_held":       total_held,
        "units_scrapped":   total_scrapped,
        "gov_purchase_rev": round(gov_revenue, 2),
        "black_mkt_units":  black_mkt_units,
        "black_mkt_found":  black_mkt_found,
        "black_mkt_fine":   round(black_mkt_fine, 2),
        "total_revenue":    round(total_revenue, 2),
        "holding_cost":     round(holding_cost, 2),
        "fin_adjustment":   round(fin_adjustment, 2),
        "brand_score":      round(inventory.brand_score, 2),
        "closing_funds":    round(inventory.funds, 2),
        "tier_sold":        tier_sold,
    }


def resolve_global_financial_events(db: Session, game: Game, cycle) -> None:
    """
    Apply GLOBAL_MARKET_SHIFT events and mark them applied.
    Called once per cycle by the cycle service, not per team.
    """
    events = _resolve_global_financial_events(db, game, cycle)
    _mark_applied(events)
    db.flush()