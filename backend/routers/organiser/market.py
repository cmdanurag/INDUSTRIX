"""
routers/organiser/market.py
============================
Organiser endpoints for managing market factions.

GET    /organiser/market/factions          — list all factions
POST   /organiser/market/factions          — create a new faction
PATCH  /organiser/market/factions/{id}     — update a faction
DELETE /organiser/market/factions/{id}     — disable a faction
POST   /organiser/market/factions/reset    — reset to game defaults

All endpoints require organiser auth.
All changes take effect immediately — they apply to the NEXT sales resolution.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core.auth import verify_organiser
from core.config import DEFAULT_MARKET_FACTIONS, TIER_FALLBACK
from core.database import get_db
from models.game import Game
from models.market import MarketFaction
from schemas.common import OkResponse

router = APIRouter(prefix="/organiser/market", tags=["organiser"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class FactionCreate(BaseModel):
    name:            str   = Field(min_length=1, max_length=100)
    tier_preference: str   = Field(description="reject | substandard | standard | premium")
    price_ceiling:   float = Field(gt=0)
    volume:          int   = Field(gt=0)
    flexibility:     float = Field(ge=0.0, le=1.0)
    brand_min:       float = Field(ge=0.0, le=100.0, default=0.0)

    @field_validator("tier_preference")
    @classmethod
    def valid_tier(cls, v):
        valid = set(TIER_FALLBACK.keys())
        if v not in valid:
            raise ValueError(f"tier_preference must be one of {sorted(valid)}")
        return v


class FactionPatch(BaseModel):
    name:            Optional[str]   = Field(None, min_length=1, max_length=100)
    tier_preference: Optional[str]   = None
    price_ceiling:   Optional[float] = Field(None, gt=0)
    volume:          Optional[int]   = Field(None, gt=0)
    flexibility:     Optional[float] = Field(None, ge=0.0, le=1.0)
    brand_min:       Optional[float] = Field(None, ge=0.0, le=100.0)
    is_active:       Optional[bool]  = None

    @field_validator("tier_preference")
    @classmethod
    def valid_tier(cls, v):
        if v is None:
            return v
        valid = set(TIER_FALLBACK.keys())
        if v not in valid:
            raise ValueError(f"tier_preference must be one of {sorted(valid)}")
        return v


class FactionOut(BaseModel):
    id:              int
    name:            str
    tier_preference: str
    price_ceiling:   float
    volume:          int
    flexibility:     float
    brand_min:       float
    is_active:       bool

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_faction(faction_id: int, game_id: int, db: Session) -> MarketFaction:
    f = db.query(MarketFaction).filter(
        MarketFaction.id      == faction_id,
        MarketFaction.game_id == game_id,
    ).first()
    if not f:
        raise HTTPException(404, f"Faction {faction_id} not found.")
    return f


def seed_market_factions(db: Session, game: Game) -> List[MarketFaction]:
    """
    Called once when a game is created.
    Seeds the six default factions from config.
    """
    rows = []
    for defn in DEFAULT_MARKET_FACTIONS:
        faction = MarketFaction(game_id=game.id, **defn)
        db.add(faction)
        rows.append(faction)
    db.flush()
    return rows


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/factions",
    response_model=List[FactionOut],
    summary="List all market factions for this game",
)
def list_factions(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Returns all factions (active and inactive) in the current game.
    Teams cannot see this endpoint — factions are opaque to players.
    This is deliberate: teams must infer market preferences from sales results.
    """
    return (
        db.query(MarketFaction)
        .filter(MarketFaction.game_id == game.id)
        .order_by(MarketFaction.id)
        .all()
    )


@router.post(
    "/factions",
    response_model=FactionOut,
    status_code=201,
    summary="Add a new market faction",
)
def create_faction(
    body: FactionCreate,
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Add a new buyer faction to the market.
    Takes effect at the next sales resolution.
    """
    faction = MarketFaction(game_id=game.id, **body.model_dump())
    db.add(faction)
    db.commit()
    db.refresh(faction)
    return faction


@router.patch(
    "/factions/{faction_id}",
    response_model=FactionOut,
    summary="Update a faction's parameters",
)
def update_faction(
    faction_id: int,
    body:       FactionPatch,
    game:       Game    = Depends(verify_organiser),
    db:         Session = Depends(get_db),
):
    """
    Modify any faction parameter between cycles.
    For example: raise the Government faction's volume before a big cycle,
    or lower the NGO price ceiling to tighten the market.

    Changes take effect at the NEXT sales resolution — already-running
    resolutions are not affected.
    """
    faction = _get_faction(faction_id, game.id, db)

    if body.name            is not None: faction.name            = body.name
    if body.tier_preference is not None: faction.tier_preference = body.tier_preference
    if body.price_ceiling   is not None: faction.price_ceiling   = body.price_ceiling
    if body.volume          is not None: faction.volume          = body.volume
    if body.flexibility     is not None: faction.flexibility     = body.flexibility
    if body.brand_min       is not None: faction.brand_min       = body.brand_min
    if body.is_active       is not None: faction.is_active       = body.is_active

    db.commit()
    db.refresh(faction)
    return faction


@router.delete(
    "/factions/{faction_id}",
    response_model=OkResponse,
    summary="Disable a faction (soft delete — keeps history)",
)
def disable_faction(
    faction_id: int,
    game:       Game    = Depends(verify_organiser),
    db:         Session = Depends(get_db),
):
    """
    Marks a faction as inactive. It will be excluded from future market
    simulations but its row is preserved for audit / re-enabling.
    """
    faction            = _get_faction(faction_id, game.id, db)
    faction.is_active  = False
    db.commit()
    return OkResponse(message=f"Faction '{faction.name}' disabled.")


@router.post(
    "/factions/reset",
    response_model=List[FactionOut],
    summary="Reset all factions to game defaults",
)
def reset_factions(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Delete all current factions and re-seed from DEFAULT_MARKET_FACTIONS.
    Useful if you've made a mess of the faction config mid-game.
    """
    db.query(MarketFaction).filter(MarketFaction.game_id == game.id).delete()
    db.flush()
    rows = seed_market_factions(db, game)
    db.commit()
    return [db.query(MarketFaction).get(r.id) for r in rows]
