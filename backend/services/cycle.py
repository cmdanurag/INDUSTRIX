"""
services/cycle.py
=================
Cycle orchestrator. All phase transitions go through here.
No event logic lives here — events are resolved inside the service
that owns each phase.

Public API
----------
create_game(db, ...)          → Game
add_team(db, game, name, pin) → Team
create_cycle(db, game)        → Cycle
advance_phase(db, game, rng)  → CyclePhaseLog
start_next_cycle(db, game)    → Cycle
end_game(db, game)            → Game
"""
import hashlib
import secrets
from datetime import datetime
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from core.enums import CyclePhase
from models.game import Cycle, CyclePhaseLog, Game, Team
from models.procurement import ComponentSlot, Inventory, MemoryProcurement
from models.production import MemoryProduction
from models.sales import MemorySales
from services.procurement import (
    resolve_procurement, seed_component_slots, seed_procurement_memory,
)
from services.production import resolve_production, seed_production_memory
from services.sales import (
    resolve_global_financial_events, resolve_sales, seed_sales_memory,
)
from services.deals import (
    create_events_for_pending_deals, roll_discovery,
)
from services.production import seed_machine
from routers.organiser.market import seed_market_factions


# ── Game setup ────────────────────────────────────────────────────────────────

def create_game(
    db:                       Session,
    name:                     str,
    qr_hard:                  float = 30.0,
    qr_soft:                  float = 50.0,
    qr_premium:               float = 75.0,
    market_demand_multiplier: float = 1.0,
    starting_funds:           float = 100_000.0,
) -> Game:
    game = Game(
        name                     = name,
        qr_hard                  = qr_hard,
        qr_soft                  = qr_soft,
        qr_premium               = qr_premium,
        market_demand_multiplier = market_demand_multiplier,
        starting_funds           = starting_funds,
        is_active                = True,
    )
    db.add(game)
    db.flush()

    # Seed default market factions for this game.
    seed_market_factions(db, game)

    db.commit()
    db.refresh(game)
    return game


def add_team(db: Session, game: Game, name: str, pin: str) -> Team:
    """
    Create a team and seed all persistent state rows.
    """
    pin_hash = hashlib.sha256(pin.encode()).hexdigest()
    team = Team(
        game_id   = game.id,
        name      = name,
        pin_hash  = pin_hash,
        is_active = True,
    )
    db.add(team)
    db.flush()

    inv = Inventory(
        team_id           = team.id,
        funds             = game.starting_funds,
        drone_stock       = [0] * 101,
        brand_score       = 50.0,
        workforce_size    = 50,
        skill_level       = 40.0,
        morale            = 60.0,
        has_gov_loan      = False,
        cumulative_profit = 0.0,
    )
    db.add(inv)

    seed_component_slots(db, team)
    seed_procurement_memory(db, team)
    seed_production_memory(db, team)
    seed_sales_memory(db, team)

    # Seed one Standard machine per component slot.
    from models.procurement import ComponentSlot
    for slot in db.query(ComponentSlot).filter(ComponentSlot.team_id == team.id).all():
        seed_machine(db, team, slot, tier="standard",
                     cycle_number=0, source="seed")

    db.commit()
    db.refresh(team)
    return team


# ── Cycle creation ────────────────────────────────────────────────────────────

def create_cycle(db: Session, game: Game) -> Cycle:
    """
    Create the next cycle, snapshotting current game parameters.
    Also generates Event rows for any pending GovDeals that didn't
    have a target cycle when they were recorded.
    """
    last = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    next_number = (last.cycle_number + 1) if last else 1

    cycle = Cycle(
        game_id                  = game.id,
        cycle_number             = next_number,
        qr_hard                  = game.qr_hard,
        qr_soft                  = game.qr_soft,
        qr_premium               = game.qr_premium,
        market_demand_multiplier = game.market_demand_multiplier,
    )
    db.add(cycle)
    db.flush()

    phase_log = CyclePhaseLog(
        cycle_id              = cycle.id,
        current_phase         = CyclePhase.PROCUREMENT_OPEN,
        procurement_opened_at = datetime.utcnow(),
    )
    db.add(phase_log)
    db.commit()
    db.refresh(cycle)

    # Generate Event rows for any GovDeals that are still PENDING and
    # have no events yet (because this cycle didn't exist at deal time).
    n = create_events_for_pending_deals(db, game, cycle)
    if n:
        db.commit()

    return cycle


