"""
routers/team/sales.py
=====================
GET   /team/sales   — view current decisions
PATCH /team/sales   — update decisions (partial)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import verify_team
from core.database import get_db
from core.enums import CyclePhase
from models.game import Cycle, Game, Team
from models.sales import MemorySales
from schemas.common import OkResponse
from schemas.sales import SalesMemoryOut, SalesPatch

router = APIRouter(prefix="/team/sales", tags=["team"])


def _assert_phase(db: Session, team: Team, expected: CyclePhase) -> Cycle:
    game  = db.query(Game).filter(Game.id == team.game_id,Game.is_active == True).first()
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


@router.get("", response_model=SalesMemoryOut)
def get_decisions(
    team: Team    = Depends(verify_team),
    db:   Session = Depends(get_db),
):
    mem = db.query(MemorySales).filter(MemorySales.team_id == team.id).first()
    return SalesMemoryOut(decisions=mem.decisions if mem else {})


@router.patch("", response_model=OkResponse)
def patch_decisions(
    body: SalesPatch,
    team: Team    = Depends(verify_team),
    db:   Session = Depends(get_db),
):
    _assert_phase(db, team, CyclePhase.SALES_OPEN)

    mem = db.query(MemorySales).filter(
        MemorySales.team_id == team.id
    ).first()
    if mem is None:
        raise HTTPException(500, "Sales memory not initialised.")

    current = dict(mem.decisions or {})

    # Save units_to_assemble at top level of decisions
    if body.units_to_assemble is not None:
        current["units_to_assemble"] = body.units_to_assemble

    for tier_val, dec in body.decisions.items():
        current[tier_val] = dec.dict()

    mem.decisions = current
    db.commit()

    return OkResponse(message="Sales decisions updated.")