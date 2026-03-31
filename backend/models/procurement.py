"""
industrix/models/procurement.py
=================================
SQLAlchemy ORM models for the procurement subsystem.

Tables defined here:
  Game            — top-level game instance (minimal, other systems will add to it)
  Team            — a playing company
  Cycle           — one game cycle
  RawMaterialSource  — an available supplier/source, pre-configured by organiser
  SourceEventLog     — history of organiser-triggered events that modify a source
  ProcurementDecision — the team's current standing order for one component
                        (persists between cycles; updated not replaced)
  ProcurementOrder    — one concrete order placed in one cycle
                        (created fresh each cycle from the decision state)
  ShipmentResult      — the resolved outcome of one order: the 101-int quality array

Relationship overview:

  Game ──< Cycle
  Game ──< Team
  Game ──< RawMaterialSource
  RawMaterialSource ──< SourceEventLog
  Team ──< ProcurementDecision   (one per component, persists)
  Team ──< ProcurementOrder      (one per component per cycle)
  ProcurementOrder ──1 ShipmentResult
"""

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SAEnum,
    Float, ForeignKey, Integer, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship

from core.database import Base
from core.enums import (
    ComponentType, ShipmentEventType, TransportMode,
)


# ─────────────────────────────────────────────────────────────────────────────
# Game  (minimal — other subsystems will reference game_id as FK)
# ─────────────────────────────────────────────────────────────────────────────

