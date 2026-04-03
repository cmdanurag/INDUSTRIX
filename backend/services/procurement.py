"""
services/procurement.py
=======================
Procurement resolution engine.

resolve_procurement(db, team, cycle, rng)
    Reads MemoryProcurement decisions, simulates shipment quality draws,
    applies transport events, updates ComponentSlot.raw_stock.
    Returns a summary dict for the organiser dashboard.

seed_procurement_memory(db, team)
    Creates the MemoryProcurement row for a new team with safe defaults.
"""
import random
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session

from core.config import (
    MIN_USABLE_GRADE, PARTIAL_DAMAGE_FRACTION, PARTIAL_DAMAGE_PENALTY,
    QUALITY_MAX, TRANSPORT,
)
from core.enums import ComponentType
from models.game import RawMaterialSource
from models.procurement import ComponentSlot, MemoryProcurement
from models.deals import Event

from core.enums import EventStatus, EventType, EventPhase


# ── Seeding ───────────────────────────────────────────────────────────────────

# NOTE: do not use this function. Seed the data using json before the start of the game.
def seed_procurement_memory(db: Session, team) -> MemoryProcurement:
    """Create MemoryProcurement row with empty decisions for a new team."""
    mem = MemoryProcurement(team_id=team.id, decisions={})
    db.add(mem)
    db.flush()
    return mem

# NOTE: do not use this function. Seed the data using json before the start of the game.
def seed_component_slots(db: Session, team) -> List[ComponentSlot]:
    """Create one ComponentSlot per component for a new team."""
    slots = []
    for comp in ComponentType:
        slot = ComponentSlot(
            team_id          = team.id,
            component        = comp,
            raw_stock        = [0] * 101,
            finished_stock   = [0] * 101,
            rnd_quality      = 0,
            rnd_consistency  = 0,
            rnd_yield        = 0,
        )
        db.add(slot)
        slots.append(slot)
    db.flush()
    return slots


# ── Event loading ─────────────────────────────────────────────────────────────

def _load_procurement_events(
        db: Session, team_id: int, cycle_id: int
) -> List[Event]:
    """Load all PENDING procurement-phase events for this team+cycle."""
    return (
        db.query(Event)
        .filter(
            Event.cycle_id == cycle_id,
            Event.target_team_id == team_id,
            Event.phase == EventPhase.PROCUREMENT,
            Event.status == EventStatus.PENDING,
        )
        .all()
    )


def _mark_applied(events: List[Event]) -> None:
    now = datetime.utcnow()
    for ev in events:
        ev.status = EventStatus.APPLIED
        ev.applied_at = now


# ── Per-component event helpers ───────────────────────────────────────────────

def _get_component_modifiers(
        events: List[Event], comp_val: str
) -> Dict:
    """
    Aggregate all event modifiers relevant to one component.
    Returns a dict of modifiers to apply during that component's processing.

    Modifiers:
        mean_bonus          : float   added to source quality_mean
        cost_multiplier     : float   applied to total procurement cost
        loss_fraction       : float   fraction of units sabotaged to scrap
    """
    mods = {
        "mean_bonus": 0.0,
        "cost_multiplier": 1.0,
        "loss_fraction": 0.0,
    }

    for ev in events:
        p = ev.payload or {}
        # Events without a "component" key are global for this team.
        # Events with a "component" key only apply to that component.
        if "component" in p and p["component"] != comp_val:
            continue

        if ev.event_type == EventType.PRIORITY_SUPPLY:
            mods["mean_bonus"] += p.get("mean_bonus", 0.0)

        elif ev.event_type == EventType.PRICE_INFLATION:
            mods["cost_multiplier"] *= p.get("cost_multiplier", 1.0)

        elif ev.event_type == EventType.SUBSIDISED_INPUTS:
            mods["cost_multiplier"] *= p.get("cost_multiplier", 1.0)

        elif ev.event_type == EventType.SUPPLY_SABOTAGE:
            # Take the worst (highest) sabotage fraction — they don't stack
            # beyond the single worst attack.
            mods["loss_fraction"] = max(
                mods["loss_fraction"],
                p.get("loss_fraction", 0.0),
            )

    return mods


# ── Quality draw ──────────────────────────────────────────────────────────────

def _draw_quality_array(
        mean: float, sigma: float, quantity: int,
        rng: np.random.Generator,
) -> List[int]:
    """Draw `quantity` units from N(mean, sigma), return 101-int array."""
    if quantity <= 0:
        return [0] * 101
    draws = rng.normal(loc=mean, scale=max(0.5, sigma), size=quantity)
    arr = [0] * 101
    for v in draws:
        g = int(np.clip(v, 0, QUALITY_MAX))
        arr[g] += 1
    # Units below MIN_USABLE_GRADE go to scrap bucket
    for g in range(0, MIN_USABLE_GRADE):
        arr[0] += arr[g]
        if g > 0:
            arr[g] = 0
    return arr


# ── Transport cost (distance-aware) ──────────────────────────────────────────

def _compute_transport_cost(
        quantity: int,
        base_cost_per_unit: float,
        distance_km: float,
        transport: str,
        cost_multiplier: float,
) -> float:
    """
    total_cost = material_cost + transport_cost
    transport_cost = fixed_cost + variable_cost_per_unit_per_km × distance × quantity
    The cost_multiplier from events is applied to the entire total.
    """
    t_cfg = TRANSPORT[transport]
    material_cost = quantity * base_cost_per_unit
    transport_cost = (
            t_cfg["base_cost"]
            + t_cfg["var_cost"] * distance_km * quantity
    )
    return round((material_cost + transport_cost) * cost_multiplier, 2)


# ── Event-driven loss application ─────────────────────────────────────────────

