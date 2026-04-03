"""
routers/organiser/cycle.py
==========================
POST /organiser/cycle/create   — create the first (or next) cycle manually
POST /organiser/cycle/advance  — advance to next phase + run resolution
POST /organiser/cycle/next     — from BACKROOM: roll discovery, start new cycle
POST /organiser/cycle/end-game — from BACKROOM: roll discovery, end game
GET  /organiser/cycle/status   — full phase status for organiser dashboard
PATCH /organiser/game/settings — update qr thresholds / demand multiplier
POST /organiser/cycle/force-phase — emergency: set phase manually
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import verify_organiser
from core.database import get_db
from core.enums import CyclePhase
from models.game import Cycle, Game
from schemas.common import OkResponse
from schemas.deals import AdvancePhaseOut, GameUpdateSettings
from services.cycle import advance_phase, create_cycle, end_game, start_next_cycle

router = APIRouter(prefix="/organiser/cycle", tags=["organiser"])


@router.post("/create", response_model=OkResponse)
def create_new_cycle(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """Create cycle 1 (or next cycle if called manually instead of /next)."""
    cycle = create_cycle(db, game)
    return OkResponse(message=f"Cycle {cycle.cycle_number} created.")


@router.post("/advance", response_model=AdvancePhaseOut)
def advance(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Advance from the current phase to the next.
    Runs resolution for the phase being closed.

    PROCUREMENT_OPEN → (procurement resolves) → PRODUCTION_OPEN
    PRODUCTION_OPEN  → (production resolves)  → SALES_OPEN
    SALES_OPEN       → (sales resolves)        → BACKROOM
    """
    try:
        phase_log = advance_phase(db, game)
    except ValueError as e:
        raise HTTPException(400, str(e))

    cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    return AdvancePhaseOut(
        previous_phase = "resolved",
        current_phase  = phase_log.current_phase.value,
        cycle_number   = cycle.cycle_number if cycle else 0,
    )


@router.post("/next", response_model=OkResponse)
def next_cycle(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """From BACKROOM: roll discovery on deals, start a new cycle."""
    try:
        cycle = start_next_cycle(db, game)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return OkResponse(message=f"Cycle {cycle.cycle_number} started.")


@router.post("/end-game", response_model=OkResponse)
def finish_game(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """From BACKROOM: end the game. Leaderboard becomes final."""
    try:
        end_game(db, game)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return OkResponse(message="Game ended. Final leaderboard is now live.")


@router.get("/status")
def cycle_status(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """Full cycle status for the organiser dashboard."""
    cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    if not cycle:
        return {"cycle": None, "phase": None}
    return {
        "cycle_number": cycle.cycle_number,
        "phase":        cycle.phase_log.current_phase.value
                        if cycle.phase_log else None,
        "qr_hard":      cycle.qr_hard,
        "qr_soft":      cycle.qr_soft,
        "qr_premium":   cycle.qr_premium,
        "demand_mult":  cycle.market_demand_multiplier,
    }


@router.patch("/force-phase", response_model=OkResponse)
def force_phase(
    phase_value: str,
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Emergency escape hatch — force the cycle into any phase.
    Use only when something has gone wrong mid-game.
    """
    try:
        target = CyclePhase(phase_value)
    except ValueError:
        raise HTTPException(400, f"Unknown phase: {phase_value}")

    cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    if not cycle or not cycle.phase_log:
        raise HTTPException(404, "No active cycle.")

    cycle.phase_log.current_phase = target
    db.commit()
    return OkResponse(message=f"Phase forced to '{target.value}'.")


@router.patch("/game/settings", response_model=OkResponse)  # override prefix
def update_settings(
    body: GameUpdateSettings,
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Update game-level parameters during BACKROOM.
    Takes effect in the next cycle (snapshotted at cycle creation).
    """
    if body.qr_hard    is not None: game.qr_hard    = body.qr_hard
    if body.qr_soft    is not None: game.qr_soft    = body.qr_soft
    if body.qr_premium is not None: game.qr_premium = body.qr_premium
    if body.market_demand_multiplier is not None:
        game.market_demand_multiplier = body.market_demand_multiplier
    db.commit()
    return OkResponse(message="Game settings updated.")