# ── Phase advancement ─────────────────────────────────────────────────────────

_PHASE_ORDER = [
    CyclePhase.PROCUREMENT_OPEN,
    CyclePhase.PRODUCTION_OPEN,
    CyclePhase.SALES_OPEN,
    CyclePhase.BACKROOM,
]

_PHASE_TIMESTAMPS = {
    CyclePhase.PRODUCTION_OPEN: "production_opened_at",
    CyclePhase.SALES_OPEN:      "sales_opened_at",
    CyclePhase.BACKROOM:        "backroom_opened_at",
}


def advance_phase(
    db:    Session,
    game:  Game,
    rng:   Optional[np.random.Generator] = None,
) -> CyclePhaseLog:
    """
    Advance to the next phase in the current cycle.
    Runs the resolution for the phase being closed.

    PROCUREMENT_OPEN → procurement resolves → PRODUCTION_OPEN
    PRODUCTION_OPEN  → production resolves  → SALES_OPEN
    SALES_OPEN       → sales + financial resolves → BACKROOM
    """
    if rng is None:
        rng = np.random.default_rng()

    cycle = _current_cycle(db, game)
    if cycle is None:
        raise ValueError("No active cycle. Create a cycle first.")

    phase_log: CyclePhaseLog = cycle.phase_log
    current   = phase_log.current_phase

    if current not in _PHASE_ORDER:
        raise ValueError(f"Cannot advance from phase '{current}'.")

    idx = _PHASE_ORDER.index(current)
    if idx + 1 >= len(_PHASE_ORDER):
        raise ValueError(
            "Already at BACKROOM. Use /next or /end-game."
        )

    teams = (
        db.query(Team)
        .filter(Team.game_id == game.id, Team.is_active == True)
        .all()
    )

    # ── Run resolution for the phase being closed ────────────────────────────
    if current == CyclePhase.PROCUREMENT_OPEN:
        proc_summaries = {}
        for team in teams:
            result = resolve_procurement(db, team, cycle, rng)
            proc_summaries[str(team.id)] = result
        phase_log.procurement_summary = proc_summaries

    elif current == CyclePhase.PRODUCTION_OPEN:
        prod_summaries = {}
        for team in teams:
            result = resolve_production(db, team, cycle, rng)
            prod_summaries[str(team.id)] = result
        phase_log.production_summary = prod_summaries

    elif current == CyclePhase.SALES_OPEN:
        sales_summaries = {}
        for team in teams:
            result = resolve_sales(db, team, cycle, teams, rng)
            sales_summaries[str(team.id)] = result
        phase_log.sales_summary = sales_summaries
        # Global financial events (market shifts) — applied once, not per team
        resolve_global_financial_events(db, game, cycle)

    # ── Advance phase ─────────────────────────────────────────────────────────
    next_phase = _PHASE_ORDER[idx + 1]
    phase_log.current_phase = next_phase

    ts_field = _PHASE_TIMESTAMPS.get(next_phase)
    if ts_field:
        setattr(phase_log, ts_field, datetime.utcnow())

    db.commit()
    db.refresh(phase_log)
    return phase_log


# ── Next cycle / end game ─────────────────────────────────────────────────────

def start_next_cycle(db: Session, game: Game) -> Cycle:
    """
    From BACKROOM: roll discovery on deals, close current cycle,
    create the next cycle.
    """
    cycle     = _current_cycle(db, game)
    phase_log = cycle.phase_log

    if phase_log.current_phase != CyclePhase.BACKROOM:
        raise ValueError("Not in BACKROOM phase.")

    roll_discovery(db, cycle)

    phase_log.completed_at = datetime.utcnow()
    db.commit()

    return create_cycle(db, game)


def end_game(db: Session, game: Game) -> Game:
    """
    From BACKROOM: roll discovery, end the game.
    """
    cycle     = _current_cycle(db, game)
    phase_log = cycle.phase_log

    if phase_log.current_phase != CyclePhase.BACKROOM:
        raise ValueError("Not in BACKROOM phase.")

    roll_discovery(db, cycle)

    phase_log.current_phase = CyclePhase.GAME_OVER
    phase_log.completed_at  = datetime.utcnow()
    game.is_active          = False
    db.commit()
    db.refresh(game)
    return game


# ── Helper ────────────────────────────────────────────────────────────────────

def _current_cycle(db: Session, game: Game) -> Optional[Cycle]:
    return (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )