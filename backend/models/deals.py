"""
models/deals.py
===============
Event   — every game event: single-cycle, flat, phase-tagged.
           Multi-cycle obligations (loans, R&D) are stored as
           multiple pre-generated rows, one per cycle.
GovDeal — backroom deal negotiation record with discovery lifecycle.
           Creating a GovDeal also generates the corresponding Event
           rows (done in services/deals.py).

Design principles:
  - Every Event is a single-cycle atomic unit. No cycles_remaining.
  - The cycle_id column says exactly which cycle this event fires in.
  - The phase column says which service resolves it.
  - Once resolved, status flips to APPLIED (soft delete for audit trail).
  - target_team_id is who is AFFECTED.
  - source_team_id is who CAUSED it (null for loans, global events).
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SAEnum,
    Float, ForeignKey, Integer, String, Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from core.database import Base
from core.enums import (
    EventPhase, EventStatus, EventType,
    GovDealStatus, GovDealType,
)


class Event(Base):
    """
    One game event targeting one team in one cycle.

    Queried by:
        (cycle_id, target_team_id, phase, status=PENDING)

    Each service calls this query at the start of its resolution,
    processes the matching events, and flips their status to APPLIED.

    For GLOBAL_MARKET_SHIFT events, target_team_id is NULL —
    the financial service queries these separately and applies
    them to the Game record.

    For LOAN_INTEREST events, source_team_id is the lender
    (null = government loan).

    payload structure is documented in EventType docstring (enums.py).
    """
    __tablename__ = "event"

    id      = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game.id", ondelete="CASCADE"),
                     nullable=False, index=True)

    # Which cycle this event fires in.
    cycle_id = Column(Integer, ForeignKey("cycle.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    # Who is affected. NULL only for GLOBAL_MARKET_SHIFT.
    target_team_id = Column(Integer, ForeignKey("team.id", ondelete="CASCADE"),
                             nullable=True, index=True)

    # Who caused it. NULL for loans, global events, team's own R&D.
    source_team_id = Column(Integer, ForeignKey("team.id", ondelete="CASCADE"),
                             nullable=True, index=True)

    # Which service resolves this.
    phase      = Column(SAEnum(EventPhase), nullable=False, index=True)

    # What this event does.
    event_type = Column(SAEnum(EventType),  nullable=False)

    # Effect parameters — structure depends on event_type (see enums.py).
    payload    = Column(JSONB, nullable=False, default=dict)

    # Lifecycle.
    status     = Column(SAEnum(EventStatus), nullable=False,
                         default=EventStatus.PENDING, index=True)

    # If this event was generated from a GovDeal, link back to it.
    # Null for loans, R&D investments, global events.
    gov_deal_id = Column(Integer, ForeignKey("gov_deal.id", ondelete="SET NULL"),
                          nullable=True, index=True)

    # Human-readable context for the organiser audit view.
    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    applied_at = Column(DateTime, nullable=True)


class GovDeal(Base):
    """
    One backroom deal negotiated offline between a team and the government.
    Recording a GovDeal immediately generates Event rows for the next cycle.

    Lifecycle:
      PENDING    → recorded, bribe deducted, Event rows generated
      APPLIED    → all generated Event rows have been consumed
      DISCOVERED → found out; fine applied to buyer, Events nullified
      CANCELLED  → organiser cancelled before application
    """
    __tablename__ = "gov_deal"

    id      = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game.id", ondelete="CASCADE"),
                     nullable=False, index=True)

    buyer_team_id  = Column(Integer, ForeignKey("team.id"), nullable=False,
                             index=True)
    target_team_id = Column(Integer, ForeignKey("team.id"), nullable=True,
                             index=True)
    # NULL for GREEN_* self-buff deals (buyer = target in that case)

    deal_type = Column(SAEnum(GovDealType), nullable=False)
    status    = Column(SAEnum(GovDealStatus), nullable=False,
                        default=GovDealStatus.PENDING)

    bribe_amount   = Column(Float, nullable=False)
    effect_scale   = Column(Float, nullable=False, default=1.0)

    # Snapshot of the computed effect payload (same as the Event rows it spawned).
    effect_payload = Column(JSONB, nullable=False, default=dict)

    discovery_probability = Column(Float, nullable=False)
    cycles_active         = Column(Integer, nullable=False, default=0)
    repeat_count          = Column(Integer, nullable=False, default=1)

    # Which cycle this deal was negotiated in.
    negotiated_cycle_id = Column(Integer, ForeignKey("cycle.id"),
                                  nullable=False, index=True)

    notes      = Column(Text,     nullable=True)
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())