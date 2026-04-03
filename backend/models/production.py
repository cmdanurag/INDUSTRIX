"""
models/production.py
====================
MemoryProduction — last cycle's production decisions (one row per team).

Machine state, labour state, and R&D levels live in ComponentSlot and
Inventory (persistent). This table only stores the *decisions* made
last cycle so they can be used as defaults this cycle.
"""
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, String,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from core.database import Base


class MemoryProduction(Base):
    """
    Last cycle's production decisions for one team.
    PATCH semantics — send only what changed.

    decisions: {
        "airframe": {
            "maintenance": "basic",      -- MaintenanceLevel
            "rnd_invest": {              -- optional
                "focus": "quality",
                "levels": 1
            },
            "upgrade_to": null           -- MachineTier or null
        },
        ... (one entry per component),
        "wage_level": "market",          -- WageLevel
        "target_headcount": 50,
        "upgrade_automation": null       -- AutomationLevel or null
    }
    """
    __tablename__ = "memory_production"
    __table_args__ = (
        UniqueConstraint("team_id", name="uq_mem_prod_team"),
    )

    id      = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("team.id", ondelete="CASCADE"),
                     nullable=False, unique=True, index=True)

    decisions  = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    team = relationship("Team", back_populates="memory_production")