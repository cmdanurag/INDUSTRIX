"""
schemas/production.py
=====================
Request and response schemas for production decisions.

Production phase scope:
  Raw materials → finished components only.
  No assembly happens here — assembly moved to sales phase.

Key changes from previous version:
  - upgrade_to removed (replaced by buy_machine: buy N new machines)
  - units_to_produce added (0 to total throughput — team's explicit choice)
  - units_to_assemble removed (lives in SalesPatch now)
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator

from core.enums import (
    AutomationLevel, ComponentType, MachineTier,
    MaintenanceLevel, RndFocus, WageLevel,
)


class RndInvestDecision(BaseModel):
    focus:  RndFocus = Field(..., description="quality, consistency, or yield")
    levels: int      = Field(1, ge=1, le=5,
        description="Number of R&D levels to invest in. "
                    "Each level costs 10,000 CU and takes 2 cycles to arrive.")


class MachinePurchase(BaseModel):
    """Buy one new machine of the given tier for this component."""
    tier: MachineTier = Field(...,
        description="Tier of the machine to purchase. "
                    "Cost is deducted immediately at production resolution.")


class ComponentProductionDecision(BaseModel):
    """
    Decisions for one component during the production phase.

    maintenance:     How well to service all machines for this component.
                     One level applies equally to every machine.
    units_to_produce: How many raw material units to convert to finished
                     components this cycle. Range: 0 to total throughput
                     of all active machines for this component.
                     Defaults to max throughput if not set (server clamps).
    rnd_invest:      Optional R&D investment this cycle.
    buy_machine:     Optional: purchase one new machine. Deducted immediately.
                     Teams can buy multiple machines per cycle by submitting
                     multiple PATCHes, or the organiser can use the auction
                     transfer endpoint.
    """
    maintenance:      MaintenanceLevel          = Field(MaintenanceLevel.NONE)
    units_to_produce: Optional[int]             = Field(None, ge=0,
        description="Units of raw material to convert. "
                    "Null means use max available throughput.")
    rnd_invest:       Optional[RndInvestDecision] = Field(None)
    buy_machine:      Optional[MachinePurchase]   = Field(None)


class ProductionPatch(BaseModel):
    """
    PATCH body. Send only what changed.
    Unspecified components and labour fields carry forward from last cycle.
    """
    component_decisions: Dict[str, ComponentProductionDecision] = Field(
        default_factory=dict,
        description="Map of component value → decision. Partial updates allowed.",
    )
    wage_level:         Optional[WageLevel]       = Field(None)
    target_headcount:   Optional[int]             = Field(None, ge=0, le=500)
    upgrade_automation: Optional[AutomationLevel] = Field(None)

    @validator("component_decisions")
    def valid_components(cls, v):
        valid = {c.value for c in ComponentType}
        for key in v:
            if key not in valid:
                raise ValueError(f"Unknown component: '{key}'.")
        return v


class ProductionMemoryOut(BaseModel):
    """What the team sees when they GET their current production decisions."""
    decisions: dict

    model_config = {
        "from_attributes" : True
    }


# ── Machine state (returned in inventory views) ───────────────────────────────

class MachineOut(BaseModel):
    """State of one physical machine."""
    id:              int
    tier:            str
    condition:       float
    is_active:       bool
    purchased_cycle: Optional[int]
    source:          str
    throughput:      int    # from config, not stored — computed on read
    base_grade:      int    # from config

    model_config = {
        "from_attributes" : True
    }


class ComponentSlotOut(BaseModel):
    """Full state of one component slot including all its machines."""
    component:         str
    raw_stock_total:   int
    fin_stock_total:   int
    rnd_quality:       int
    rnd_consistency:   int
    rnd_yield:         int
    machines:          List[MachineOut]
    total_throughput:  int   # sum of active machine throughputs


# ── Decision Support (Live Projections) ───────────────────────────────────────

class ComponentProjection(BaseModel):
    throughput_max:  int
    effective_grade: float
    sigma:           float
    cost_maint:      float
    cost_rnd:        float
    cost_buy:        float


class ProductionProjectionResponse(BaseModel):
    total_outflow:           float
    total_required_labour:   int
    labour_gap:              int
    labour_factor:           float
    projected_morale_delta:  float
    projected_morale:        float
    components:              Dict[str, ComponentProjection]