def _apply_sabotage_loss(
        quality_array: List[int], loss_fraction: float
) -> List[int]:
    """Move loss_fraction of usable units to the scrap bucket (index 0)."""
    if loss_fraction <= 0:
        return quality_array
    arr = list(quality_array)
    total = sum(arr[1:])
    to_lose = int(total * loss_fraction)
    remaining = to_lose
    for g in range(QUALITY_MAX, 0, -1):
        if remaining <= 0:
            break
        take = min(arr[g], remaining)
        arr[g] -= take
        arr[0] += take
        remaining -= take
    return arr


def _apply_partial_damage(quality_array: List[int]) -> List[int]:
    """Damage PARTIAL_DAMAGE_FRACTION of units by PARTIAL_DAMAGE_PENALTY grades."""
    arr = list(quality_array)
    total = sum(arr[1:])
    to_damage = int(total * PARTIAL_DAMAGE_FRACTION)
    remaining = to_damage
    for g in range(QUALITY_MAX, 0, -1):
        if remaining <= 0:
            break
        take = min(arr[g], remaining)
        arr[g] -= take
        new_g = max(0, g - PARTIAL_DAMAGE_PENALTY)
        if new_g < MIN_USABLE_GRADE:
            new_g = 0
        arr[new_g] += take
        remaining -= take
    return arr


# ── Main resolution ───────────────────────────────────────────────────────────


def resolve_procurement(
    db:    Session,
    team,
    cycle,
    rng:   Optional[np.random.Generator] = None,
) -> Dict:
    """
    For each component in MemoryProcurement.decisions:
      1. Load the source.
      2. Draw a quality array from N(mean, sigma+transport_sigma_add).
      3. Apply total loss, then partial damage events.
      4. Merge new array into ComponentSlot.raw_stock.
      5. Deduct cost from Inventory.funds.

    Returns a per-component summary dict.
    """
    if rng is None:
        rng = np.random.default_rng()

    mem: MemoryProcurement = (
        db.query(MemoryProcurement)
        .filter(MemoryProcurement.team_id == team.id)
        .first()
    )
    if not mem or not mem.decisions:
        return {}

    from models.procurement import Inventory
    inventory = db.query(Inventory).filter(Inventory.team_id == team.id).first()

    # Load and aggregate all procurement events for this team+cycle
    events = _load_procurement_events(db, team.id, cycle.id)

    total_cost = 0.0
    summary    = {}

    for comp_val, decision in mem.decisions.items():
        source_id = decision.get("source_id")
        quantity  = decision.get("quantity", 0)
        transport = decision.get("transport", "road")

        if quantity == 0:
            summary[comp_val] = {"units_ordered": 0, "units_received": 0, "cost": 0.0}
            continue

        source: RawMaterialSource = (
            db.query(RawMaterialSource)
            .filter(
                RawMaterialSource.id      == source_id,
                RawMaterialSource.is_active == True,
            )
            .first()
        )
        if source is None:
            summary[comp_val] = {
                "units_ordered": quantity, "units_received": 0, "cost": 0.0,
                "event": "source_unavailable",
            }
            continue

        t_cfg = TRANSPORT[transport]
        if t_cfg is None:
            summary[comp_val] = {
                "units_ordered": quantity, "units_received": 0, "cost": 0.0,
                "event": "invalid_transport",
            }
            continue

            # Aggregate event modifiers for this component
        mods = _get_component_modifiers(events, comp_val)

        # ── Quality draw ──────────────────────────────────────────────────────
        effective_mean = source.quality_mean + mods["mean_bonus"] - t_cfg["mean_reduce"]
        effective_sigma = source.quality_sigma + t_cfg["sigma_add"]
        quality_array = _draw_quality_array(
            effective_mean, effective_sigma, quantity, rng
        )

        event_label = "none"

        # ── Transport loss events ─────────────────────────────────────────────
        # Partial damage
        if random.random() < t_cfg["p_damage"]:
            quality_array = _apply_partial_damage(quality_array)
            event_label = "partial_damage"

        # Supply sabotage (applied after transport events)
        effective_sabotage = mods["loss_fraction"] * t_cfg["vulnerability"]
        if effective_sabotage > 0:
            quality_array = _apply_sabotage_loss(quality_array, effective_sabotage)
            if event_label == "none":
                event_label = "sabotaged"

        units_received = sum(quality_array[1:])

        # ── Merge into raw_stock ──────────────────────────────────────────────
        slot: ComponentSlot = (
            db.query(ComponentSlot)
            .filter(
                ComponentSlot.team_id == team.id,
                ComponentSlot.component == comp_val,
            )
            .first()
        )
        if slot is None:
            summary[comp_val] = {"error": "component_slot_missing"}
            continue

        existing = slot.raw_stock or [0] * 101
        slot.raw_stock = [existing[i] + quality_array[i] for i in range(101)]

        # ── Cost ──────────────────────────────────────────────────────────────
        distance_km = getattr(source, "distance", 500.0)
        cost = _compute_transport_cost(
            quantity, source.base_cost_per_unit,
            distance_km, transport,
            mods["cost_multiplier"],
        )
        total_cost += cost

        summary[comp_val] = {
            "units_ordered": quantity,
            "units_received": units_received,
            "cost": cost,
            "event": event_label,
            "source": source.name,
            "transport": transport,
            "distance_km": distance_km,
        }
    # Deduct total procurement cost (allow going negative — dealt with in backroom)
    if inventory:
        inventory.funds = round(inventory.funds - total_cost, 2)

    # ── Mark all procurement events as applied ────────────────────────────────
    _mark_applied(events)

    db.flush()
    return {"per_component": summary, "total_cost": round(total_cost, 2)}