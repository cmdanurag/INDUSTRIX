"""
schemas/procurement.py
======================
Request and response schemas for procurement decisions.
"""
from typing import Dict, Optional
from pydantic import BaseModel, Field, validator

from core.enums import ComponentType, TransportMode


class ComponentProcurementDecision(BaseModel):
    """Decision for one component."""
    source_id: int           = Field(..., gt=0)
    quantity:  int           = Field(..., ge=0, le=10_000)
    transport: TransportMode = Field(TransportMode.ROAD)


class ProcurementPatch(BaseModel):
    """
    PATCH body. Send only the components you want to change.
    Unspecified components keep last cycle's decision.

    Example:
        {"airframe": {"source_id": 2, "quantity": 300, "transport": "rail"}}
    """
    decisions: Dict[str, ComponentProcurementDecision] = Field(
        default_factory=dict,
        description="Map of component value → decision. Partial updates allowed.",
    )

    @validator("decisions")
    def valid_components(cls, v):
        valid = {c.value for c in ComponentType}
        for key in v:
            if key not in valid:
                raise ValueError(f"Unknown component: {key}")
        return v


class RawMaterialSourceOut(BaseModel):
    """
    One supplier row shown to teams during PROCUREMENT_OPEN.
    quality_mean and quality_sigma are shown so teams can make
    informed decisions about quality/cost trade-offs.
    is_active is always True here (inactive sources are filtered out).
    """
    id: int
    component: str  # ComponentType value
    name: str
    distance: int
    quality_mean: float
    quality_sigma: float
    base_cost_per_unit: float
    min_order: int
    max_order: int

    model_config = {
        "from_attributes": True
    }


class ProcurementMemoryOut(BaseModel):
    """Current (last cycle's) procurement decisions — shown to the team."""
    decisions: Dict[str, dict]

    model_config = {
        "from_attributes": True
    }

class TransportOut(BaseModel):
    base_cost: float
    var_cost: float
    sigma_add: float
    p_damage: float
    mean_reduce: float
    vulnerability: float

    model_config = {
        "from_attributes": True
    }

class CostProjectionOut(BaseModel):
    total_cost: float
    per_component: Dict[str, dict]

    model_config = {
        "from_attributes": True
    }