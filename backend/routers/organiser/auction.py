"""
routers/organiser/auction.py
=============================
Auction result endpoints — called by the organiser after an open ascending
auction has concluded verbally during the backroom phase.

The auction itself runs offline (organiser announces a lot, teams bid verbally
in rounds, organiser keeps bidding open until no higher bid). Once a winner
is determined, the organiser calls one of these endpoints to:
  a) deduct the winning bid from the winner's funds, and
  b) inject the won asset directly into the winner's inventory.

Three asset types can be auctioned:

POST /organiser/auction/raw-material
    Winner receives a batch of raw material (a 101-int quality array)
    injected into their ComponentSlot.raw_stock for one component.

POST /organiser/auction/component
    Winner receives a batch of finished components (a 101-int quality array)
    injected into their ComponentSlot.finished_stock for one component.
    These are ready to be assembled into drones in the next sales phase.

POST /organiser/auction/machine
    Winner receives a new machine of a specified tier and starting condition
    added to their Machine table for one component.

All endpoints are only callable during BACKROOM phase.
All endpoints deduct funds immediately (can go negative — handled in backroom).

GET /organiser/auction/preview/{team_id}
    Show what the team currently has in each component so the organiser
    can make sensible auction decisions (e.g. check if a team can even
    use more machines of a given component).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from core.auth import verify_organiser
from core.config import MACHINE_MAX_CONDITION, MACHINE_TIERS
from core.database import get_db
from core.enums import ComponentType, CyclePhase
from models.game import Cycle, Game, Team
from models.procurement import ComponentSlot, Inventory, Machine
from schemas.common import OkResponse
from services.production import seed_machine

router = APIRouter(prefix="/organiser/auction", tags=["organiser"])


# ── Guards ────────────────────────────────────────────────────────────────────

def _assert_backroom(game: Game, db: Session) -> Cycle:
    cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    if not cycle or cycle.phase_log.current_phase != CyclePhase.BACKROOM:
        raise HTTPException(
            400,
            "Auction endpoints are only accessible during the BACKROOM phase.",
        )
    return cycle


def _get_team(team_id: int, game_id: int, db: Session) -> Team:
    team = db.query(Team).filter(
        Team.id == team_id, Team.game_id == game_id
    ).first()
    if not team:
        raise HTTPException(404, f"Team {team_id} not found.")
    return team


def _get_slot(team_id: int, component: str, db: Session) -> ComponentSlot:
    slot = db.query(ComponentSlot).filter(
        ComponentSlot.team_id   == team_id,
        ComponentSlot.component == component,
    ).first()
    if not slot:
        raise HTTPException(404, f"Component slot '{component}' not found for team.")
    return slot


def _valid_component(component: str) -> str:
    valid = {c.value for c in ComponentType}
    if component not in valid:
        raise HTTPException(
            400,
            f"Invalid component '{component}'. "
            f"Valid values: {sorted(valid)}",
        )
    return component


def _valid_quality_array(arr: List[int]) -> List[int]:
    if len(arr) != 101:
        raise HTTPException(
            400,
            f"quality_array must have exactly 101 elements (got {len(arr)}). "
            "Index 0 = scrap bucket, indices 1-100 = grade counts.",
        )
    if any(v < 0 for v in arr):
        raise HTTPException(400, "quality_array values must be non-negative.")
    return arr


# ── Request bodies ────────────────────────────────────────────────────────────

class RawMaterialTransfer(BaseModel):
    winner_team_id: int         = Field(..., gt=0)
    component:      str         = Field(...,
        description="Component type value e.g. 'airframe'.")
    quality_array:  List[int]   = Field(...,
        description="101-int array. Index 0 = scrap, 1-100 = grade counts. "
                    "Represents the batch of raw material being transferred.")
    deduct_funds:   float       = Field(0.0, ge=0,
        description="Amount to deduct from winner's funds (the winning bid). "
                    "Set to 0 if the organiser is doing a non-auction transfer.")
    notes:          Optional[str] = None

    @validator("quality_array")
    def check_array(cls, v):
        if len(v) != 101:
            raise ValueError(f"quality_array must have 101 elements, got {len(v)}.")
        if any(x < 0 for x in v):
            raise ValueError("quality_array values must be non-negative.")
        return v


class ComponentTransfer(BaseModel):
    winner_team_id: int         = Field(..., gt=0)
    component:      str         = Field(...,
        description="Component type value e.g. 'avionics'.")
    quality_array:  List[int]   = Field(...,
        description="101-int array representing the finished components being "
                    "transferred. These go directly into finished_stock, ready "
                    "for assembly into drones in the next sales phase.")
    deduct_funds:   float       = Field(0.0, ge=0)
    notes:          Optional[str] = None

    @validator("quality_array")
    def check_array(cls, v):
        if len(v) != 101:
            raise ValueError(f"quality_array must have 101 elements, got {len(v)}.")
        if any(x < 0 for x in v):
            raise ValueError("quality_array values must be non-negative.")
        return v


class MachineTransfer(BaseModel):
    winner_team_id:    int   = Field(..., gt=0)
    component:         str   = Field(...,
        description="Which component this machine will process.")
    tier:              str   = Field(...,
        description="Machine tier: basic, standard, industrial, precision.")
    starting_condition: float = Field(100.0, ge=1.0, le=100.0,
        description="Starting condition of the machine. "
                    "100 = brand new. Can be set lower for used/reconditioned machines.")
    deduct_funds:      float = Field(0.0, ge=0,
        description="Winning bid amount to deduct from winner's funds.")
    notes:             Optional[str] = None

    @validator("tier")
    def valid_tier(cls, v):
        if v not in MACHINE_TIERS:
            raise ValueError(
                f"Invalid tier '{v}'. Valid: {list(MACHINE_TIERS.keys())}."
            )
        return v


# ── Response bodies ───────────────────────────────────────────────────────────

class TransferResult(BaseModel):
    ok:              bool  = True
    team_name:       str
    component:       str
    units_received:  Optional[int] = None   # for raw material and component transfers
    machine_id:      Optional[int] = None   # for machine transfers
    funds_deducted:  float
    funds_remaining: float
    notes:           Optional[str]


# ── Raw material transfer ─────────────────────────────────────────────────────

@router.post("/raw-material", response_model=TransferResult, status_code=201,
             summary="Transfer a raw material batch to the auction winner.")
def transfer_raw_material(
    body: RawMaterialTransfer,
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Inject a batch of raw material into the winner's ComponentSlot.raw_stock.
    Deduct the winning bid from their funds.

    The quality_array represents the distribution of grade quality in the batch.
    For a premium auction lot, the organiser would set high-grade indices:
    e.g. [0, 0, ..., 0, 50, 100, 150, 0, 0, 0] with the mass at grades 90-95.
    """
    cycle  = _assert_backroom(game, db)
    team   = _get_team(body.winner_team_id, game.id, db)
    comp   = _valid_component(body.component)
    slot   = _get_slot(team.id, comp, db)
    inv    = db.query(Inventory).filter(Inventory.team_id == team.id).first()

    if not inv:
        raise HTTPException(500, "Team inventory not found.")

    # Merge quality array into raw_stock
    existing       = slot.raw_stock or [0] * 101
    slot.raw_stock = [existing[i] + body.quality_array[i] for i in range(101)]

    # Deduct winning bid (allowed to go negative)
    inv.funds -= body.deduct_funds

    units_received = sum(body.quality_array[1:])
    db.commit()

    return TransferResult(
        team_name      = team.name,
        component      = comp,
        units_received = units_received,
        funds_deducted = body.deduct_funds,
        funds_remaining = round(inv.funds, 2),
        notes          = body.notes,
    )


