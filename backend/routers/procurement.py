"""
industrix/routers/procurement.py
==================================
FastAPI router for the procurement subsystem.

Endpoints:

  ORGANISER (game master / corrupt government):
    POST   /games/{game_id}/sources                   — add a source
    GET    /games/{game_id}/sources                   — list all sources
    PATCH  /games/{game_id}/sources/{source_id}       — modify source (event)
    DELETE /games/{game_id}/sources/{source_id}       — disable source

  TEAMS:
    GET    /teams/{team_id}/procurement               — view all current decisions
    PATCH  /teams/{team_id}/procurement/{component}   — update one component decision
    GET    /teams/{team_id}/procurement/cost-estimate — see total estimated cost

  RESULTS (read after cycle resolution):
    GET    /cycles/{cycle_id}/procurement/{team_id}   — full shipment report
    GET    /cycles/{cycle_id}/procurement/{team_id}/shipment/{component}
                                                      — single component shipment array
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.enums import ComponentType
from models.procurement import (
    Cycle, Game, ProcurementDecision, ProcurementOrder,
    RawMaterialSource, ShipmentResult, SourceEventLog, Team,
)
from schemas.procurement import (
    AllProcurementDecisionsOut,
    CycleProcurementReport,
    ProcurementDecisionOut,
    ProcurementDecisionUpdate,
    ProcurementOrderOut,
    ShipmentResultOut,
    SourceCreate,
    SourceEventLogOut,
    SourceOut,
    SourceUpdate,
)
from services.procurement_service import compute_order_cost

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_game(db: Session, game_id: int) -> Game:
    g = db.query(Game).filter(Game.id == game_id).first()
    if not g:
        raise HTTPException(404, f"Game {game_id} not found.")
    return g


def _get_team(db: Session, team_id: int) -> Team:
    t = db.query(Team).filter(Team.id == team_id).first()
    if not t:
        raise HTTPException(404, f"Team {team_id} not found.")
    return t


def _get_source(db: Session, source_id: int, game_id: int) -> RawMaterialSource:
    s = db.query(RawMaterialSource).filter(
        RawMaterialSource.id      == source_id,
        RawMaterialSource.game_id == game_id,
    ).first()
    if not s:
        raise HTTPException(404, f"Source {source_id} not found in game {game_id}.")
    return s


def _enrich_decision(
    decision: ProcurementDecision,
    db:       Session,
) -> ProcurementDecisionOut:
    """
    Build a ProcurementDecisionOut from a ProcurementDecision ORM row,
    joining to the source for name and computing estimated cost.
    """
    source_name = None
    est_unit    = None
    est_total   = None

    if decision.source_id:
        source = db.query(RawMaterialSource).filter(
            RawMaterialSource.id == decision.source_id
        ).first()
        if source:
            source_name = source.name
            if decision.quantity > 0:
                est_unit, est_total = compute_order_cost(
                    source, decision.transport_mode, decision.quantity
                )

    return ProcurementDecisionOut(
        id                   = decision.id,
        team_id              = decision.team_id,
        component            = decision.component,
        source_id            = decision.source_id,
        source_name          = source_name,
        quantity             = decision.quantity,
        transport_mode       = decision.transport_mode,
        estimated_unit_cost  = est_unit,
        estimated_total_cost = est_total,
        updated_at           = decision.updated_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ORGANISER — source management
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/games/{game_id}/sources",
    response_model = SourceOut,
    status_code    = 201,
    summary        = "Add a raw material source to the game",
    tags           = ["Organiser / Sources"],
)
def create_source(
    game_id: int,
    body:    SourceCreate,
    db:      Session = Depends(get_db),
):
    """
    Organiser pre-configures a raw material source for a specific component.
    All teams will see this source when making procurement decisions.

    Can be called at any time, including between cycles.
    """
    _get_game(db, game_id)
    source = RawMaterialSource(game_id=game_id, **body.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get(
    "/games/{game_id}/sources",
    response_model = List[SourceOut],
    summary        = "List all sources for a game",
    tags           = ["Organiser / Sources", "Teams / Procurement"],
)
def list_sources(
    game_id:   int,
    component: Optional[ComponentType] = Query(None, description="Filter by component type"),
    available_only: bool = Query(True,  description="If True, hide disabled sources"),
    db:        Session = Depends(get_db),
):
    """
    Returns all raw material sources for the game.
    Teams use this to see what sources they can order from.
    Organiser uses this to see the full picture including disabled sources.
    """
    _get_game(db, game_id)
    q = db.query(RawMaterialSource).filter(RawMaterialSource.game_id == game_id)
    if component:
        q = q.filter(RawMaterialSource.component == component)
    if available_only:
        q = q.filter(RawMaterialSource.is_available == True)
    return q.order_by(RawMaterialSource.component, RawMaterialSource.name).all()


@router.patch(
    "/games/{game_id}/sources/{source_id}",
    response_model = SourceOut,
    summary        = "Modify a source's parameters (triggers an event log entry)",
    tags           = ["Organiser / Sources"],
)
def update_source(
    game_id:   int,
    source_id: int,
    body:      SourceUpdate,
    db:        Session = Depends(get_db),
):
    """
    Organiser modifies a source between cycles.
    Examples: over-extraction event (quality degrades), supply disruption (price rises),
    new infrastructure (quality improves).

    Every modification is logged in SourceEventLog for transparency.
    Changes take effect immediately — they will apply to the NEXT cycle's orders.
    """
    source = _get_source(db, source_id, game_id)

    # Get current cycle for the event log (may be None between cycles).
    latest_cycle = (
        db.query(Cycle)
          .filter(Cycle.game_id == game_id)
          .order_by(Cycle.cycle_number.desc())
          .first()
    )

    # Compute deltas for the event log before applying changes.
    qm_delta  = None
    qs_delta  = None
    cost_mult = None

    if body.quality_mean is not None:
        qm_delta = body.quality_mean - source.quality_mean
        source.quality_mean = body.quality_mean

    if body.quality_sigma is not None:
        qs_delta = body.quality_sigma - source.quality_sigma
        source.quality_sigma = body.quality_sigma

    if body.base_cost_per_unit is not None:
        cost_mult = body.base_cost_per_unit / source.base_cost_per_unit
        source.base_cost_per_unit = body.base_cost_per_unit

    avail_change = None
    if body.is_available is not None:
        avail_change = body.is_available
        source.is_available = body.is_available

    # Log the event.
    log = SourceEventLog(
        source_id           = source.id,
        cycle_id            = latest_cycle.id if latest_cycle else None,
        event_name          = body.event_name,
        description         = body.description,
        quality_mean_delta  = round(qm_delta,  4) if qm_delta  is not None else None,
        quality_sigma_delta = round(qs_delta,  4) if qs_delta  is not None else None,
        cost_multiplier     = round(cost_mult, 4) if cost_mult is not None else None,
        availability_change = avail_change,
    )
    db.add(log)
    db.commit()
    db.refresh(source)
    return source


@router.get(
    "/games/{game_id}/sources/{source_id}/events",
    response_model = List[SourceEventLogOut],
    summary        = "Get the event history for a source",
    tags           = ["Organiser / Sources"],
)
def get_source_events(
    game_id:   int,
    source_id: int,
    db:        Session = Depends(get_db),
):
    """Full history of organiser-triggered modifications to this source."""
    source = _get_source(db, source_id, game_id)
    return (
        db.query(SourceEventLog)
          .filter(SourceEventLog.source_id == source.id)
          .order_by(SourceEventLog.created_at.desc())
          .all()
    )


# ─────────────────────────────────────────────────────────────────────────────
# TEAMS — decision management
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/teams/{team_id}/procurement",
    response_model = AllProcurementDecisionsOut,
    summary        = "Get all current procurement decisions for a team",
    tags           = ["Teams / Procurement"],
)
def get_team_decisions(
    team_id: int,
    db:      Session = Depends(get_db),
):
    """
    Returns the team's current standing procurement decisions for all six components.
    Includes estimated costs based on current source parameters.
    This is what the team sees on their decision dashboard.
    """
    team = _get_team(db, team_id)
    decisions = (
        db.query(ProcurementDecision)
          .filter(ProcurementDecision.team_id == team_id)
          .order_by(ProcurementDecision.component)
          .all()
    )

    enriched = [_enrich_decision(d, db) for d in decisions]
    total_estimated = sum(
        d.estimated_total_cost for d in enriched if d.estimated_total_cost
    )

    return AllProcurementDecisionsOut(
        team_id              = team_id,
        decisions            = enriched,
        estimated_total_cost = round(total_estimated, 2),
    )


@router.patch(
    "/teams/{team_id}/procurement/{component}",
    response_model = ProcurementDecisionOut,
    summary        = "Update procurement decision for one component",
    tags           = ["Teams / Procurement"],
)
def update_team_decision(
    team_id:   int,
    component: ComponentType,
    body:      ProcurementDecisionUpdate,
    db:        Session = Depends(get_db),
):
    """
    Team updates their standing procurement decision for one component.
    PATCH semantics — only provided fields are changed.

    This persists between cycles. The decision set here will be used
    in all future cycles until the team changes it again.

    Only callable while the current cycle is OPEN.
    """
    team = _get_team(db, team_id)

    # Ensure the cycle is open (teams cannot change decisions after organiser closes it).
    open_cycle = (
        db.query(Cycle)
          .filter(Cycle.game_id == team.game_id, Cycle.status == "open")
          .order_by(Cycle.cycle_number.desc())
          .first()
    )
    if not open_cycle:
        raise HTTPException(
            400,
            "No open cycle — decisions cannot be changed after the organiser closes a cycle.",
        )

    decision = (
        db.query(ProcurementDecision)
          .filter(
              ProcurementDecision.team_id  == team_id,
              ProcurementDecision.component == component,
          )
          .first()
    )
    if not decision:
        raise HTTPException(404, f"Procurement decision for {component} not found.")

    # Validate source if provided.
    if body.source_id is not None:
        source = db.query(RawMaterialSource).filter(
            RawMaterialSource.id      == body.source_id,
            RawMaterialSource.game_id == team.game_id,
            RawMaterialSource.is_available == True,
        ).first()
        if not source:
            raise HTTPException(
                404,
                f"Source {body.source_id} not found or not available.",
            )
        if source.component != component:
            raise HTTPException(
                400,
                f"Source {body.source_id} supplies '{source.component.value}', "
                f"not '{component.value}'.",
            )
        decision.source_id = body.source_id

    elif body.source_id is None and "source_id" in body.model_fields_set:
        # Explicitly set to null — team is opting out of this component.
        decision.source_id = None

    if body.quantity is not None:
        decision.quantity = body.quantity

    if body.transport_mode is not None:
        decision.transport_mode = body.transport_mode

    db.commit()
    db.refresh(decision)
    return _enrich_decision(decision, db)


@router.get(
    "/teams/{team_id}/procurement/cost-estimate",
    summary = "Get the total estimated procurement cost for the current decisions",
    tags    = ["Teams / Procurement"],
)
def get_cost_estimate(
    team_id: int,
    db:      Session = Depends(get_db),
) -> dict:
    """
    Returns the total estimated procurement cost based on current decisions
    and current source parameters. Useful for teams planning their budget.

    Per-component breakdown is included.
    """
    _get_team(db, team_id)
    decisions = (
        db.query(ProcurementDecision)
          .filter(ProcurementDecision.team_id == team_id)
          .all()
    )

    breakdown = {}
    total = 0.0

    for d in decisions:
        if not d.source_id or d.quantity <= 0:
            breakdown[d.component.value] = {"unit_cost": None, "total_cost": 0.0}
            continue

        source = db.query(RawMaterialSource).filter(
            RawMaterialSource.id == d.source_id
        ).first()
        if not source:
            breakdown[d.component.value] = {"unit_cost": None, "total_cost": 0.0}
            continue

        unit_cost, total_cost = compute_order_cost(source, d.transport_mode, d.quantity)
        breakdown[d.component.value] = {
            "source":     source.name,
            "quantity":   d.quantity,
            "unit_cost":  unit_cost,
            "total_cost": total_cost,
        }
        total += total_cost

    return {
        "team_id":        team_id,
        "total_estimated_cost": round(total, 2),
        "per_component":  breakdown,
    }


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS — read after cycle resolution
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cycles/{cycle_id}/procurement/{team_id}",
    response_model = CycleProcurementReport,
    summary        = "Full procurement report for a team after cycle resolution",
    tags           = ["Results / Procurement"],
)
def get_cycle_procurement_report(
    cycle_id: int,
    team_id:  int,
    db:       Session = Depends(get_db),
):
    """
    Returns the complete procurement result for a team in a resolved cycle.
    This includes all orders, their costs, and the quality arrays of what arrived.
    Shown to the team at the start of the next cycle.
    """
    cycle = db.query(Cycle).filter(Cycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(404, f"Cycle {cycle_id} not found.")
    if cycle.status == "open":
        raise HTTPException(400, "Cycle has not been resolved yet.")

    orders = (
        db.query(ProcurementOrder)
          .filter(
              ProcurementOrder.team_id  == team_id,
              ProcurementOrder.cycle_id == cycle_id,
          )
          .all()
    )

    orders_out:    List[ProcurementOrderOut]  = []
    shipments_out: List[ShipmentResultOut]    = []
    total_cost          = 0.0
    total_units_ordered = 0
    total_units_arrived = 0
    total_units_lost    = 0
    per_component: dict = {}

    for order in orders:
        orders_out.append(ProcurementOrderOut.model_validate(order))
        total_cost          += order.total_cost
        total_units_ordered += order.quantity_ordered

        result: Optional[ShipmentResult] = order.result
        if result:
            shipments_out.append(ShipmentResultOut(
                id            = result.id,
                order_id      = order.id,
                component     = order.component,
                quality_array = result.quality_array,
                total_usable  = result.total_usable,
                total_lost    = result.total_lost,
                weighted_mean = result.weighted_mean,
                min_grade     = result.min_grade,
                max_grade     = result.max_grade,
            ))
            total_units_arrived += result.total_usable
            total_units_lost    += result.total_lost
            per_component[order.component.value] = {
                "ordered":    order.quantity_ordered,
                "arrived":    result.total_usable,
                "lost":       result.total_lost,
                "mean_grade": result.weighted_mean,
            }

    return CycleProcurementReport(
        team_id               = team_id,
        cycle_id              = cycle_id,
        cycle_number          = cycle.cycle_number,
        orders                = orders_out,
        shipments             = shipments_out,
        total_cost            = round(total_cost, 2),
        total_units_ordered   = total_units_ordered,
        total_units_arrived   = total_units_arrived,
        total_units_lost      = total_units_lost,
        per_component_summary = per_component,
    )


@router.get(
    "/cycles/{cycle_id}/procurement/{team_id}/{component}",
    summary = "Get the quality array for one component's shipment",
    tags    = ["Results / Procurement"],
)
def get_shipment_array(
    cycle_id:  int,
    team_id:   int,
    component: ComponentType,
    db:        Session = Depends(get_db),
) -> dict:
    """
    Returns the raw 101-integer quality array for one component's shipment.
    Index 0 = lost/unusable. Index 1–100 = count of units at each grade.
    """
    order = (
        db.query(ProcurementOrder)
          .filter(
              ProcurementOrder.team_id  == team_id,
              ProcurementOrder.cycle_id == cycle_id,
              ProcurementOrder.component == component,
          )
          .first()
    )
    if not order:
        raise HTTPException(
            404,
            f"No procurement order for component '{component.value}' in cycle {cycle_id}.",
        )
    if not order.result:
        raise HTTPException(
            404,
            "Shipment result not yet available — cycle may not be resolved.",
        )

    return {
        "team_id":      team_id,
        "cycle_id":     cycle_id,
        "component":    component.value,
        "quality_array": order.result.quality_array,
        "total_usable":  order.result.total_usable,
        "total_lost":    order.result.total_lost,
        "weighted_mean": order.result.weighted_mean,
        "min_grade":     order.result.min_grade,
        "max_grade":     order.result.max_grade,
        "shipment_event": order.shipment_event.value,
        "was_sabotaged":  order.was_sabotaged,
    }

