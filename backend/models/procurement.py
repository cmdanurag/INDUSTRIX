"""
models/procurement.py
=====================
Inventory         — persistent company-level financial and labour state.
ComponentSlot     — per-component material and R&D state (six rows per team).
Machine           — one physical machine (N per component per team, no cap).
MemoryProcurement — last cycle's procurement decisions (one row per team).

Key design change: machine state has moved out of ComponentSlot into a
dedicated Machine table. Teams can own any number of machines per component.
ComponentSlot now holds only stock arrays and R&D levels.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SAEnum,
    Float, ForeignKey, Integer, String, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship

from core.database import Base
from core.enums import AutomationLevel, BrandTier, ComponentType


class Inventory(Base):
    """
    The company's persistent financial and physical top-level state.
    Updated in place at the end of every cycle.

    drone_stock: int[101] — index 0 = scrap, 1-100 = grade counts.
    Unsold drones carry between cycles.
    """
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("team_id", name="uq_inventory_team"),
    )

    id      = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("team.id", ondelete="CASCADE"),
                     nullable=False, unique=True, index=True)

    funds       = Column(Float,        nullable=False, default=100_000.0)
    drone_stock = Column(ARRAY(Integer), nullable=False,
                          default=lambda: [0] * 101)

    brand_score = Column(Float,           nullable=False, default=50.0)
    brand_tier  = Column(SAEnum(BrandTier), nullable=False,
                          default=BrandTier.FAIR)

    # Labour state — persistent across cycles.
    workforce_size   = Column(Integer,            nullable=False, default=50)
    skill_level      = Column(Float,              nullable=False, default=40.0)
    morale           = Column(Float,              nullable=False, default=60.0)
    automation_level = Column(SAEnum(AutomationLevel), nullable=False,
                               default=AutomationLevel.MANUAL)

    # Running total for leaderboard composite score.
    cumulative_profit = Column(Float, nullable=False, default=0.0)

    # True while any government loan is outstanding.
    # Blocks backroom deals while active.
    has_gov_loan = Column(Boolean, nullable=False, default=False)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    team = relationship("Team", back_populates="inventory")


class ComponentSlot(Base):
    """
    Per-component material and R&D state for one team.
    Six rows per team, one per ComponentType.

    Machine state has been extracted to the Machine table.
    This table now holds only stock arrays and R&D levels.

    raw_stock      : int[101] — unconsumed raw materials.
    finished_stock : int[101] — manufactured components not yet assembled
                                into drones. Carries between cycles.
    """
    __tablename__ = "component_slot"
    __table_args__ = (
        UniqueConstraint("team_id", "component", name="uq_slot_team_component"),
    )

    id        = Column(Integer, primary_key=True, index=True)
    team_id   = Column(Integer, ForeignKey("team.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    component = Column(SAEnum(ComponentType), nullable=False)

    # Stock arrays
    raw_stock      = Column(ARRAY(Integer), nullable=False,
                             default=lambda: [0] * 101)
    finished_stock = Column(ARRAY(Integer), nullable=False,
                             default=lambda: [0] * 101)

    # R&D levels (0–MAX_RND_LEVEL each)
    rnd_quality     = Column(Integer, nullable=False, default=0)
    rnd_consistency = Column(Integer, nullable=False, default=0)
    rnd_yield       = Column(Integer, nullable=False, default=0)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    team     = relationship("Team",    back_populates="component_slots")
    machines = relationship("Machine", back_populates="slot",
                             cascade="all, delete-orphan",
                             foreign_keys="Machine.slot_id")


class Machine(Base):
    """
    One physical machine owned by a team for one component.
    Teams can own any number of machines per component — limited only by funds.

    Throughput for a component = sum of throughput of all ACTIVE machines
    for that component.

    Maintenance is applied uniformly to all machines of a component
    (one maintenance decision per component covers all its machines).

    is_active: False means the machine has been destroyed (condition hit 0)
               or scrapped by the organiser. Kept for audit trail.

    purchased_cycle: cycle number when this machine was bought.
                     Used for fast-track infra event targeting.

    source: "bought" (team purchased), "auction" (won at auction),
            "grant" (organiser transferred directly).
    """
    __tablename__ = "machine"

    id        = Column(Integer, primary_key=True, index=True)
    team_id   = Column(Integer, ForeignKey("team.id",           ondelete="CASCADE"),
                       nullable=False, index=True)
    slot_id   = Column(Integer, ForeignKey("component_slot.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    component = Column(SAEnum(ComponentType), nullable=False)

    # Machine tier determines base output grade and throughput.
    # Stored as a plain string so we can add tiers without schema migrations.
    tier      = Column(String(20), nullable=False, default="standard")

    # 0.0–100.0. Degrades each cycle per tier config. At 0 the machine is destroyed.
    condition = Column(Float, nullable=False, default=100.0)

    is_active       = Column(Boolean, nullable=False, default=True)
    purchased_cycle = Column(Integer, nullable=True)   # cycle_number, not cycle.id

    # "bought" | "auction" | "grant" | "seed"
    source = Column(String(20), nullable=False, default="bought")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    slot = relationship("ComponentSlot", back_populates="machines",
                         foreign_keys=[slot_id])


class MemoryProcurement(Base):
    """
    Last cycle's procurement decisions for one team.
    PATCH semantics — only changed fields are sent; rest carry forward.

    decisions: {
        "airframe": {
            "source_id": 3,
            "quantity":  500,
            "transport": "rail"
        },
        ... (one entry per component)
    }
    """
    __tablename__ = "memory_procurement"
    __table_args__ = (
        UniqueConstraint("team_id", name="uq_mem_proc_team"),
    )

    id      = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("team.id", ondelete="CASCADE"),
                     nullable=False, unique=True, index=True)

    decisions  = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    team = relationship("Team", back_populates="memory_procurement")
