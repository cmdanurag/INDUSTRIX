"""
models/game.py
==============
Core structural tables: Game, Team, Cycle, CyclePhaseLog,
RawMaterialSource.

These are the backbone everything else references via FK.
"""
import secrets
from datetime import datetime

from anyio.streams.text import TextSendStream
from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SAEnum,
    Float, ForeignKey, Integer, String, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from core.database import Base
from core.enums import ComponentType, CyclePhase, TransportMode


class Game(Base):
    """
    One game instance = one Industrix competition session.
    Only one game is active at a time.

    organiser_secret: long random hex string generated at creation.
    The organiser includes this in every admin request header.
    """
    __tablename__ = "game"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(200), nullable=False)
    is_active        = Column(Boolean, nullable=False, default=True)

    # Global quality thresholds — snapshotted into each cycle.
    qr_hard    = Column(Float, nullable=False, default=30.0)
    qr_soft    = Column(Float, nullable=False, default=50.0)
    qr_premium = Column(Float, nullable=False, default=75.0)

    # Global market multiplier — can be changed between cycles.
    market_demand_multiplier = Column(Float, nullable=False, default=1.0)

    # Starting funds given to each team.
    starting_funds = Column(Float, nullable=False, default=100_000.0)

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    teams   = relationship("Team",             back_populates="game",
                            cascade="all, delete-orphan")
    cycles  = relationship("Cycle",            back_populates="game",
                            cascade="all, delete-orphan")
    sources = relationship("RawMaterialSource", back_populates="game",
                            cascade="all, delete-orphan")
    market_factions = relationship("MarketFaction", back_populates="game",
                                   cascade="all, delete-orphan")


class Team(Base):
    """
    A competing company. One row per team.
    pin_hash = sha256(raw_pin) — never store the raw PIN.
    """
    __tablename__ = "team"

    id       = Column(Integer, primary_key=True, index=True)
    game_id  = Column(Integer, ForeignKey("game.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    name     = Column(String(100), nullable=False)
    pin_hash = Column(String(64),  nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("game_id", "name", name="uq_team_name_per_game"),
    )

    # Relationships
    game      = relationship("Game",      back_populates="teams")
    inventory = relationship("Inventory", back_populates="team",
                              uselist=False, cascade="all, delete-orphan")
    component_slots = relationship("ComponentSlot", back_populates="team",
                                    cascade="all, delete-orphan")
    memory_procurement = relationship("MemoryProcurement", back_populates="team",
                                       uselist=False, cascade="all, delete-orphan")
    memory_production  = relationship("MemoryProduction",  back_populates="team",
                                       uselist=False, cascade="all, delete-orphan")
    memory_sales       = relationship("MemorySales",       back_populates="team",
                                       uselist=False, cascade="all, delete-orphan")


class Cycle(Base):
    """
    One game cycle. Created by the organiser.
    Thresholds are snapshotted from the game at creation time so
    historical cycles are always reproducible.
    """
    __tablename__ = "cycle"

    id           = Column(Integer, primary_key=True, index=True)
    game_id      = Column(Integer, ForeignKey("game.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    cycle_number = Column(Integer, nullable=False)

    # Snapshotted at cycle creation.
    qr_hard                  = Column(Float, nullable=False)
    qr_soft                  = Column(Float, nullable=False)
    qr_premium               = Column(Float, nullable=False)
    market_demand_multiplier = Column(Float, nullable=False)

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("game_id", "cycle_number", name="uq_cycle_number_per_game"),
    )

    game      = relationship("Game",          back_populates="cycles")
    phase_log = relationship("CyclePhaseLog", back_populates="cycle",
                              uselist=False, cascade="all, delete-orphan")


class CyclePhaseLog(Base):
    """
    Tracks the current phase of a cycle and timestamps for each transition.
    Also stores per-team resolution summaries written at advance_phase time.

    production_summary: {team_id: {components, riot, wage_total, ...}}
    sales_summary:      {team_id: {units_sold, total_revenue, tier_sold, ...}}

    These are written once at resolution and never updated — they are the
    historical record of what happened each cycle.
    """
    __tablename__ = "cycle_phase_log"
    __table_args__ = (
        UniqueConstraint("cycle_id", name="uq_phase_log_cycle"),
    )

    id       = Column(Integer, primary_key=True, index=True)
    cycle_id = Column(Integer, ForeignKey("cycle.id", ondelete="CASCADE"),
                      nullable=False, unique=True, index=True)

    current_phase = Column(SAEnum(CyclePhase), nullable=False,
                            default=CyclePhase.PROCUREMENT_OPEN)

    procurement_opened_at = Column(DateTime, nullable=True)
    production_opened_at  = Column(DateTime, nullable=True)
    sales_opened_at       = Column(DateTime, nullable=True)
    backroom_opened_at    = Column(DateTime, nullable=True)
    completed_at          = Column(DateTime, nullable=True)

    # Resolution summaries — written once when each phase resolves.
    procurement_summary = Column(JSONB, nullable=True)  # {str(team_id): {...}}
    production_summary = Column(JSONB, nullable=True)   # {str(team_id): {...}}
    sales_summary      = Column(JSONB, nullable=True)   # {str(team_id): {...}}

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    cycle = relationship("Cycle", back_populates="phase_log")
    """
    Tracks the current phase of a cycle and timestamps for each transition.
    One row per cycle, created when the cycle is created.

    The organiser calls /advance to move through:
      PROCUREMENT_OPEN → PRODUCTION_OPEN → SALES_OPEN → BACKROOM

    From BACKROOM the organiser calls /next or /end-game.
    """
    __tablename__ = "cycle_phase_log"

    id       = Column(Integer, primary_key=True, index=True)
    cycle_id = Column(Integer, ForeignKey("cycle.id", ondelete="CASCADE"),
                      nullable=False, unique=True, index=True)

    current_phase = Column(SAEnum(CyclePhase), nullable=False,
                            default=CyclePhase.PROCUREMENT_OPEN)

    procurement_opened_at = Column(DateTime, nullable=True)
    production_opened_at  = Column(DateTime, nullable=True)
    sales_opened_at       = Column(DateTime, nullable=True)
    backroom_opened_at    = Column(DateTime, nullable=True)
    completed_at          = Column(DateTime, nullable=True)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    cycle = relationship("Cycle", back_populates="phase_log")


class RawMaterialSource(Base):
    """
    A supplier for one component type.
    Multiple sources can exist per component — teams choose which to order from.
    """
    __tablename__ = "raw_material_source"

    id        = Column(Integer, primary_key=True, index=True)
    game_id   = Column(Integer, ForeignKey("game.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    component = Column(SAEnum(ComponentType), nullable=False)
    name      = Column(String(100), nullable=False)

    distance  = Column(Integer, nullable=False, default=500)
    note      = Column(String(200), nullable=True)

    quality_mean  = Column(Float, nullable=False)   # Centre of Normal draw
    quality_sigma = Column(Float, nullable=False)   # Spread of Normal draw
    base_cost_per_unit = Column(Float, nullable=False)
    min_order     = Column(Integer, nullable=False, default=1)
    max_order     = Column(Integer, nullable=False, default=10_000)
    is_active     = Column(Boolean, nullable=False, default=True)

    game = relationship("Game", back_populates="sources")