"""
industrix/schemas/procurement.py
==================================
Pydantic v2 schemas for the procurement subsystem.

Input schemas  (suffix *In or *Update) — what the API receives.
Output schemas (suffix *Out)           — what the API returns.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from core.enums import ComponentType, ShipmentEventType, TransportMode


# ─────────────────────────────────────────────────────────────────────────────
# Source schemas  (organiser-managed)
# ─────────────────────────────────────────────────────────────────────────────

class SourceCreate(BaseModel):
    """Organiser creates a new raw material source for a game."""
    name:                 str   = Field(min_length=1, max_length=150)
    component:            ComponentType
    location_description: Optional[str] = None
    distance_km:          float = Field(gt=0, description="Distance from factory in km")
    base_cost_per_unit:   float = Field(gt=0, description="CU per unit before transport multiplier")
    quality_mean:         float = Field(ge=1, le=100, description="Mean of quality Normal distribution")
    quality_sigma:        float = Field(ge=0.5, le=40, description="Std dev of quality Normal distribution")
    is_available:         bool  = True


class SourceUpdate(BaseModel):
    """
    Organiser modifies a source's parameters between cycles.
    All fields optional — only provided fields are updated.
    An event_name and description must accompany any change (logged in SourceEventLog).
    """
    quality_mean:        Optional[float] = Field(None, ge=1,   le=100)
    quality_sigma:       Optional[float] = Field(None, ge=0.5, le=40)
    base_cost_per_unit:  Optional[float] = Field(None, gt=0)
    is_available:        Optional[bool]  = None
    event_name:          str             = Field(min_length=1,
                                                  description="Short name for the event (e.g. 'over_extraction')")
    description:         Optional[str]   = None

    @model_validator(mode="after")
    def at_least_one_change(self) -> "SourceUpdate":
        changed = any([
            self.quality_mean       is not None,
            self.quality_sigma      is not None,
            self.base_cost_per_unit is not None,
            self.is_available       is not None,
        ])
        if not changed:
            raise ValueError("At least one parameter must be updated.")
        return self


class SourceOut(BaseModel):
    id:                   int
    game_id:              int
    name:                 str
    component:            ComponentType
    location_description: Optional[str]
    distance_km:          float
    base_cost_per_unit:   float
    quality_mean:         float
    quality_sigma:        float
    is_available:         bool
    created_at:           datetime
    updated_at:           datetime

    model_config = {"from_attributes": True}


class SourceEventLogOut(BaseModel):
    id:                  int
    source_id:           int
    cycle_id:            Optional[int]
    event_name:          str
    description:         Optional[str]
    quality_mean_delta:  Optional[float]
    quality_sigma_delta: Optional[float]
    cost_multiplier:     Optional[float]
    availability_change: Optional[bool]
    created_at:          datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Decision schemas  (team-managed, persists between cycles)
# ─────────────────────────────────────────────────────────────────────────────

class ProcurementDecisionUpdate(BaseModel):
    """
    Team updates their standing decision for one component.
    PATCH semantics — only provided fields are changed.
    """
    source_id:      Optional[int]           = Field(None, description="Set null to stop buying this component")
    quantity:       Optional[int]           = Field(None, ge=0, le=10_000)
    transport_mode: Optional[TransportMode] = None


class ProcurementDecisionOut(BaseModel):
    """The team's current standing decision for one component."""
    id:             int
    team_id:        int
    component:      ComponentType
    source_id:      Optional[int]
    source_name:    Optional[str]   = None   # Populated by joining to source
    quantity:       int
    transport_mode: TransportMode
    # Estimated cost for this order (computed from current source params).
    estimated_unit_cost:  Optional[float] = None
    estimated_total_cost: Optional[float] = None
    updated_at:     datetime

    model_config = {"from_attributes": True}


class AllProcurementDecisionsOut(BaseModel):
    """All six component decisions for one team — shown on the team dashboard."""
    team_id:   int
    decisions: List[ProcurementDecisionOut]
    # Total estimated procurement cost across all components.
    estimated_total_cost: float


# ─────────────────────────────────────────────────────────────────────────────
# Order and shipment schemas  (created at cycle resolution)
# ─────────────────────────────────────────────────────────────────────────────

class ProcurementOrderOut(BaseModel):
    """One concrete order from one cycle — read-only result data."""
    id:               int
    team_id:          int
    cycle_id:         int
    source_id:        Optional[int]
    component:        ComponentType
    transport_mode:   TransportMode
    quantity_ordered: int
    unit_cost:        float
    total_cost:       float
    shipment_event:   ShipmentEventType
    was_sabotaged:    bool
    sabotage_loss_fraction: float
    created_at:       datetime

    model_config = {"from_attributes": True}


class ShipmentResultOut(BaseModel):
    """
    The quality distribution array for one shipment.
    This is the primary output of the procurement system.
    """
    id:            int
    order_id:      int
    component:     ComponentType   # Populated by joining to order
    quality_array: List[int]       # 101 integers: index 0 = lost, 1–100 = usable grades
    total_usable:  int
    total_lost:    int
    weighted_mean: Optional[float]
    min_grade:     Optional[int]
    max_grade:     Optional[int]

    model_config = {"from_attributes": True}

    @field_validator("quality_array")
    @classmethod
    def must_be_101(cls, v: List[int]) -> List[int]:
        if len(v) != 101:
            raise ValueError("quality_array must have exactly 101 elements (index 0–100).")
        return v


class CycleProcurementReport(BaseModel):
    """
    Full procurement report for one team after one cycle resolves.
    This is what gets displayed to the team at the start of the next cycle.
    """
    team_id:      int
    cycle_id:     int
    cycle_number: int

    orders:        List[ProcurementOrderOut]
    shipments:     List[ShipmentResultOut]

    # Aggregated across all components.
    total_cost:         float
    total_units_ordered: int
    total_units_arrived: int   # sum of all total_usable
    total_units_lost:    int   # sum of all total_lost

    # Per-component summary for quick display.
    # { "airframe": {"ordered": 500, "arrived": 480, "lost": 20, "mean_grade": 72.3} }
    per_component_summary: dict