# ── Finished component transfer ───────────────────────────────────────────────

@router.post("/component", response_model=TransferResult, status_code=201,
             summary="Transfer finished components to the auction winner.")
def transfer_component(
    body: ComponentTransfer,
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Inject finished components directly into the winner's finished_stock.
    These bypass the raw material → production step entirely.

    Use this for:
    - Auctioning pre-manufactured premium components
    - Emergency organiser intervention (e.g. compensating a team for a bug)
    - Granting components as a global event prize
    """
    cycle  = _assert_backroom(game, db)
    team   = _get_team(body.winner_team_id, game.id, db)
    comp   = _valid_component(body.component)
    slot   = _get_slot(team.id, comp, db)
    inv    = db.query(Inventory).filter(Inventory.team_id == team.id).first()

    if not inv:
        raise HTTPException(500, "Team inventory not found.")

    existing            = slot.finished_stock or [0] * 101
    slot.finished_stock = [existing[i] + body.quality_array[i] for i in range(101)]

    inv.funds -= body.deduct_funds

    units_received = sum(body.quality_array[1:])
    db.commit()

    return TransferResult(
        team_name      = team.name,
        component      = comp,
        units_received = units_received,
        funds_deducted = body.deduct_funds,
        funds_remaining = round(inv.funds, 2),
        notes          = body.notes,
    )


# ── Machine transfer ──────────────────────────────────────────────────────────

@router.post("/machine", response_model=TransferResult, status_code=201,
             summary="Transfer a machine to the auction winner.")
def transfer_machine(
    body: MachineTransfer,
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Add a new Machine row directly to the winner's component slot.
    Deduct the winning bid from their funds.

    Use for:
    - Auctioning premium/rare machines (e.g. a Precision machine not available
      in the normal buy flow, or a machine at 90 condition instead of 100)
    - Direct organiser transfers (grant, compensation)

    The machine is immediately active and counts toward throughput from the
    very next production phase.
    """
    cycle  = _assert_backroom(game, db)
    team   = _get_team(body.winner_team_id, game.id, db)
    comp   = _valid_component(body.component)
    slot   = _get_slot(team.id, comp, db)
    inv    = db.query(Inventory).filter(Inventory.team_id == team.id).first()

    if not inv:
        raise HTTPException(500, "Team inventory not found.")

    # Create the machine directly (bypass normal buy flow — no cost deduction
    # from tier config, the deduct_funds parameter handles the price)
    machine = Machine(
        team_id         = team.id,
        slot_id         = slot.id,
        component       = comp,
        tier            = body.tier,
        condition       = body.starting_condition,
        is_active       = True,
        purchased_cycle = cycle.cycle_number,
        source          = "auction",
    )
    db.add(machine)
    db.flush()

    inv.funds -= body.deduct_funds
    db.commit()

    cfg = MACHINE_TIERS.get(body.tier, MACHINE_TIERS["standard"])

    return TransferResult(
        team_name       = team.name,
        component       = comp,
        machine_id      = machine.id,
        funds_deducted  = body.deduct_funds,
        funds_remaining = round(inv.funds, 2),
        notes           = (
            f"{body.notes or ''} | "
            f"{body.tier} machine added (throughput {cfg['throughput']}, "
            f"base grade {cfg['grade']}, condition {body.starting_condition})"
        ).strip(" |"),
    )


# ── Preview ───────────────────────────────────────────────────────────────────

@router.get("/preview/{team_id}",
            summary="Preview a team's current component and machine state "
                    "before deciding what to auction to them.")
def auction_preview(
    team_id: int,
    game:    Game    = Depends(verify_organiser),
    db:      Session = Depends(get_db),
):
    """
    Shows the organiser what a team currently has per component:
    - Raw stock totals
    - Finished stock totals
    - All machines (tier, condition, throughput)
    - Current funds

    Useful for deciding whether to auction additional raw material, components,
    or machines to a specific team.
    """
    team = _get_team(team_id, game.id, db)
    inv  = db.query(Inventory).filter(Inventory.team_id == team.id).first()

    slots = db.query(ComponentSlot).filter(
        ComponentSlot.team_id == team.id
    ).order_by(ComponentSlot.component).all()

    components = []
    for slot in slots:
        machines = db.query(Machine).filter(
            Machine.slot_id == slot.id
        ).order_by(Machine.id).all()

        active_tp = sum(
            MACHINE_TIERS.get(m.tier, MACHINE_TIERS["standard"])["throughput"]
            for m in machines if m.is_active
        )

        components.append({
            "component":       slot.component.value,
            "raw_stock_total": sum(slot.raw_stock[1:])       if slot.raw_stock      else 0,
            "fin_stock_total": sum(slot.finished_stock[1:])  if slot.finished_stock else 0,
            "rnd_quality":     slot.rnd_quality,
            "rnd_consistency": slot.rnd_consistency,
            "rnd_yield":       slot.rnd_yield,
            "total_throughput": active_tp,
            "machines": [
                {
                    "id":        m.id,
                    "tier":      m.tier,
                    "condition": round(m.condition, 1),
                    "is_active": m.is_active,
                    "source":    m.source,
                    "throughput": MACHINE_TIERS.get(
                        m.tier, MACHINE_TIERS["standard"]
                    )["throughput"] if m.is_active else 0,
                }
                for m in machines
            ],
        })

    return {
        "team":       {"id": team.id, "name": team.name},
        "funds":      round(inv.funds, 2) if inv else 0.0,
        "components": components,
    }

