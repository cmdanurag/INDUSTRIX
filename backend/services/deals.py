"""
services/deals.py
=================
Responsible ONLY for:
  1. Recording GovDeals (backroom negotiations).
  2. Generating Event rows from those deals.
  3. Creating Event rows for loans and global events.
  4. Rolling discovery at the end of the backroom phase.

Resolution of event effects lives in the service that owns each phase:
  - procurement events → services/procurement.py
  - production events  → services/production.py
  - sales events       → services/sales.py
  - financial events   → services/sales.py (end of sales resolution)

Public API
----------
record_gov_deal(db, game, cycle, buyer, target, deal_type, bribe, ...)
    Validate, deduct bribe, persist GovDeal, generate Event rows
    for the NEXT cycle.

create_loan_events(db, game, next_cycle_number, borrower_team_id,
                   lender_team_id, amount_per_cycle, num_cycles, notes)
    Pre-generate one LOAN_INTEREST Event per cycle.

create_global_event(db, game, next_cycle_number, payload, notes)
    Create a GLOBAL_MARKET_SHIFT Event for each affected cycle.

create_rnd_event(db, game, team, target_cycle_id, component, focus, levels)
    Called by production service when a team invests in R&D.

roll_discovery(db, cycle)
    Roll discovery for all PENDING GovDeals.
    Cancel the corresponding pending Event rows on discovery.
"""
import math
import random
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from core.config import (
    BRAND_DELTA_DEAL_FOUND, DEAL_BASE_DISCOVERY, DEAL_BRIBE_FLOOR,
    DEAL_DISCOVERY_DECAY, DEAL_EFFECT_CAP, DEAL_FINE_MULTIPLIER,
    DEAL_LOG_SCALE_DIVISOR, DEAL_REPEAT_STACK_RATE, DEAL_SIZE_DISCOVERY_RATE,
    GOV_LOAN_INTEREST_RATE, BRAND_DELTA_GOV_LOAN,
)
from core.enums import (
    EventPhase, EventStatus, EventType,
    GovDealStatus, GovDealType,
)
from models.deals import Event, GovDeal
from models.game import Cycle
from models.procurement import Inventory


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _effect_scale(bribe: float, floor: float) -> float:
    if floor <= 0 or bribe <= floor:
        return 1.0
    return min(DEAL_EFFECT_CAP,
               1.0 + math.log(bribe / floor) / DEAL_LOG_SCALE_DIVISOR)


def _discovery_prob(deal_type: str, bribe: float, floor: float,
                    repeat: int) -> float:
    base      = DEAL_BASE_DISCOVERY.get(deal_type, 0.10)
    size_add  = (math.log(bribe / floor) * DEAL_SIZE_DISCOVERY_RATE
                 if floor > 0 and bribe > floor else 0.0)
    stack_add = (repeat - 1) * DEAL_REPEAT_STACK_RATE
    return min(1.0, max(0.0, base + size_add + stack_add))


def _next_cycle(db: Session, game_id: int, current_cycle: Cycle) -> Optional[Cycle]:
    """Return the cycle immediately after current_cycle, if it exists."""
    return (
        db.query(Cycle)
        .filter(
            Cycle.game_id      == game_id,
            Cycle.cycle_number == current_cycle.cycle_number + 1,
        )
        .first()
    )


def _make_event(
    db:             Session,
    game_id:        int,
    cycle_id:       int,
    phase:          EventPhase,
    event_type:     EventType,
    payload:        Dict,
    target_team_id: Optional[int] = None,
    source_team_id: Optional[int] = None,
    gov_deal_id:    Optional[int] = None,
    notes:          Optional[str] = None,
) -> Event:
    ev = Event(
        game_id        = game_id,
        cycle_id       = cycle_id,
        target_team_id = target_team_id,
        source_team_id = source_team_id,
        phase          = phase,
        event_type     = event_type,
        payload        = payload,
        status         = EventStatus.PENDING,
        gov_deal_id    = gov_deal_id,
        notes          = notes,
    )
    db.add(ev)
    return ev


