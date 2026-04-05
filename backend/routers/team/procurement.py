"""
routers/team/procurement.py
===========================
GET   /team/procurement        — view current decisions
PATCH /team/procurement        — update decisions (partial)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from typing import Dict, List

from core.auth import verify_team
from core.database import get_db
from core.enums import CyclePhase
from core.config import TRANSPORT
from models.game import Cycle, Game, Team, RawMaterialSource
from models.procurement import MemoryProcurement
from schemas.common import OkResponse
from schemas.procurement import ProcurementMemoryOut, ProcurementPatch, RawMaterialSourceOut, TransportOut, CostProjectionOut

router = APIRouter(prefix="/team/procurement", tags=["team"])


def _assert_phase(db: Session, team: Team, expected: CyclePhase) -> Cycle:
    game  = db.query(Game).filter(Game.id == team.game_id, Game.is_active == True).first()
    cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    if not cycle or cycle.phase_log.current_phase != expected:
        raise HTTPException(
            400,
            f"Action only allowed during {expected.value}. "
            f"Current: {cycle.phase_log.current_phase.value if cycle else 'none'}",
        )
    return cycle

@router.get("/transports", response_model=Dict[str, TransportOut])
def get_transports(
        team: Team = Depends(verify_team),
        db : Session = Depends(get_db),
):
    transports = TRANSPORT
    dct: Dict[str, TransportOut] = {}
    for key, value in transports.items():
        dct[key] = TransportOut(**value)
    return dct

@router.get("/sources", response_model=List[RawMaterialSourceOut])
def get_sources(
        team: Team = Depends(verify_team),
        db: Session = Depends(get_db),
):
    """
    Return all active raw material sources for this game.

    This is the catalogue the team browses when filling in their procurement
    decisions. Only called during PROCUREMENT_OPEN, but not phase-gated —
    teams may also want to inspect sources during PRODUCTION_OPEN to plan
    ahead for the next cycle.

    Only components that have at least one active source appear as keys.
    """
    sources = (
        db.query(RawMaterialSource)
        .filter(
            RawMaterialSource.game_id == team.game_id,
            RawMaterialSource.is_active == True,
        )
        .order_by(RawMaterialSource.component, RawMaterialSource.name)
        .all()
    )

    grouped: List[RawMaterialSourceOut] = []
    for src in sources:
        grouped.append(RawMaterialSourceOut.from_orm(src))
    return grouped


@router.get("", response_model=ProcurementMemoryOut)
def get_decisions(
    team: Team    = Depends(verify_team),
    db:   Session = Depends(get_db),
):
    mem = db.query(MemoryProcurement).filter(
        MemoryProcurement.team_id == team.id
    ).first()
    return ProcurementMemoryOut(decisions=mem.decisions if mem else {})


@router.patch("", response_model=OkResponse)
def patch_decisions(
    body: ProcurementPatch,
    team: Team    = Depends(verify_team),
    db:   Session = Depends(get_db),
):
    _assert_phase(db, team, CyclePhase.PROCUREMENT_OPEN)

    mem = db.query(MemoryProcurement).filter(
        MemoryProcurement.team_id == team.id
    ).first()
    if mem is None:
        raise HTTPException(500, "Procurement memory not initialised.")

    # PATCH: merge incoming decisions over existing ones
    current = dict(mem.decisions or {})
    for comp_val, decision in body.decisions.items():
        current[comp_val] = decision.dict()
    mem.decisions = current
    db.commit()
    return OkResponse(message="Procurement decisions updated.")

@router.post("/project", response_model=CostProjectionOut)
def project_costs(
    body: ProcurementPatch,
    team: Team    = Depends(verify_team),
    db:   Session = Depends(get_db),
):
    cycle = _assert_phase(db, team, CyclePhase.PROCUREMENT_OPEN)
    
    from services.procurement import _load_procurement_events, _get_component_modifiers
    from core.config import TRANSPORT

    events = _load_procurement_events(db, team.id, cycle.id)
    
    total_cost = 0.0
    summary = {}
    
    for comp_val, decision in body.decisions.items():
        source_id = decision.source_id
        quantity  = decision.quantity
        transport_mode = decision.transport.value if hasattr(decision.transport, "value") else decision.transport
        
        if quantity == 0:
            summary[comp_val] = {"material_cost": 0.0, "transport_cost": 0.0, "total": 0.0}
            continue
            
        source = db.query(RawMaterialSource).filter(RawMaterialSource.id == source_id).first()
        if not source:
            summary[comp_val] = {"material_cost": 0.0, "transport_cost": 0.0, "total": 0.0}
            continue
            
        mods = _get_component_modifiers(events, comp_val)
        distance_km = getattr(source, "distance", 500.0)
        
        t_cfg = TRANSPORT.get(transport_mode)
        if not t_cfg:
            summary[comp_val] = {"material_cost": 0.0, "transport_cost": 0.0, "total": 0.0}
            continue

        raw_material_cost = quantity * source.base_cost_per_unit
        raw_transport_cost = t_cfg["base_cost"] + (t_cfg["var_cost"] * distance_km * quantity)
        
        final_total = round((raw_material_cost + raw_transport_cost) * mods["cost_multiplier"], 2)
        
        summary[comp_val] = {
            "material_cost": raw_material_cost * mods["cost_multiplier"],
            "transport_cost": raw_transport_cost * mods["cost_multiplier"],
            "total": final_total,
        }
        total_cost += final_total
        
    return CostProjectionOut(total_cost=round(total_cost, 2), per_component=summary)