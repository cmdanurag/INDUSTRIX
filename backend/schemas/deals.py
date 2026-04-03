"""
schemas/deals.py
================
Organiser-side schemas for deals, events, and game control.

Reflects the new Event table structure:
  - Every event is a single-cycle atomic row.
  - Multi-cycle obligations (loans) are pre-generated as N separate rows.
  - The EventOut schema maps to the new Event ORM model.
  - Loan and global-event creation bodies are purpose-built rather than
    using a generic EventCreate that accepted arbitrary event_type values.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator

from core.enums import EventPhase, EventType, GovDealType


# ── Government deals ──────────────────────────────────────────────────────────

class GovDealCreate(BaseModel):
    buyer_team_id:   int         = Field(..., gt=0)
    deal_type:       GovDealType
    bribe_amount:    float       = Field(..., gt=0)
    target_team_id:  Optional[int] = Field(
        None, gt=0,
        description="Required for RED_* offensive deals. Null for GREEN_* self-buffs.",
    )
    override_params: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Override specific effect payload keys computed by the server. "
            "Example: for green_gov_purchase, set "
            "{\"units\": 100, \"price_per_unit\": 2800}."
        ),
    )
    notes: Optional[str] = None


class GovDealOut(BaseModel):
    id:                    int
    game_id:               int
    buyer_team_id:         int
    target_team_id:        Optional[int]
    deal_type:             str
    status:                str
    bribe_amount:          float
    effect_scale:          float
    effect_payload:        dict
    discovery_probability: float
    cycles_active:         int
    repeat_count:          int
    negotiated_cycle_id:   int
    notes:                 Optional[str]
    applied_at:            Optional[Any]
    created_at:            Any

    model_config = {
        "from_attributes" : True
    }


# ── Event (single row, single cycle) ─────────────────────────────────────────

class EventOut(BaseModel):
    """
    Maps to the Event ORM model.
    One row = one event firing in one cycle.
    """
    id:             int
    game_id:        int
    cycle_id:       int
    target_team_id: Optional[int]
    source_team_id: Optional[int]
    phase:          str
    event_type:     str
    payload:        dict
    status:         str
    gov_deal_id:    Optional[int]
    notes:          Optional[str]
    created_at:     Any
    applied_at:     Optional[Any]

    model_config = {
        "from_attributes": True
    }


# ── Loan creation bodies ──────────────────────────────────────────────────────
# These are purpose-built because loans are NOT created via the generic
# GovDeal flow — they are created directly by the organiser and immediately
# generate Event rows (one per interest-due cycle).

class InterTeamLoanCreate(BaseModel):
    borrower_team_id: int   = Field(..., gt=0)
    lender_team_id:   int   = Field(..., gt=0)
    principal:        float = Field(..., gt=0,
        description="Amount transferred from lender to borrower immediately.")
    interest_rate:    float = Field(..., ge=0.02, le=0.12,
        description="Per-cycle interest rate (0.02 = 2%, 0.12 = 12%).")
    duration_cycles:  int   = Field(1, ge=1,
        description="Number of cycles interest is charged.")
    notes:            Optional[str] = None

    @validator("lender_team_id")
    def lender_ne_borrower(cls, v, values):
        if "borrower_team_id" in values and v == values["borrower_team_id"]:
            raise ValueError("Lender and borrower cannot be the same team.")
        return v


class GovLoanCreate(BaseModel):
    borrower_team_id: int   = Field(..., gt=0)
    principal:        float = Field(..., gt=0,
        description="Amount credited to borrower. Interest rate is fixed at 15%/cycle.")
    duration_cycles:  int   = Field(1, ge=1,
        description="Number of cycles interest is charged.")
    notes:            Optional[str] = None


# ── Global event creation body ────────────────────────────────────────────────

class GlobalEventCreate(BaseModel):
    """
    A global event adjusts game-level parameters for one or more cycles.
    Each cycle gets its own Event row (pre-generated at creation time).

    payload keys (all optional — include only what you want to change):
        market_demand_multiplier_delta: float  e.g. -0.2 shrinks market by 20%
        qr_hard_delta:                  float  e.g. +5 raises the reject threshold
        qr_soft_delta:                  float
        qr_premium_delta:               float
    """
    duration_cycles: int            = Field(1, ge=1,
        description="How many consecutive cycles this event fires.")
    payload:         Dict[str, Any] = Field(...,
        description="Effect parameters. See GlobalEventCreate docstring.")
    notes:           Optional[str]  = None

    @validator("payload")
    def payload_not_empty(cls, v):
        allowed = {
            "market_demand_multiplier_delta",
            "qr_hard_delta", "qr_soft_delta", "qr_premium_delta",
        }
        unknown = set(v.keys()) - allowed
        if unknown:
            raise ValueError(
                f"Unknown payload keys: {unknown}. "
                f"Allowed: {allowed}"
            )
        if not v:
            raise ValueError("payload cannot be empty.")
        return v


# ── Loan creation response ────────────────────────────────────────────────────

class LoanCreatedOut(BaseModel):
    """Returned after creating a loan — summarises what was generated."""
    events_created:  int
    borrower_team_id: int
    lender_team_id:  Optional[int]   # None = government
    principal:       float
    interest_rate:   float
    amount_per_cycle: float
    duration_cycles: int
    total_interest:  float


# ── Game control ──────────────────────────────────────────────────────────────

class AdvancePhaseOut(BaseModel):
    previous_phase: str
    current_phase:  str
    cycle_number:   int


class GameUpdateSettings(BaseModel):
    """
    Organiser updates these during BACKROOM phase.
    Values take effect in the NEXT cycle (snapshotted at cycle creation).
    """
    qr_hard:                  Optional[float] = Field(None, ge=0, le=100)
    qr_soft:                  Optional[float] = Field(None, ge=0, le=100)
    qr_premium:               Optional[float] = Field(None, ge=0, le=100)
    market_demand_multiplier: Optional[float] = Field(None, gt=0)