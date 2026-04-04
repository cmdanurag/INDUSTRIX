"""
routers/team/production.py
==========================
GET   /team/production   — view current decisions
PATCH /team/production   — update decisions (partial)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import verify_team
from core.database import get_db
from core.enums import CyclePhase
from models.game import Cycle, Game, Team
from models.production import MemoryProduction
from schemas.common import OkResponse
from schemas.production import ProductionMemoryOut, ProductionPatch

router = APIRouter(prefix="/team/production", tags=["team"])


def _assert_phase(db: Session, team: Team, expected: CyclePhase) -> Cycle:
    game  = db.query(Game).filter(Game.id == team.game_id,
                                   Game.is_active == True).first()
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


@router.get("", response_model=ProductionMemoryOut)
def get_decisions(
    team: Team    = Depends(verify_team),
    db:   Session = Depends(get_db),
):
    mem = db.query(MemoryProduction).filter(
        MemoryProduction.team_id == team.id
    ).first()
    return ProductionMemoryOut(decisions=mem.decisions if mem else {})


@router.patch("", response_model=OkResponse)
def patch_decisions(
    body: ProductionPatch,
    team: Team    = Depends(verify_team),
    db:   Session = Depends(get_db),
):
    _assert_phase(db, team, CyclePhase.PRODUCTION_OPEN)

    mem = db.query(MemoryProduction).filter(
        MemoryProduction.team_id == team.id
    ).first()
    if mem is None:
        raise HTTPException(500, "Production memory not initialised.")

    current = dict(mem.decisions or {})

    # Merge component decisions
    for comp_val, dec in body.component_decisions.items():
        if comp_val not in current:
            print("Hello")
            current[comp_val] = {}
        current[comp_val] = dec.dict()

    # Merge top-level labour fields
    if body.wage_level is not None:
        current["wage_level"] = body.wage_level.value
    if body.target_headcount is not None:
        current["target_headcount"] = body.target_headcount
    if body.upgrade_automation is not None:
        current["upgrade_automation"] = body.upgrade_automation.value

    mem.decisions = current
    db.commit()

    return OkResponse(message="Production decisions updated.")