# ─────────────────────────────────────────────────────────────────────────────
# Deal type → (EventPhase, EventType, payload builder)
# ─────────────────────────────────────────────────────────────────────────────

def _deal_to_events(
    deal_type:      str,
    scale:          float,
    override:       Optional[Dict],
    buyer_team_id:  int,
    target_team_id: Optional[int],
) -> List[Dict]:
    """
    Map a GovDealType to one or more (phase, event_type, payload,
    target_team_id) tuples. Returns a list of dicts ready to be
    passed to _make_event.

    For self-buff (GREEN_*) deals, target = buyer.
    For offensive (RED_*) deals, target = the rival.
    """
    # Defensive: self-buff target is the buyer
    self_id   = buyer_team_id
    rival_id  = target_team_id  # may be None for GREEN deals

    def p(d): return {**d, **(override or {})}

    mapping = {
        # ── Procurement ───────────────────────────────────────────────────────
        "red_supply_sabotage": [(
            EventPhase.PROCUREMENT, EventType.SUPPLY_SABOTAGE,
            p({"loss_fraction": min(0.90, 0.25 * scale)}), rival_id,
        )],
        "red_price_inflation": [(
            EventPhase.PROCUREMENT, EventType.PRICE_INFLATION,
            p({"cost_multiplier": 1.0 + 0.30 * scale}), rival_id,
        )],
        "green_priority_supply": [(
            EventPhase.PROCUREMENT, EventType.PRIORITY_SUPPLY,
            p({"mean_bonus": 5.0 * scale}), self_id,
        )],
        "green_subsidised_inputs": [(
            EventPhase.PROCUREMENT, EventType.SUBSIDISED_INPUTS,
            p({"cost_multiplier": max(0.50, 1.0 - 0.20 * scale)}), self_id,
        )],

        # ── Production ────────────────────────────────────────────────────────
        "red_machine_sabotage": [(
            EventPhase.PRODUCTION, EventType.MACHINE_SABOTAGE,
            p({"condition_hit": min(90.0, 30.0 * scale)}), rival_id,
        )],
        "red_infra_delay": [(
            EventPhase.PRODUCTION, EventType.INFRA_DELAY,
            p({}), rival_id,
        )],
        "green_fast_track_infra": [(
            EventPhase.PRODUCTION, EventType.FAST_TRACK_INFRA,
            p({"condition_bonus": 10.0 * scale, "quality_bonus": 5.0 * scale}),
            self_id,
        )],
        "red_labour_strike": [(
            EventPhase.PRODUCTION, EventType.LABOUR_STRIKE, p({}), rival_id,
        )],
        "red_labour_poach": [(
            EventPhase.PRODUCTION, EventType.LABOUR_POACH,
            p({"skill_hit": min(40.0, 12.0 * scale)}), rival_id,
        )],
        "red_rnd_sabotage": [(
            EventPhase.PRODUCTION, EventType.RND_SABOTAGE,
            p({"levels_stolen": 1 if scale < 1.5 else 2}), rival_id,
        )],
        "green_skilled_labour": [(
            EventPhase.PRODUCTION, EventType.SKILLED_LABOUR,
            p({"skill_bonus": min(30.0, 8.0 * scale)}), self_id,
        )],
        # green_research_grant → generates an RND_INVESTMENT event
        # (arrives immediately — 0-cycle delay for a grant)
        "green_research_grant": [(
            EventPhase.PRODUCTION, EventType.RND_INVESTMENT,
            p({"level_arriving": 1,
               "bonus_prob": max(0.0, (scale - 1.0) / (DEAL_EFFECT_CAP - 1.0))}),
            self_id,
        )],

        # ── Sales ─────────────────────────────────────────────────────────────
        "red_market_limit": [(
            EventPhase.SALES, EventType.MARKET_LIMIT,
            p({"block_fraction": min(0.80, 0.30 * scale)}), rival_id,
        )],
        "red_demand_suppression": [(
            EventPhase.SALES, EventType.DEMAND_SUPPRESSION,
            p({"demand_multiplier": max(0.25, 1.0 - 0.35 * scale)}), rival_id,
        )],
        "red_price_pressure": [(
            EventPhase.SALES, EventType.PRICE_PRESSURE, p({}), rival_id,
        )],
        "green_demand_boost": [(
            EventPhase.SALES, EventType.DEMAND_BOOST,
            p({"demand_multiplier": 1.0 + 0.35 * scale}), self_id,
        )],
        "green_gov_purchase": [(
            EventPhase.SALES, EventType.GOV_PURCHASE,
            p({"units": 0, "price_per_unit": 2_800.0}), self_id,
        )],
        "green_quality_waiver": [(
            EventPhase.SALES, EventType.QUALITY_WAIVER,
            p({"threshold_reduction": min(20.0, 5.0 * scale)}), self_id,
        )],
        "green_audit_immunity": [(
            EventPhase.SALES, EventType.AUDIT_IMMUNITY, p({}), self_id,
        )],

        # ── Financial ─────────────────────────────────────────────────────────
        "red_targeted_audit": [],   # handled by organiser offline; no Event
        "red_arbitrary_fine": [(
            EventPhase.FINANCIAL, EventType.ARBITRARY_FINE,
            p({"fine_amount": 5_000.0 * scale}), rival_id,
        )],
        "green_tax_evasion": [(
            EventPhase.FINANCIAL, EventType.TAX_EVASION_REFUND,
            p({"refund_fraction": min(0.25, 0.08 * scale)}), self_id,
        )],
    }

    return [
        {"phase": ph, "event_type": et, "payload": pl, "target_team_id": tgt}
        for ph, et, pl, tgt in mapping.get(deal_type, [])
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Record a government deal
# ─────────────────────────────────────────────────────────────────────────────

def record_gov_deal(
    db:              Session,
    game,
    cycle,
    buyer_team,
    deal_type:       GovDealType,
    bribe_amount:    float,
    target_team=None,
    override_params: Optional[Dict] = None,
    notes:           Optional[str]  = None,
) -> GovDeal:
    """
    Validate and record a backroom deal.
    Deducts bribe immediately.
    Generates Event rows for the NEXT cycle.
    """
    inv: Inventory = (
        db.query(Inventory)
        .filter(Inventory.team_id == buyer_team.id)
        .first()
    )
    if inv is None:
        raise ValueError("Buyer team has no inventory.")
    if inv.has_gov_loan:
        raise ValueError(
            f"Team '{buyer_team.name}' has an active gov loan — "
            "backroom deals are blocked."
        )

    floor = DEAL_BRIBE_FLOOR.get(deal_type.value, 0.0)
    if bribe_amount < floor:
        raise ValueError(
            f"Bribe {bribe_amount} is below the floor {floor} "
            f"for '{deal_type.value}'."
        )
    if inv.funds < bribe_amount:
        raise ValueError(
            f"Insufficient funds ({inv.funds:.0f}) "
            f"for bribe {bribe_amount:.0f}."
        )

    is_offensive = deal_type.value.startswith("red_")
    if is_offensive and target_team is None:
        raise ValueError(f"'{deal_type.value}' requires a target team.")
    if not is_offensive and target_team is not None:
        raise ValueError(f"'{deal_type.value}' is a self-buff — no target needed.")
    if target_team and target_team.id == buyer_team.id:
        raise ValueError("Cannot target yourself.")

    scale  = _effect_scale(bribe_amount, floor)
    repeat = (
        db.query(GovDeal)
        .filter(
            GovDeal.negotiated_cycle_id == cycle.id,
            GovDeal.buyer_team_id       == buyer_team.id,
            GovDeal.deal_type           == deal_type,
            GovDeal.status.in_([GovDealStatus.PENDING, GovDealStatus.APPLIED]),
        )
        .count()
    ) + 1

    disc_prob = _discovery_prob(
        deal_type.value, bribe_amount, floor, repeat
    )

    # Build effect snapshot for the GovDeal record
    event_specs = _deal_to_events(
        deal_type.value, scale, override_params,
        buyer_team.id,
        target_team.id if target_team else None,
    )
    effect_payload = event_specs[0]["payload"] if event_specs else {}

    inv.funds -= bribe_amount

    deal = GovDeal(
        game_id               = game.id,
        buyer_team_id         = buyer_team.id,
        target_team_id        = target_team.id if target_team else None,
        deal_type             = deal_type,
        status                = GovDealStatus.PENDING,
        bribe_amount          = bribe_amount,
        effect_scale          = scale,
        effect_payload        = effect_payload,
        discovery_probability = disc_prob,
        cycles_active         = 0,
        repeat_count          = repeat,
        negotiated_cycle_id   = cycle.id,
        notes                 = notes,
    )
    db.add(deal)
    db.flush()   # get deal.id before creating Event rows

    # Find the next cycle to attach events to
    next_cyc = _next_cycle(db, game.id, cycle)
    if next_cyc is None:
        # Backroom is being run before next cycle exists — events will be
        # created when the next cycle is opened via create_events_for_deal()
        pass
    else:
        _create_event_rows_for_deal(db, game, next_cyc, deal, event_specs,
                                     buyer_team.id)

    return deal


def _create_event_rows_for_deal(
    db:            Session,
    game,
    target_cycle:  Cycle,
    deal:          GovDeal,
    event_specs:   List[Dict],
    buyer_team_id: int,
) -> None:
    """Generate Event rows for a deal into the given cycle."""
    for spec in event_specs:
        _make_event(
            db             = db,
            game_id        = game.id,
            cycle_id       = target_cycle.id,
            phase          = spec["phase"],
            event_type     = spec["event_type"],
            payload        = spec["payload"],
            target_team_id = spec["target_team_id"],
            source_team_id = buyer_team_id,
            gov_deal_id    = deal.id,
            notes          = deal.notes,
        )


def create_events_for_pending_deals(
    db: Session, game, new_cycle: Cycle
) -> int:
    """
    Called when a new cycle is created.
    Finds all GovDeals that are PENDING and have no Event rows yet
    (because the next cycle didn't exist when they were recorded),
    and creates their Event rows now.
    """
    pending_deals: List[GovDeal] = (
        db.query(GovDeal)
        .filter(
            GovDeal.game_id == game.id,
            GovDeal.status  == GovDealStatus.PENDING,
        )
        .all()
    )

    count = 0
    for deal in pending_deals:
        # Check if Event rows already exist for this deal
        existing = (
            db.query(Event)
            .filter(Event.gov_deal_id == deal.id)
            .count()
        )
        if existing > 0:
            continue

        event_specs = _deal_to_events(
            deal.deal_type.value,
            deal.effect_scale,
            None,
            deal.buyer_team_id,
            deal.target_team_id,
        )
        _create_event_rows_for_deal(db, game, new_cycle, deal, event_specs,
                                     deal.buyer_team_id)
        count += 1

    db.flush()
    return count


# ─────────────────────────────────────────────────────────────────────────────
# Loan events
# ─────────────────────────────────────────────────────────────────────────────

def create_loan_events(
    db:               Session,
    game,
    db_cycles:        List[Cycle],   # the cycles this loan covers, in order
    borrower_team_id: int,
    lender_team_id:   Optional[int],  # None = government
    amount_per_cycle: float,
    notes:            Optional[str] = None,
) -> List[Event]:
    """
    Pre-generate one LOAN_INTEREST Event per cycle.
    db_cycles must be the actual Cycle ORM objects for the cycles
    during which interest is due.
    """
    events = []
    for cyc in db_cycles:
        ev = _make_event(
            db             = db,
            game_id        = game.id,
            cycle_id       = cyc.id,
            phase          = EventPhase.FINANCIAL,
            event_type     = EventType.LOAN_INTEREST,
            payload        = {
                "amount":          round(amount_per_cycle, 2),
                "lender_team_id":  lender_team_id,
            },
            target_team_id = borrower_team_id,
            source_team_id = lender_team_id,
            notes          = notes,
        )
        events.append(ev)
    db.flush()
    return events


# ─────────────────────────────────────────────────────────────────────────────
# Global market shift events
# ─────────────────────────────────────────────────────────────────────────────

def create_global_event(
    db:             Session,
    game,
    db_cycles:      List[Cycle],
    payload:        Dict,
    notes:          Optional[str] = None,
) -> List[Event]:
    """
    Create a GLOBAL_MARKET_SHIFT Event for each cycle in db_cycles.
    target_team_id is NULL — the financial service applies this to
    the Game record, not to any specific team.
    """
    events = []
    for cyc in db_cycles:
        ev = _make_event(
            db             = db,
            game_id        = game.id,
            cycle_id       = cyc.id,
            phase          = EventPhase.FINANCIAL,
            event_type     = EventType.GLOBAL_MARKET_SHIFT,
            payload        = payload,
            target_team_id = None,
            source_team_id = None,
            notes          = notes,
        )
        events.append(ev)
    db.flush()
    return events


# ─────────────────────────────────────────────────────────────────────────────
# R&D investment events (called by production service)
# ─────────────────────────────────────────────────────────────────────────────

def create_rnd_event(
    db:        Session,
    game,
    team,
    target_cycle: Cycle,   # the cycle in which R&D arrives
    component: str,
    focus:     str,
    levels:    int,
    cost:      float,
) -> Event:
    """
    Create an RND_INVESTMENT event targeting the cycle when research matures.
    Cost is deducted by the caller before calling this.
    """
    ev = _make_event(
        db             = db,
        game_id        = game.id,
        cycle_id       = target_cycle.id,
        phase          = EventPhase.PRODUCTION,
        event_type     = EventType.RND_INVESTMENT,
        payload        = {
            "component":     component,
            "focus":         focus,
            "level_arriving": levels,
        },
        target_team_id = team.id,
        source_team_id = None,
        notes          = f"R&D: {component} {focus} +{levels} (cost {cost:.0f} CU)",
    )
    db.flush()
    return ev


# ─────────────────────────────────────────────────────────────────────────────
# Discovery roll
# ─────────────────────────────────────────────────────────────────────────────

def roll_discovery(db: Session, cycle) -> Dict:
    """
    Roll discovery for all PENDING GovDeals.
    Called when the organiser closes the backroom phase (/next or /end-game).

    On discovery:
      - GovDeal status → DISCOVERED
      - Fine deducted from buyer's funds
      - Brand hit applied
      - All PENDING Event rows generated from this deal → APPLIED
        (they are cancelled, not executed — nullifying the effect)
    """
    pending: List[GovDeal] = (
        db.query(GovDeal)
        .filter(GovDeal.status == GovDealStatus.PENDING)
        .all()
    )

    discovered_count = 0
    safe_count       = 0

    for deal in pending:
        deal.cycles_active += 1
        effective_p = deal.discovery_probability * (
            DEAL_DISCOVERY_DECAY ** deal.cycles_active
        )
        effective_p = min(1.0, max(0.0, effective_p))

        if random.random() < effective_p:
            # Discovered — cancel effect, apply fine
            fine = round(deal.bribe_amount * DEAL_FINE_MULTIPLIER, 2)
            inv  = (
                db.query(Inventory)
                .filter(Inventory.team_id == deal.buyer_team_id)
                .first()
            )
            if inv:
                inv.funds      -= fine
                inv.brand_score = max(0.0, inv.brand_score + BRAND_DELTA_DEAL_FOUND)

            # Cancel all pending Event rows for this deal
            (
                db.query(Event)
                .filter(
                    Event.gov_deal_id == deal.id,
                    Event.status      == EventStatus.PENDING,
                )
                .update(
                    {"status": EventStatus.APPLIED,
                     "applied_at": datetime.utcnow()},
                    synchronize_session=False,
                )
            )

            deal.status = GovDealStatus.DISCOVERED
            discovered_count += 1
        else:
            safe_count += 1

    db.flush()
    return {
        "discovered": discovered_count,
        "safe":       safe_count,
    }

