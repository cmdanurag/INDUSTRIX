"""
models/market.py
================
MarketFaction — one buyer faction in the sales market.

Each faction is configured per-game by the organiser and can be
adjusted between cycles. The sales engine runs each faction
independently as a rational buyer.

Schema:
    name             : display name (e.g. "Government Procurement")
    tier_preference  : which quality tier they primarily want
    price_ceiling    : max CU/unit they will pay at full volume
    volume           : how many units they want this cycle
    flexibility      : 0.0–1.0 — willingness to step down one tier
                       if ideal is unavailable.
                       0.0 = will not compromise at all
                       1.0 = will buy anything available
    brand_min        : minimum brand score they'll buy from (0 = no min)
    is_active        : organiser can disable a faction mid-game
"""

from sqlalchemy import (
    Boolean, Column, DateTime, Float,
    ForeignKey, Integer, String,
    UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from core.database import Base


class MarketFaction(Base):
    __tablename__ = "market_faction"
    __table_args__ = (
        UniqueConstraint("game_id", "name", name="uq_faction_name_per_game"),
    )

    id      = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game.id", ondelete="CASCADE"),
                     nullable=False, index=True)

    name             = Column(String(100), nullable=False)
    # QualityTier value: "reject" | "substandard" | "standard" | "premium"
    tier_preference  = Column(String(20),  nullable=False, default="standard")
    price_ceiling    = Column(Float,       nullable=False, default=3_000.0)
    volume           = Column(Integer,     nullable=False, default=200)
    flexibility      = Column(Float,       nullable=False, default=0.3)
    brand_min        = Column(Float,       nullable=False, default=0.0)
    is_active        = Column(Boolean,     nullable=False, default=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    game = relationship("Game", back_populates="market_factions")
