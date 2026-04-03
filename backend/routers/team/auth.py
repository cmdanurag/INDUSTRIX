"""
routers/team/auth.py
====================
POST /team/login   — verify PIN, return team_id and name
GET  /team/status  — return current game phase (polling endpoint, no auth)
GET  /team/me      — return team's own inventory snapshot
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.auth import verify_team
from core.database import get_db
from models.game import Cycle, CyclePhaseLog, Game, Team
from models.procurement import Inventory
from schemas.common import OkResponse, PhaseStatusResponse
from schemas.game import TeamLoginResponse
from schemas.sales import InventoryOut

router = APIRouter(prefix="/team", tags=["team"])


@router.post("/login", response_model=TeamLoginResponse)
def login(team: Team = Depends(verify_team)):
    """
    Verify team credentials. Returns team_id and name.
    The frontend stores team_id and raw PIN locally and sends them
    as headers on every subsequent request.
    """
    return TeamLoginResponse(team_id=team.id, team_name=team.name)


@router.get("/status", response_model=PhaseStatusResponse)
def game_status(db: Session = Depends(get_db)):
    """
    Public polling endpoint — no auth required.
    Frontend polls this every 5-10 seconds to detect phase changes.
    """
    game = db.query(Game).filter(Game.is_active == True).first()
    if not game:
        return PhaseStatusResponse(
            game_name="", cycle_number=0,
            phase="no_active_game", game_active=False,
        )
    cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    if not cycle:
        return PhaseStatusResponse(
            game_name=game.name, cycle_number=0,
            phase="waiting_for_first_cycle", game_active=True,
        )
    return PhaseStatusResponse(
        game_name    = game.name,
        cycle_number = cycle.cycle_number,
        phase        = cycle.phase_log.current_phase.value
                       if cycle.phase_log else "unknown",
        game_active  = game.is_active,
    )


@router.get("/me", response_model=InventoryOut)
def my_inventory(
    team: Team = Depends(verify_team),
    db:   Session = Depends(get_db),
):
    inv = db.query(Inventory).filter(Inventory.team_id == team.id).first()
    if inv is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Inventory not found.")
    return InventoryOut(
        funds             = inv.funds,
        brand_score       = inv.brand_score,
        brand_tier        = inv.brand_tier.value,
        drone_stock_total = sum(inv.drone_stock[1:]) if inv.drone_stock else 0,
        workforce_size    = inv.workforce_size,
        skill_level       = inv.skill_level,
        morale            = inv.morale,
        automation_level  = inv.automation_level.value
                            if hasattr(inv.automation_level, "value")
                            else str(inv.automation_level),
        has_gov_loan      = inv.has_gov_loan,
    )