"""
schemas/game.py
===============
Pydantic schemas for game, team, cycle, and source endpoints.
"""
from typing import Optional
from pydantic import BaseModel, Field, validator


# ── Game ──────────────────────────────────────────────────────────────────────

class GameCreate(BaseModel):
    name:                    str   = Field(..., min_length=1, max_length=200)
    qr_hard:                 float = Field(30.0,  ge=0,  le=100)
    qr_soft:                 float = Field(50.0,  ge=0,  le=100)
    qr_premium:              float = Field(75.0,  ge=0,  le=100)
    market_demand_multiplier: float = Field(1.0,  gt=0)
    starting_funds:          float = Field(100_000.0, gt=0)

    @validator("qr_premium")
    def thresholds_ordered(cls, v, values):
        if "qr_soft" in values and v <= values["qr_soft"]:
            raise ValueError("qr_premium must be > qr_soft")
        return v


class GameOut(BaseModel):
    id:                      int
    name:                    str
    qr_hard:                 float
    qr_soft:                 float
    qr_premium:              float
    market_demand_multiplier: float
    starting_funds:          float
    is_active:               bool

    model_config = {
        "from_attributes" : True
    }


# ── Team ──────────────────────────────────────────────────────────────────────

class TeamCreate(BaseModel):
    name: str  = Field(..., min_length=1, max_length=100)
    pin:  str  = Field(..., min_length=4, max_length=50)


class TeamOut(BaseModel):
    id:        int
    name:      str
    is_active: bool

    model_config = {
        "from_attributes": True
    }


class TeamLoginResponse(BaseModel):
    team_id:   int
    team_name: str
    message:   str = "Login successful."


# ── Cycle ─────────────────────────────────────────────────────────────────────

class CycleOut(BaseModel):
    id:                      int
    cycle_number:            int
    qr_hard:                 float
    qr_soft:                 float
    qr_premium:              float
    market_demand_multiplier: float
    current_phase:           str

    model_config = {
        "from_attributes": True
    }


# ── RawMaterialSource ─────────────────────────────────────────────────────────

class SourceCreate(BaseModel):
    component:          str   = Field(..., description="ComponentType value")
    name:               str   = Field(..., min_length=1, max_length=100)
    quality_mean:       float = Field(..., ge=1,  le=100)
    quality_sigma:      float = Field(..., ge=0.5, le=30)
    base_cost_per_unit: float = Field(..., gt=0)
    min_order:          int   = Field(1,   ge=1)
    max_order:          int   = Field(10_000, ge=1)


class SourceOut(BaseModel):
    id:                 int
    component:          str
    name:               str
    quality_mean:       float
    quality_sigma:      float
    base_cost_per_unit: float
    min_order:          int
    max_order:          int
    is_active:          bool

    model_config = {
        "from_attributes": True
    }