"""
industrix/services/procurement_service.py
==========================================
The procurement simulation engine.

Public API (called by the cycle orchestrator):
  seed_default_decisions(db, team)
      → Create default ProcurementDecision rows for a new team.

  compute_order_cost(source, transport_mode, quantity)
      → Deterministic cost calculation. Called on every decision update
        so teams always see their estimated cost.

  resolve_procurement(db, team, cycle, sabotage_targets)
      → Called once per team when the organiser triggers cycle resolution.
        Reads ProcurementDecision rows, creates ProcurementOrder rows,
        simulates shipments, writes ShipmentResult rows.
        Returns a CycleProcurementReport for the team's debrief.

Internal helpers (not exported):
  _draw_quality_array   — Normal distribution draw into 101-int array
  _apply_transit_damage — Partial damage event
  _apply_total_loss     — Full loss event
  _apply_sabotage       — Rival-funded sabotage
  _compute_summary_stats — Derived fields for ShipmentResult
"""

import random
from typing import Dict, List, Optional, Tuple

import numpy as np

from sqlalchemy.orm import Session

from core.config import (
    MIN_USABLE_GRADE,
    PARTIAL_DAMAGE_FRACTION,
    PARTIAL_DAMAGE_GRADE_PENALTY,
    QUALITY_MAX,
    SABOTAGE_DEFAULT_LOSS_FRACTION,
    TRANSPORT_CONFIG,
)
from core.enums import ComponentType, ShipmentEventType, TransportMode
from models.procurement import (
    ProcurementDecision,
    ProcurementOrder,
    RawMaterialSource,
    ShipmentResult,
    Team,
)
from schemas.procurement import (
    CycleProcurementReport,
    ProcurementOrderOut,
    ShipmentResultOut,
)


# ─────────────────────────────────────────────────────────────────────────────
# Default decision seeds
# ─────────────────────────────────────────────────────────────────────────────

# Default standing decisions for a new team joining Cycle 1.
# All components start with no source selected and zero quantity.
# Teams must actively choose to buy before their first cycle.
DEFAULT_DECISIONS = {
    component: {
        "source_id":      None,
        "quantity":       0,
        "transport_mode": TransportMode.ROAD,
    }
    for component in ComponentType
}

#TODO: Attend to the use of this function later.
def seed_default_decisions(db: Session, team: Team):
    """
    Create one ProcurementDecision row per component for a new team.
    Called once when the team is added to the game.
    Uses hardcoded sensible defaults (no procurement — team must opt in).
    """
    rows = []
    for component, defaults in DEFAULT_DECISIONS.items():
        decision = ProcurementDecision(
            team_id        = team.id,
            component      = component,
            source_id      = defaults["source_id"],
            quantity       = defaults["quantity"],
            transport_mode = defaults["transport_mode"],
        )
        db.add(decision)
        rows.append(decision)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Cost computation  (deterministic, called on every decision update)
# ─────────────────────────────────────────────────────────────────────────────

