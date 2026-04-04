"""
routers/organiser/teams.py
==========================
GET  /organiser/teams                    List all teams with summary stats
GET  /organiser/teams/{id}/inventory     Full inventory for one team
POST /organiser/teams/{id}/reset-pin     Reset a team's PIN
POST /organiser/game/create              Bootstrap: create the game
POST /organiser/teams/add                Add a team to the active game
"""
import hashlib
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from core.auth import verify_organiser
from core.config import MACHINE_TIERS
from core.database import get_db
from models.game import Game, Team
from models.procurement import ComponentSlot, Inventory, Machine
from schemas.common import OkResponse
from schemas.game import GameCreate, GameOut, TeamCreate, TeamOut
from schemas.production import ComponentSlotOut, MachineOut
from services.cycle import add_team, create_game
from services.production import get_active_machines

from core.config import ADMIN_CODE

router = APIRouter(prefix="/organiser", tags=["organiser"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_machine_out(m: Machine) -> MachineOut:
    cfg = MACHINE_TIERS.get(m.tier, MACHINE_TIERS["standard"])
    return MachineOut(
        id              = m.id,
        tier            = m.tier,
        condition       = round(m.condition, 1),
        is_active       = m.is_active,
        purchased_cycle = m.purchased_cycle,
        source          = m.source,
        throughput      = cfg["throughput"],
        base_grade      = cfg["grade"],
    )


def _build_slot_out(
    db: Session, slot: ComponentSlot
) -> ComponentSlotOut:
    machines = (
        db.query(Machine)
        .filter(Machine.slot_id == slot.id)
        .order_by(Machine.id)
        .all()
    )
    active_machines = [m for m in machines if m.is_active]
    tp = sum(
        MACHINE_TIERS.get(m.tier, MACHINE_TIERS["standard"])["throughput"]
        for m in active_machines
    )
    return ComponentSlotOut(
        component        = slot.component.value,
        raw_stock_total  = sum(slot.raw_stock[1:])  if slot.raw_stock  else 0,
        fin_stock_total  = sum(slot.finished_stock[1:]) if slot.finished_stock else 0,
        rnd_quality      = slot.rnd_quality,
        rnd_consistency  = slot.rnd_consistency,
        rnd_yield        = slot.rnd_yield,
        machines         = [_build_machine_out(m) for m in machines],
        total_throughput = tp,
    )


# ── Game creation (bootstrap) ─────────────────────────────────────────────────

@router.post("/game/create", response_model=GameOut, status_code=201,
             summary="Create the game. One-time bootstrap call.")
def bootstrap_game(
    body:               GameCreate,
    x_bootstrap_secret: str = Header(...,
        description="One-time secret from .env — used only for this call."),
    db: Session = Depends(get_db),
):
    """
    Create the game. Called once before the event.
    Returns the organiser_secret — store it, it is needed for all admin endpoints.
    After this call, authenticate via x-organiser-secret header.
    """
    expected = ADMIN_CODE
    if not expected or x_bootstrap_secret != expected:
        raise HTTPException(403, "Invalid bootstrap secret.")

    game = create_game(
        db                       = db,
        name                     = body.name,
        qr_hard                  = body.qr_hard,
        qr_soft                  = body.qr_soft,
        qr_premium               = body.qr_premium,
        market_demand_multiplier = body.market_demand_multiplier,
        starting_funds           = body.starting_funds,
    )
    return game


# ── Team management ───────────────────────────────────────────────────────────

@router.post("/teams/add", response_model=TeamOut, status_code=201,
             summary="Add a team to the active game.")
def create_team(
    body: TeamCreate,
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Creates a team and seeds all persistent rows:
    Inventory, ComponentSlot × 6, Machine × 6 (one Standard per component),
    MemoryProcurement, MemoryProduction, MemorySales.
    """
    try:
        team = add_team(db, game, body.name, body.pin)
    except Exception as e:
        raise HTTPException(400, str(e))
    return team


@router.get("/teams", response_model=List[dict],
            summary="List all teams with summary financials.")
def list_teams(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    teams = db.query(Team).filter(Team.game_id == game.id).all()
    result = []
    for team in teams:
        inv = db.query(Inventory).filter(Inventory.team_id == team.id).first()

        # Count total active machines across all components
        machine_count = (
            db.query(Machine)
            .filter(Machine.team_id == team.id, Machine.is_active == True)
            .count()
        )

        # Finished component stock totals per component
        slots = db.query(ComponentSlot).filter(
            ComponentSlot.team_id == team.id
        ).all()
        fin_stock_total = sum(
            sum(s.finished_stock[1:]) if s.finished_stock else 0
            for s in slots
        )

        result.append({
            "id":               team.id,
            "name":             team.name,
            "is_active":        team.is_active,
            "funds":            round(inv.funds, 2) if inv else 0.0,
            "brand_score":      round(inv.brand_score, 2) if inv else 0.0,
            "brand_tier":       inv.brand_tier.value if inv else "fair",
            "has_gov_loan":     inv.has_gov_loan if inv else False,
            "drone_stock":      sum(inv.drone_stock[1:]) if inv and inv.drone_stock else 0,
            "fin_stock_total":  fin_stock_total,
            "active_machines":  machine_count,
            "cumul_profit":     round(inv.cumulative_profit, 2) if inv else 0.0,
        })
    return result


@router.get("/teams/{team_id}/inventory",
            summary="Full inventory for one team including all machines.")
def team_inventory(
    team_id: int,
    game:    Game    = Depends(verify_organiser),
    db:      Session = Depends(get_db),
):
    """
    Returns the complete state of one team:
    - Inventory (funds, brand, labour)
    - Per-component: raw_stock, finished_stock, R&D levels, all machines
      (including inactive ones for audit purposes)
    """
    team = db.query(Team).filter(
        Team.id == team_id, Team.game_id == game.id
    ).first()
    if not team:
        raise HTTPException(404, "Team not found.")

    inv   = db.query(Inventory).filter(Inventory.team_id == team.id).first()
    slots = db.query(ComponentSlot).filter(
        ComponentSlot.team_id == team.id
    ).order_by(ComponentSlot.component).all()

    return {
        "team": {
            "id":        team.id,
            "name":      team.name,
            "is_active": team.is_active,
        },
        "inventory": {
            "funds":              round(inv.funds, 2) if inv else 0.0,
            "brand_score":        round(inv.brand_score, 2) if inv else 0.0,
            "brand_tier":         inv.brand_tier.value if inv else "fair",
            "drone_stock_total":  sum(inv.drone_stock[1:]) if inv and inv.drone_stock else 0,
            "workforce_size":     inv.workforce_size if inv else 0,
            "skill_level":        round(inv.skill_level, 1) if inv else 0.0,
            "morale":             round(inv.morale, 1) if inv else 0.0,
            "automation_level":   inv.automation_level.value
                                  if inv and hasattr(inv.automation_level, "value")
                                  else "manual",
            "has_gov_loan":       inv.has_gov_loan if inv else False,
            "cumulative_profit":  round(inv.cumulative_profit, 2) if inv else 0.0,
        },
        "components": [_build_slot_out(db, slot).dict() for slot in slots],
    }


@router.post("/teams/{team_id}/reset-pin", response_model=OkResponse,
             summary="Reset a team's PIN (useful if forgotten during the event).")
def reset_pin(
    team_id: int,
    new_pin: str,
    game:    Game    = Depends(verify_organiser),
    db:      Session = Depends(get_db),
):
    team = db.query(Team).filter(
        Team.id == team_id, Team.game_id == game.id
    ).first()
    if not team:
        raise HTTPException(404, "Team not found.")
    team.pin_hash = hashlib.sha256(new_pin.encode()).hexdigest()
    db.commit()
    return OkResponse(message=f"PIN reset for team '{team.name}'.")

# ── Sources management ────────────────────────────────────────────────────────

from models.game import RawMaterialSource
from schemas.procurement import RawMaterialSourceOut
from pydantic import BaseModel as _BM
from typing import Optional as _Opt


class SourceCreate(_BM):
    component:          str
    name:               str
    distance:           int   = 500
    quality_mean:       float
    quality_sigma:      float
    base_cost_per_unit: float
    note:               _Opt[str] = None


class SourcePatch(_BM):
    quality_mean:       _Opt[float] = None
    quality_sigma:      _Opt[float] = None
    base_cost_per_unit: _Opt[float] = None
    is_active:          _Opt[bool]  = None
    note:               _Opt[str]   = None


@router.get("/sources", summary="List all raw material sources for this game.")
def list_sources(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Returns all sources (active and inactive) so the organiser can see
    the full supplier landscape. Teams only see active sources via
    GET /team/procurement/sources.
    """
    sources = (
        db.query(RawMaterialSource)
        .filter(RawMaterialSource.game_id == game.id)
        .order_by(RawMaterialSource.component, RawMaterialSource.name)
        .all()
    )
    return [
        {
            "id":                 s.id,
            "component":          s.component.value,
            "name":               s.name,
            "quality_mean":       s.quality_mean,
            "quality_sigma":      s.quality_sigma,
            "base_cost_per_unit": s.base_cost_per_unit,
            "distance":           s.distance,
            "is_active":          s.is_active,
            "note":               s.note,
        }
        for s in sources
    ]


@router.post("/sources", status_code=201,
             summary="Add a new raw material source mid-game.")
def create_source(
    body: SourceCreate,
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Add a new supplier. Takes effect immediately — teams will see it
    the next time they call GET /team/procurement/sources.

    Useful for: introducing a new supplier as a global event reward,
    or replacing a disabled source mid-game.
    """
    from core.enums import ComponentType
    try:
        comp = ComponentType(body.component)
    except ValueError:
        raise HTTPException(400, f"Unknown component '{body.component}'.")

    source = RawMaterialSource(
        game_id            = game.id,
        component          = comp,
        name               = body.name,
        distance           = body.distance,
        quality_mean       = body.quality_mean,
        quality_sigma      = body.quality_sigma,
        base_cost_per_unit = body.base_cost_per_unit,
        note               = body.note,
        is_active          = True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return {"id": source.id, "name": source.name, "component": source.component.value}


@router.patch("/sources/{source_id}",
              summary="Modify a source's parameters (price, quality, active status).")
def update_source(
    source_id: int,
    body:      SourcePatch,
    game:      Game    = Depends(verify_organiser),
    db:        Session = Depends(get_db),
):
    """
    Modify a supplier between cycles. Use for:
    - Over-extraction events (lower quality_mean, raise cost)
    - Supply disruption (set is_active=false)
    - Infrastructure investment (raise quality_mean, lower cost)
    - New transport route (lower distance/cost)

    Changes take effect at the next procurement resolution.
    """
    source = db.query(RawMaterialSource).filter(
        RawMaterialSource.id      == source_id,
        RawMaterialSource.game_id == game.id,
    ).first()
    if not source:
        raise HTTPException(404, f"Source {source_id} not found.")

    if body.quality_mean       is not None: source.quality_mean       = body.quality_mean
    if body.quality_sigma      is not None: source.quality_sigma      = body.quality_sigma
    if body.base_cost_per_unit is not None: source.base_cost_per_unit = body.base_cost_per_unit
    if body.is_active          is not None: source.is_active          = body.is_active
    if body.note               is not None: source.note               = body.note

    db.commit()
    return OkResponse(message=f"Source '{source.name}' updated.")


# ── Direct fund adjustment ────────────────────────────────────────────────────

@router.post("/teams/{team_id}/adjust-funds",
             summary="Directly adjust a team's funds (manual correction).")
def adjust_funds(
    team_id: int,
    amount:  float,
    reason:  str = "Manual organiser adjustment",
    game:    Game    = Depends(verify_organiser),
    db:      Session = Depends(get_db),
):
    """
    Add or subtract funds from a team directly. Use for:
    - Correcting a calculation error
    - Applying a penalty outside the deals system
    - Emergency bailout not recorded as a loan
    - Applying a prize

    `amount` can be positive (add funds) or negative (deduct funds).
    Funds can go below zero — there is no floor.
    """
    team = db.query(Team).filter(
        Team.id == team_id, Team.game_id == game.id
    ).first()
    if not team:
        raise HTTPException(404, "Team not found.")

    inv = db.query(Inventory).filter(Inventory.team_id == team.id).first()
    if not inv:
        raise HTTPException(500, "Inventory not found.")

    inv.funds = round(inv.funds + amount, 2)
    db.commit()

    return {
        "team":          team.name,
        "adjustment":    round(amount, 2),
        "funds_after":   round(inv.funds, 2),
        "reason":        reason,
    }


# ── Deactivate a team (bankruptcy / forfeit) ──────────────────────────────────

@router.post("/teams/{team_id}/deactivate",
             summary="Eliminate a team (bankruptcy or voluntary forfeit).")
def deactivate_team(
    team_id: int,
    reason:  str = "Eliminated",
    game:    Game    = Depends(verify_organiser),
    db:      Session = Depends(get_db),
):
    """
    Mark a team as inactive. They will be excluded from all future resolution
    passes. Their data is preserved for audit and debrief.

    Use when:
    - A team's funds are so negative they cannot recover
    - A team chooses to forfeit during the backroom phase
    - A team violates a rule that warrants elimination
    """
    team = db.query(Team).filter(
        Team.id == team_id, Team.game_id == game.id
    ).first()
    if not team:
        raise HTTPException(404, "Team not found.")
    if not team.is_active:
        raise HTTPException(400, f"Team '{team.name}' is already inactive.")

    team.is_active = False
    db.commit()
    return OkResponse(message=f"Team '{team.name}' deactivated. Reason: {reason}")


# ── Loan repayment ────────────────────────────────────────────────────────────

from models.deals import Event, EventStatus, EventType


@router.post("/deals/repay-loan",
             summary="Mark a loan repaid, clear gov-loan flag, optionally transfer funds.")
def repay_loan(
    borrower_team_id: int,
    amount:           float,
    clear_gov_flag:   bool = True,
    game:             Game    = Depends(verify_organiser),
    db:               Session = Depends(get_db),
):
    """
    Record a loan repayment. Steps:
    1. Deduct `amount` from borrower's funds.
    2. If clear_gov_flag=True and borrower has no remaining gov-loan
       interest events, set has_gov_loan=False (unblocking backroom deals).
    3. Cancel all remaining PENDING LOAN_INTEREST events for this borrower
       (assumes full repayment; partial repayments should use adjust-funds).

    For inter-team loans: manually transfer funds to the lender separately
    using /teams/{id}/adjust-funds if needed.
    """
    team = db.query(Team).filter(
        Team.id == borrower_team_id, Team.game_id == game.id
    ).first()
    if not team:
        raise HTTPException(404, "Team not found.")

    inv = db.query(Inventory).filter(Inventory.team_id == team.id).first()
    if not inv:
        raise HTTPException(500, "Inventory not found.")

    inv.funds = round(inv.funds - amount, 2)

    # Cancel remaining PENDING loan interest events for this borrower
    pending_loans = (
        db.query(Event)
        .filter(
            Event.target_team_id == team.id,
            Event.event_type     == EventType.LOAN_INTEREST,
            Event.status         == EventStatus.PENDING,
        )
        .all()
    )
    from datetime import datetime
    for ev in pending_loans:
        ev.status     = EventStatus.APPLIED
        ev.applied_at = datetime.utcnow()

    if clear_gov_flag:
        inv.has_gov_loan = False

    db.commit()
    return {
        "team":          team.name,
        "amount_repaid": round(amount, 2),
        "funds_after":   round(inv.funds, 2),
        "loans_cancelled": len(pending_loans),
        "gov_flag_cleared": clear_gov_flag,
    }


# ── Leaderboard history ───────────────────────────────────────────────────────

from models.game import Cycle
from services.leaderboard import compute_leaderboard


@router.get("/leaderboard/history",
            summary="Leaderboard snapshots across all completed cycles.")
def leaderboard_history(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Returns the leaderboard state at the end of every completed cycle.
    Useful for the post-game debrief screen showing how rankings evolved.

    Completed cycles = those whose phase_log.completed_at is not null.
    The current (in-progress) cycle is included as the final entry using
    current inventory state.
    """
    cycles = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number)
        .all()
    )

    history = []
    for cycle in cycles:
        is_final   = (
            cycle.phase_log and cycle.phase_log.completed_at is not None
        )
        rows = compute_leaderboard(db, game, cycle, is_final=is_final)
        history.append({
            "cycle_number": cycle.cycle_number,
            "is_complete":  is_final,
            "standings":    rows,
        })

    return {"game_id": game.id, "history": history}


# ── Game summary ──────────────────────────────────────────────────────────────

@router.get("/game/summary",
            summary="Full game state in one call for the organiser dashboard.")
def game_summary(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Returns a complete snapshot of the current game state:
    - Current cycle number and phase
    - All teams with funds, brand, drone stock, gov-loan status
    - Market factions (volume + price ceiling)
    - Current game-level QR thresholds and demand multiplier
    - Active event count per phase

    Use this as the primary data source for the organiser dashboard
    to avoid making 10 separate API calls.
    """
    from models.market import MarketFaction
    from models.deals import EventPhase

    cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )

    # Teams summary
    teams = db.query(Team).filter(Team.game_id == game.id).all()
    team_rows = []
    for t in teams:
        inv = db.query(Inventory).filter(Inventory.team_id == t.id).first()
        slots = db.query(ComponentSlot).filter(
            ComponentSlot.team_id == t.id
        ).all()
        fin_total = sum(
            sum(s.finished_stock[1:]) if s.finished_stock else 0
            for s in slots
        )
        team_rows.append({
            "id":              t.id,
            "name":            t.name,
            "is_active":       t.is_active,
            "funds":           round(inv.funds, 2) if inv else 0.0,
            "brand_score":     round(inv.brand_score, 2) if inv else 0.0,
            "brand_tier":      inv.brand_tier.value if inv else "fair",
            "drone_stock":     sum(inv.drone_stock[1:]) if inv and inv.drone_stock else 0,
            "fin_stock_total": fin_total,
            "has_gov_loan":    inv.has_gov_loan if inv else False,
        })

    # Active events breakdown
    event_counts = {}
    if cycle:
        for phase in EventPhase:
            count = (
                db.query(Event)
                .filter(
                    Event.cycle_id == cycle.id,
                    Event.phase    == phase,
                    Event.status   == EventStatus.PENDING,
                )
                .count()
            )
            event_counts[phase.value] = count

    # Market factions
    factions = (
        db.query(MarketFaction)
        .filter(
            MarketFaction.game_id  == game.id,
            MarketFaction.is_active == True,
        )
        .all()
    )

    return {
        "game": {
            "id":        game.id,
            "name":      game.name,
            "is_active": game.is_active,
            "qr_hard":   game.qr_hard,
            "qr_soft":   game.qr_soft,
            "qr_premium": game.qr_premium,
            "demand_multiplier": game.market_demand_multiplier,
        },
        "cycle": {
            "number": cycle.cycle_number if cycle else None,
            "phase":  cycle.phase_log.current_phase.value
                      if cycle and cycle.phase_log else None,
        } if cycle else None,
        "teams": team_rows,
        "market_factions": [
            {
                "name":           f.name,
                "tier_preference": f.tier_preference,
                "price_ceiling":  f.price_ceiling,
                "volume":         f.volume,
            }
            for f in factions
        ],
        "pending_events_by_phase": event_counts,
    }