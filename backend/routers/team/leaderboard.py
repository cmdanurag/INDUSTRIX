"""
routers/team/leaderboard.py
===========================
GET /team/leaderboard — visible during BACKROOM phase and GAME_OVER.
                        No auth required — public board.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.enums import CyclePhase
from models.game import Cycle, Game
from schemas.sales import LeaderboardOut, LeaderboardRow
from services.leaderboard import compute_leaderboard

router = APIRouter(prefix="/team/leaderboard", tags=["team"])


@router.get("", response_model=LeaderboardOut)
def get_leaderboard(db: Session = Depends(get_db)):
    """
    Returns the leaderboard for the current cycle.
    Available during BACKROOM and GAME_OVER phases.
    Teams see all rivals — this is the big reveal moment.
    """
    game = db.query(Game).filter(Game.is_active == True).first()
    if not game:
        # Game over — find the last game
        game = (
            db.query(Game)
            .filter(Game.is_active == False)
            .order_by(Game.id.desc())
            .first()
        )
        if not game:
            raise HTTPException(404, "No game found.")

    cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    if not cycle:
        raise HTTPException(404, "No cycle found.")

    phase = cycle.phase_log.current_phase if cycle.phase_log else None
    if phase not in (CyclePhase.BACKROOM, CyclePhase.GAME_OVER):
        raise HTTPException(
            403,
            f"Leaderboard is only visible during BACKROOM or GAME_OVER. "
            f"Current phase: {phase.value if phase else 'unknown'}",
        )

    is_final = phase == CyclePhase.GAME_OVER
    rows     = compute_leaderboard(db, game, cycle, is_final)

    return LeaderboardOut(
        cycle_number = cycle.cycle_number,
        is_final     = is_final,
        rows         = [LeaderboardRow(**r) for r in rows],
    )