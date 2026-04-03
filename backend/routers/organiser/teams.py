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