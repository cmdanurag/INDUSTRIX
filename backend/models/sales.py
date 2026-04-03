"""
models/sales.py
===============
MemorySales — last cycle's sales decisions (one row per team).
"""

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from core.database import Base


class MemorySales(Base):
    """
    Last cycle's sales decisions for one team.
    PATCH semantics — send only what changed.

    decisions: {
        "reject":      {"action": "scrap",          "price_override": null},
        "substandard": {"action": "sell_discounted", "price_override": null},
        "standard":    {"action": "sell_market",     "price_override": null},
        "premium":     {"action": "sell_premium",    "price_override": null}
    }
    """
    __tablename__ = "memory_sales"
    __table_args__ = (
        UniqueConstraint("team_id", name="uq_mem_sales_team"),
    )

    id      = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("team.id", ondelete="CASCADE"),
                     nullable=False, unique=True, index=True)

    decisions  = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    team = relationship("Team", back_populates="memory_sales")