class Game(Base):
    """
    Top-level game instance. One game = one Industrix session (e.g. Srijan 2026).
    The organiser controls all cycle transitions.
    """
    __tablename__ = "game"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(200), nullable=False)

    # Global quality thresholds — set by organiser, can be changed between cycles.
    # qr_hard:    drones below this grade cannot be sold in regulated markets.
    # qr_soft:    drones between qr_hard and qr_soft are "sub-standard".
    # qr_premium: drones at or above this grade qualify for premium pricing.
    qr_hard    = Column(Float, nullable=False, default=20.0)
    qr_soft    = Column(Float, nullable=False, default=50.0)
    qr_premium = Column(Float, nullable=False, default=80.0)

    # Global market demand multiplier — organiser can adjust between cycles.
    market_demand_multiplier = Column(Float, nullable=False, default=1.0)

    total_cycles = Column(Integer, nullable=False, default=6)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    teams   = relationship("Team",              back_populates="game",
                           cascade="all, delete-orphan")
    cycles  = relationship("Cycle",             back_populates="game",
                           cascade="all, delete-orphan",
                           order_by="Cycle.cycle_number")
    sources = relationship("RawMaterialSource", back_populates="game",
                           cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# Team
# ─────────────────────────────────────────────────────────────────────────────

class Team(Base):
    """A playing team — one fire-fighting drone company."""
    __tablename__ = "team"

    id      = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    name    = Column(String(100), nullable=False)

    # Simple PIN for team auth (hash in production).
    pin_hash = Column(String(128), nullable=False, default="0000")

    is_active  = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    game                 = relationship("Game", back_populates="teams")
    procurement_decisions = relationship("ProcurementDecision",
                                         back_populates="team",
                                         cascade="all, delete-orphan")
    procurement_orders   = relationship("ProcurementOrder",
                                         back_populates="team",
                                         cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# Cycle
# ─────────────────────────────────────────────────────────────────────────────

class Cycle(Base):
    """
    One game cycle. The organiser opens and closes cycles explicitly.
    OPEN   → teams can update their decisions.
    CLOSED → organiser has triggered resolution; decisions are locked.
    """
    __tablename__ = "cycle"

    id           = Column(Integer, primary_key=True, index=True)
    game_id      = Column(Integer, ForeignKey("game.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    cycle_number = Column(Integer, nullable=False)   # 1-indexed

    # "open" or "closed" — the only two states the organiser toggles.
    status = Column(String(10), nullable=False, default="open")

    # Snapshot of market conditions at the moment this cycle was opened.
    # Stored so the debrief always shows what conditions were actually in effect.
    qr_hard    = Column(Float, nullable=False)
    qr_soft    = Column(Float, nullable=False)
    qr_premium = Column(Float, nullable=False)
    market_demand_multiplier = Column(Float, nullable=False, default=1.0)

    opened_at   = Column(DateTime, nullable=True)
    closed_at   = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    game   = relationship("Game", back_populates="cycles")
    orders = relationship("ProcurementOrder", back_populates="cycle",
                          cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# RawMaterialSource
# ─────────────────────────────────────────────────────────────────────────────

class RawMaterialSource(Base):
    """
    A source (supplier / mining location / factory) for one component type.
    Pre-configured by the organiser before the game starts.
    All teams see the same sources.

    The quality of materials from this source follows a Normal distribution
    with mean = quality_mean and std = quality_sigma (both on the 1–100 scale).
    Units drawn below MIN_USABLE_GRADE go to index 0 of the shipment array.

    Cost is deterministic: base_cost_per_unit × transport_multiplier,
    regardless of what quality was actually drawn.

    The organiser can modify quality_mean, quality_sigma, and base_cost_per_unit
    between cycles (e.g. to model an over-extraction event).
    All changes are logged in SourceEventLog.
    """
    __tablename__ = "raw_material_source"

    id      = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game.id", ondelete="CASCADE"),
                     nullable=False, index=True)

    name      = Column(String(150), nullable=False)
    component = Column(SAEnum(ComponentType), nullable=False)

    # Location descriptor (for display — not used in computation).
    location_description = Column(String(200), nullable=True)

    # Distance from factory in km — determines base transport cost.
    # transport_cost = distance_km * distance_cost_rate + base_cost_per_unit
    distance_km = Column(Float, nullable=False, default=500.0)

    # Per-unit cost before transport multiplier.
    # Total per-unit cost = base_cost_per_unit * transport_mode_multiplier
    base_cost_per_unit = Column(Float, nullable=False)

    # Quality distribution parameters (Normal distribution, grades 1–100).
    quality_mean  = Column(Float, nullable=False)   # Mean of the quality draw
    quality_sigma = Column(Float, nullable=False)   # Std deviation of the quality draw

    # Whether this source is currently available to teams.
    # Organiser can disable a source (e.g. after a catastrophic event).
    is_available = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    game       = relationship("Game", back_populates="sources")
    event_log  = relationship("SourceEventLog", back_populates="source",
                               cascade="all, delete-orphan",
                               order_by="SourceEventLog.created_at")


class SourceEventLog(Base):
    """
    Audit log of every organiser-triggered event that modifies a source's parameters.
    Examples: over-extraction (quality degrades), supply disruption (price rises),
    infrastructure investment (quality improves).

    The actual modification is applied directly to RawMaterialSource columns.
    This table records what changed and why, for transparency and debrief display.
    """
    __tablename__ = "source_event_log"

    id        = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("raw_material_source.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    cycle_id  = Column(Integer, ForeignKey("cycle.id", ondelete="SET NULL"),
                       nullable=True)

    event_name = Column(String(100), nullable=False)   # e.g. "over_extraction"
    description = Column(Text, nullable=True)          # Human-readable explanation

    # What changed (delta values for display — actual values already applied to source).
    quality_mean_delta  = Column(Float, nullable=True)
    quality_sigma_delta = Column(Float, nullable=True)
    cost_multiplier     = Column(Float, nullable=True)
    availability_change = Column(Boolean, nullable=True)  # True=enabled, False=disabled

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    source = relationship("RawMaterialSource", back_populates="event_log")


# ─────────────────────────────────────────────────────────────────────────────
# ProcurementDecision  (persistent — carries between cycles)
# ─────────────────────────────────────────────────────────────────────────────

class ProcurementDecision(Base):
    """
    A team's standing procurement decision for one component.

    This is the PERSISTENT state that carries between cycles.
    The server seeds one row per component per team with hardcoded defaults
    when the team is created. Teams PATCH this to change their decisions.
    At cycle resolution the server reads these rows and creates ProcurementOrders.

    One row per (team_id, component) — unique constraint enforced.
    """
    __tablename__ = "procurement_decision"
    __table_args__ = (
        UniqueConstraint("team_id", "component", name="uq_team_component"),
    )

    id        = Column(Integer, primary_key=True, index=True)
    team_id   = Column(Integer, ForeignKey("team.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    component = Column(SAEnum(ComponentType), nullable=False)

    # Which source the team is buying from this cycle.
    # Null means "not buying this component" (valid — some components optional).
    source_id     = Column(Integer, ForeignKey("raw_material_source.id"),
                           nullable=True)

    # How many units to order this cycle.
    quantity      = Column(Integer, nullable=False, default=0)

    # How the shipment is transported from the source.
    transport_mode = Column(SAEnum(TransportMode), nullable=False,
                            default=TransportMode.ROAD)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    team   = relationship("Team", back_populates="procurement_decisions")
    source = relationship("RawMaterialSource")


# ─────────────────────────────────────────────────────────────────────────────
# ProcurementOrder  (per-cycle — created fresh at resolution)
# ─────────────────────────────────────────────────────────────────────────────

class ProcurementOrder(Base):
    """
    A concrete procurement order for one component in one cycle.
    Created by the cycle resolver from the team's ProcurementDecision snapshot.
    Immutable after creation — it records what was ordered and what arrived.

    One row per (team_id, cycle_id, component).
    """
    __tablename__ = "procurement_order"
    __table_args__ = (
        UniqueConstraint("team_id", "cycle_id", "component",
                         name="uq_order_team_cycle_component"),
    )

    id        = Column(Integer, primary_key=True, index=True)
    team_id   = Column(Integer, ForeignKey("team.id",  ondelete="CASCADE"),
                       nullable=False, index=True)
    cycle_id  = Column(Integer, ForeignKey("cycle.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("raw_material_source.id"),
                       nullable=True)  # Null if team chose not to order this component

    component      = Column(SAEnum(ComponentType), nullable=False)
    transport_mode = Column(SAEnum(TransportMode), nullable=False)
    quantity_ordered = Column(Integer, nullable=False, default=0)

    # Deterministic cost — computed at order creation.
    # unit_cost = source.base_cost_per_unit * transport_multiplier
    unit_cost   = Column(Float, nullable=False, default=0.0)
    total_cost  = Column(Float, nullable=False, default=0.0)

    # Snapshot of source parameters at the time of the order
    # (source params may change next cycle due to events).
    source_quality_mean  = Column(Float, nullable=True)
    source_quality_sigma = Column(Float, nullable=True)

    # Shipment event that occurred in transit.
    shipment_event = Column(SAEnum(ShipmentEventType), nullable=False,
                            default=ShipmentEventType.NONE)

    # Whether a rival paid to sabotage this specific shipment.
    was_sabotaged       = Column(Boolean, nullable=False, default=False)
    sabotage_loss_fraction = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    team    = relationship("Team",  back_populates="procurement_orders")
    cycle   = relationship("Cycle", back_populates="orders")
    source  = relationship("RawMaterialSource")
    result  = relationship("ShipmentResult", back_populates="order",
                           uselist=False, cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# ShipmentResult  (the 101-integer quality array)
# ─────────────────────────────────────────────────────────────────────────────

class ShipmentResult(Base):
    """
    The resolved quality distribution of one procurement order.

    quality_array is a PostgreSQL ARRAY of 101 integers:
      index 0       → units that are unusable (damaged beyond use, lost, sabotaged)
      index 1–100   → count of units at each quality grade

    sum(quality_array[1:]) + quality_array[0] = quantity_ordered
    (all units are accounted for — either usable at some grade or in the loss bucket)

    This is the PRIMARY OUTPUT of the procurement system.
    The production system reads these arrays as its raw material input.
    """
    __tablename__ = "shipment_result"

    id       = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("procurement_order.id", ondelete="CASCADE"),
                      nullable=False, unique=True, index=True)

    # The 101-integer quality distribution array.
    # Stored as PostgreSQL integer array — fast to read, no JSON parsing.
    quality_array = Column(ARRAY(Integer), nullable=False)

    # Derived summary statistics (computed once, stored for quick display).
    total_usable  = Column(Integer, nullable=False, default=0)   # sum(quality_array[1:])
    total_lost    = Column(Integer, nullable=False, default=0)   # quality_array[0]
    weighted_mean = Column(Float,   nullable=True)               # mean grade of usable units
    min_grade     = Column(Integer, nullable=True)               # lowest grade with count > 0
    max_grade     = Column(Integer, nullable=True)               # highest grade with count > 0

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    order = relationship("ProcurementOrder", back_populates="result")
