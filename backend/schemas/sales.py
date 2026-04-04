"""
schemas/sales.py
================
Request and response schemas for sales decisions and leaderboard.

Sales phase scope (updated):
  1. Assembly: team chooses how many drones to assemble (0 to max possible).
               Max possible = min(finished_stock_total) across all six components.
  2. Selling:  per-tier actions on the assembled + carried drone stock.

units_to_assemble is the new top-level field in SalesPatch.
It defaults to None (server assembles as many as possible).
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator

from core.enums import QualityTier, SalesAction


class TierSalesDecision(BaseModel):
    """
    What to do with drones in one quality tier.
    price_override: if set, overrides the default market price for sell actions.
    """
    action:         SalesAction     = Field(SalesAction.SELL_MARKET)
    price_override: Optional[float] = Field(None, gt=0,
        description="Override the default price per unit. "
                    "Only valid for sell_market, sell_premium, sell_discounted.")


class SalesPatch(BaseModel):
    """
    PATCH body for sales decisions. Send only what changed.

    units_to_assemble:
        How many drones to assemble from finished component inventory
        before selling. Range: 0 to max_possible.
        max_possible = min(sum(finished_stock[1:])) across all six components.
        Null means assemble the maximum possible (default).

    decisions:
        Per-tier selling decisions. Partial — unspecified tiers carry forward.
    """
    units_to_assemble: Optional[int]                    = Field(None, ge=0,
        description="Drones to assemble this cycle. "
                    "Null = assemble as many as possible.")
    decisions:         Dict[str, TierSalesDecision]     = Field(
        default_factory=dict,
        description="Map of quality tier → selling decision.",
    )

    @validator("decisions")
    def valid_tiers(cls, v):
        valid = {t.value for t in QualityTier}
        for key in v:
            if key not in valid:
                raise ValueError(f"Unknown quality tier: '{key}'.")
        return v


class SalesMemoryOut(BaseModel):
    """What the team sees when they GET their current sales decisions."""
    decisions:         dict

    model_config = {
        "from_attributes": True
    }


# ── Leaderboard ───────────────────────────────────────────────────────────────

class LeaderboardRow(BaseModel):
    rank:              int
    team_name:         str
    composite_score:   float
    closing_funds:     float
    cumulative_profit: float
    brand_score:       float
    quality_avg:       float
    inventory_penalty: float


class LeaderboardOut(BaseModel):
    cycle_number: int
    is_final:     bool
    rows:         List[LeaderboardRow]


# ── Inventory snapshot ────────────────────────────────────────────────────────

class InventoryOut(BaseModel):
    """Summary of a team's own state — returned by GET /team/me."""
    funds:             float
    brand_score:       float
    brand_tier:        str
    drone_stock_total: int
    workforce_size:    int
    skill_level:       float
    morale:            float
    automation_level:  str
    has_gov_loan:      bool

    model_config = {
        "from_attributes": True
    }