def compute_order_cost(
    source:         RawMaterialSource,
    transport_mode: TransportMode,
    quantity:       int,
) -> Tuple[float, float]:
    """
    Compute the deterministic cost of a procurement order.

    Cost formula:
        unit_cost  = source.base_cost_per_unit * transport_config.cost_multiplier
        total_cost = unit_cost * quantity

    The cost does NOT depend on quality — teams always pay the same price
    per unit regardless of what quality grade is actually drawn.

    Args:
        source:         The RawMaterialSource being ordered from.
        transport_mode: The chosen transport mode.
        quantity:       Number of units being ordered.

    Returns:
        (unit_cost, total_cost)
    """
    t_cfg     = TRANSPORT_CONFIG[transport_mode.value]
    unit_cost = source.base_cost_per_unit * t_cfg.cost_multiplier
    return round(unit_cost, 4), round(unit_cost * quantity, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Quality array simulation  (stochastic)
# ─────────────────────────────────────────────────────────────────────────────

def _draw_quality_array(
    quality_mean:    float,
    quality_sigma:   float,
    transport_mode:  TransportMode,
    quantity:        int,
    rng:             Optional[np.random.Generator] = None,
) -> List[int]:
    """
    Draw a 101-integer quality distribution array for a shipment.

    Process:
      1. Sample `quantity` values from Normal(quality_mean, effective_sigma).
         effective_sigma = quality_sigma + transport_config.damage_sigma_add
         (transport adds extra variance due to handling / vibration / delays)
      2. Round each sample to nearest integer and clamp to [0, QUALITY_MAX].
      3. Samples that fall below MIN_USABLE_GRADE go to index 0 (unusable).
      4. All other samples increment the count at their grade index.

    Args:
        quality_mean:   Source's mean quality (1–100 scale).
        quality_sigma:  Source's base sigma.
        transport_mode: Determines additional sigma from handling.
        quantity:       Number of units in the shipment.
        rng:            Optional numpy Generator for reproducibility in tests.

    Returns:
        List of 101 integers. Index 0 = unusable. Index 1–100 = grade counts.
    """
    if quantity <= 0:
        return [0] * 101

    if rng is None:
        rng = np.random.default_rng()

    t_cfg          = TRANSPORT_CONFIG[transport_mode.value]
    effective_sigma = quality_sigma + t_cfg.damage_sigma_add

    # Draw all grades at once — vectorised, fast even for large quantities.
    raw_grades = rng.normal(loc=quality_mean, scale=effective_sigma, size=quantity)

    # Build the array.
    array = [0] * 101
    for g in raw_grades:
        grade = int(round(g))
        grade = max(0, min(QUALITY_MAX, grade))   # Clamp to [0, 100]
        if grade < MIN_USABLE_GRADE:
            # Grade 0 or below MIN_USABLE_GRADE → unusable bucket.
            array[0] += 1
        else:
            array[grade] += 1

    return array


# ─────────────────────────────────────────────────────────────────────────────
# Damage and loss events
# ─────────────────────────────────────────────────────────────────────────────

def _apply_partial_damage(array: List[int]) -> List[int]:
    """
    Simulate a partial damage event during transit.

    PARTIAL_DAMAGE_FRACTION of usable units have their grade reduced
    by PARTIAL_DAMAGE_GRADE_PENALTY. Units whose grade falls below
    MIN_USABLE_GRADE after the penalty are moved to index 0.

    The array is modified in-place and returned.
    """
    # Identify usable units (indices 1–100) and pick a random subset to damage.
    usable_units: List[Tuple[int, int]] = []   # (grade, count)
    for grade in range(MIN_USABLE_GRADE, QUALITY_MAX + 1):
        if array[grade] > 0:
            usable_units.append((grade, array[grade]))

    total_usable = sum(c for _, c in usable_units)
    n_to_damage  = int(round(total_usable * PARTIAL_DAMAGE_FRACTION))

    if n_to_damage == 0:
        return array

    # Build a flat list of grades, shuffle, pick the first n_to_damage.
    flat_grades = []
    for grade, count in usable_units:
        flat_grades.extend([grade] * count)
    random.shuffle(flat_grades)

    for grade in flat_grades[:n_to_damage]:
        # Remove one unit from original grade.
        array[grade] -= 1
        # Apply penalty.
        new_grade = grade - PARTIAL_DAMAGE_GRADE_PENALTY
        if new_grade < MIN_USABLE_GRADE:
            array[0] += 1   # Falls to unusable
        else:
            array[new_grade] += 1

    return array


def _apply_total_loss(array: List[int]) -> List[int]:
    """
    Simulate total shipment loss.
    Every usable unit is moved to index 0. Returns the collapsed array.
    """
    total = sum(array)
    return [total] + [0] * 100


def _apply_sabotage(array: List[int], loss_fraction: float) -> List[int]:
    """
    Simulate a rival-funded government sabotage on this shipment.

    `loss_fraction` of usable units are moved to index 0 (destroyed/seized).
    The fraction is set in the GovDeal that paid for this action.
    Args:
        array:         The quality array (modified in-place and returned).
        loss_fraction: Fraction of usable units to destroy (0.0–1.0).
    """
    loss_fraction = max(0.0, min(1.0, loss_fraction))
    total_usable  = sum(array[1:])
    n_to_destroy  = int(round(total_usable * loss_fraction))

    if n_to_destroy == 0:
        return array

    # Destroy units starting from the best grades (maximum pain for the target).
    remaining = n_to_destroy
    for grade in range(QUALITY_MAX, MIN_USABLE_GRADE - 1, -1):
        if remaining <= 0:
            break
        take = min(array[grade], remaining)
        array[grade]  -= take
        array[0]      += take
        remaining     -= take

    return array


# ─────────────────────────────────────────────────────────────────────────────
# Summary statistics
# ─────────────────────────────────────────────────────────────────────────────

def _compute_summary_stats(array: List[int]) -> Dict:
    """
    Compute derived summary fields from a 101-integer quality array.

    Returns a dict with:
        total_usable, total_lost, weighted_mean, min_grade, max_grade
    """
    total_lost   = array[0]
    total_usable = sum(array[1:])

    if total_usable == 0:
        return {
            "total_usable":  0,
            "total_lost":    total_lost,
            "weighted_mean": None,
            "min_grade":     None,
            "max_grade":     None,
        }

    total_quality = sum(grade * array[grade] for grade in range(1, 101) if array[grade] > 0)
    weighted_mean = total_quality / total_usable

    grades_with_stock = [g for g in range(1, 101) if array[g] > 0]
    min_grade = min(grades_with_stock) if grades_with_stock else None
    max_grade = max(grades_with_stock) if grades_with_stock else None

    return {
        "total_usable":  total_usable,
        "total_lost":    total_lost,
        "weighted_mean": round(weighted_mean, 2),
        "min_grade":     min_grade,
        "max_grade":     max_grade,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main resolver — called by the cycle orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def resolve_procurement(
    db:                Session,
    team:              Team,
    cycle,             # Cycle ORM object
    sabotage_targets:  Dict[int, float],
    # sabotage_targets: { procurement_decision_source_id_or_order_id: loss_fraction }
    # Key is source_id being targeted for this team this cycle.
    # Built by the orchestrator from active GovDeal rows before calling here.
    rng:               Optional[np.random.Generator] = None,
) -> CycleProcurementReport:
    """
    Resolve all procurement for one team in one cycle.

    Steps per component:
      1. Load the team's ProcurementDecision.
      2. If source_id is null or quantity is 0 — skip (no order).
      3. Create a ProcurementOrder (snapshot of decision + computed cost).
      4. Load the source (with current parameters — may have changed from events).
      5. Draw the quality array from Normal(mean, effective_sigma).
      6. Roll for transit events (total loss → partial damage, in that order).
      7. Apply sabotage if the source was targeted this cycle.
      8. Compute summary stats.
      9. Write ShipmentResult.

    Args:
        db:               Database session.
        team:             The Team ORM object.
        cycle:            The Cycle ORM object being resolved.
        sabotage_targets: Dict mapping source_id → loss_fraction for
                          any shipments sabotaged this cycle for this team.
        rng:              Optional numpy RNG (for deterministic tests).

    Returns:
        CycleProcurementReport — the full debrief data for this team.
    """
    if rng is None:
        rng = np.random.default_rng()

    decisions: List[ProcurementDecision] = (
        db.query(ProcurementDecision)
          .filter(ProcurementDecision.team_id == team.id)
          .all()
    )

    orders_out:    List[ProcurementOrderOut]  = []
    shipments_out: List[ShipmentResultOut]    = []
    total_cost         = 0.0
    total_units_ordered = 0
    total_units_arrived = 0
    total_units_lost    = 0
    per_component: Dict = {}

    for decision in decisions:
        component_name = decision.component.value

        # ── Skip if no source selected or zero quantity ───────────────────
        if decision.source_id is None or decision.quantity <= 0:
            per_component[component_name] = {
                "ordered": 0, "arrived": 0, "lost": 0, "mean_grade": None,
            }
            continue

        # ── Load source (current parameters) ─────────────────────────────
        source: Optional[RawMaterialSource] = (
            db.query(RawMaterialSource)
              .filter(RawMaterialSource.id == decision.source_id)
              .first()
        )
        if source is None or not source.is_available:
            # Source was disabled between decision and resolution.
            # Treat as zero order — team gets nothing, costs nothing.
            per_component[component_name] = {
                "ordered": 0, "arrived": 0, "lost": 0, "mean_grade": None,
                "note": "Source unavailable at resolution time.",
            }
            continue

        # ── Compute deterministic cost ────────────────────────────────────
        unit_cost, order_total_cost = compute_order_cost(
            source, decision.transport_mode, decision.quantity
        )
        total_cost         += order_total_cost
        total_units_ordered += decision.quantity

        # ── Create ProcurementOrder row ───────────────────────────────────
        order = ProcurementOrder(
            team_id              = team.id,
            cycle_id             = cycle.id,
            source_id            = source.id,
            component            = decision.component,
            transport_mode       = decision.transport_mode,
            quantity_ordered     = decision.quantity,
            unit_cost            = unit_cost,
            total_cost           = order_total_cost,
            source_quality_mean  = source.quality_mean,
            source_quality_sigma = source.quality_sigma,
            shipment_event       = ShipmentEventType.NONE,
            was_sabotaged        = False,
            sabotage_loss_fraction = 0.0,
        )
        db.add(order)
        db.flush()   # Get order.id

        # ── Draw quality array ────────────────────────────────────────────
        array = _draw_quality_array(
            quality_mean   = source.quality_mean,
            quality_sigma  = source.quality_sigma,
            transport_mode = decision.transport_mode,
            quantity       = decision.quantity,
            rng            = rng,
        )

        # ── Roll for transit events ───────────────────────────────────────
        t_cfg = TRANSPORT_CONFIG[decision.transport_mode.value]
        event = ShipmentEventType.NONE

        loss_roll   = rng.random()
        damage_roll = rng.random()

        if loss_roll < t_cfg.p_total_loss:
            array = _apply_total_loss(array)
            event = ShipmentEventType.LOST

        elif damage_roll < t_cfg.p_partial_damage:
            array = _apply_partial_damage(array)
            event = ShipmentEventType.DAMAGED

        order.shipment_event = event

        # ── Apply sabotage if this source was targeted ────────────────────
        loss_fraction = sabotage_targets.get(source.id, 0.0)
        if loss_fraction > 0.0:
            array = _apply_sabotage(array, loss_fraction)
            order.was_sabotaged         = True
            order.sabotage_loss_fraction = loss_fraction
            # Only override event if not already a worse event.
            if event == ShipmentEventType.NONE:
                order.shipment_event = ShipmentEventType.SABOTAGED

        # ── Compute summary statistics ────────────────────────────────────
        stats = _compute_summary_stats(array)

        # ── Write ShipmentResult ──────────────────────────────────────────
        result = ShipmentResult(
            order_id      = order.id,
            quality_array = array,
            **stats,
        )
        db.add(result)

        # ── Accumulate totals ─────────────────────────────────────────────
        total_units_arrived += stats["total_usable"]
        total_units_lost    += stats["total_lost"]

        per_component[component_name] = {
            "ordered":    decision.quantity,
            "arrived":    stats["total_usable"],
            "lost":       stats["total_lost"],
            "mean_grade": stats["weighted_mean"],
        }

        # ── Build output objects ──────────────────────────────────────────
        orders_out.append(ProcurementOrderOut.model_validate(order))
        shipments_out.append(ShipmentResultOut(
            id            = result.id if result.id else 0,   # flushed below
            order_id      = order.id,
            component     = decision.component,
            quality_array = array,
            **stats,
        ))

    db.flush()
    db.commit()

    # Fix result IDs in output (after flush they are available).
    for s_out, decision in zip(shipments_out, [d for d in decisions if d.source_id and d.quantity > 0]):
        pass   # IDs are correct after flush; ShipmentResult.id populated above

    return CycleProcurementReport(
        team_id              = team.id,
        cycle_id             = cycle.id,
        cycle_number         = cycle.cycle_number,
        orders               = orders_out,
        shipments            = shipments_out,
        total_cost           = round(total_cost, 2),
        total_units_ordered  = total_units_ordered,
        total_units_arrived  = total_units_arrived,
        total_units_lost     = total_units_lost,
        per_component_summary = per_component,
    )
