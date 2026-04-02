"""
routers/organiser/deals.py
==========================
All backroom deal and event endpoints. Only accessible during BACKROOM phase
(except /events which is a read-only audit view available any time).

POST /organiser/deals/gov              Record a government deal
POST /organiser/deals/inter-team       Record an inter-team loan
POST /organiser/deals/gov-loan         Issue a government loan
POST /organiser/deals/global-event     Record a global market event
GET  /organiser/deals                  List GovDeals for current cycle
GET  /organiser/deals/{deal_id}        Get one GovDeal with its Event rows
DELETE /organiser/deals/{deal_id}      Cancel a PENDING GovDeal
POST /organiser/deals/discover         Manually trigger discovery roll
GET  /organiser/events                 List all Event rows for current cycle
                                       (organiser audit view — shows what will
                                        fire in each phase this cycle)
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.auth import verify_organiser
from core.config import BRAND_DELTA_GOV_LOAN, GOV_LOAN_INTEREST_RATE
from core.database import get_db
from core.enums import (
    CyclePhase, EventPhase, EventStatus, EventType, GovDealStatus,
)
from models.deals import Event, GovDeal
from models.game import Cycle, Game, Team
from models.procurement import Inventory
from schemas.common import OkResponse
from schemas.deals import (
    AdvancePhaseOut, EventOut, GlobalEventCreate,
    GovDealCreate, GovDealOut, GovLoanCreate,
    InterTeamLoanCreate, LoanCreatedOut,
)
from services.deals import (
    create_global_event, create_loan_events,
    record_gov_deal, roll_discovery,
)

router = APIRouter(prefix="/organiser/deals", tags=["organiser"])


# ── Guards ────────────────────────────────────────────────────────────────────

def _assert_backroom(game: Game, db: Session) -> Cycle:
    cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    if not cycle or cycle.phase_log.current_phase != CyclePhase.BACKROOM:
        raise HTTPException(
            400,
            "This endpoint is only accessible during the BACKROOM phase. "
            f"Current phase: "
            f"{cycle.phase_log.current_phase.value if cycle and cycle.phase_log else 'none'}",
        )
    return cycle


def _get_team(team_id: int, game_id: int, db: Session) -> Team:
    team = db.query(Team).filter(
        Team.id == team_id, Team.game_id == game_id
    ).first()
    if not team:
        raise HTTPException(404, f"Team {team_id} not found in this game.")
    return team


def _get_future_cycles(
    db: Session, game_id: int, from_cycle_number: int, count: int
) -> List[Cycle]:
    """
    Return `count` cycles starting from from_cycle_number + 1.
    Only returns cycles that already exist. If fewer than `count` exist,
    returns what is available.
    """
    return (
        db.query(Cycle)
        .filter(
            Cycle.game_id      == game_id,
            Cycle.cycle_number >  from_cycle_number,
            Cycle.cycle_number <= from_cycle_number + count,
        )
        .order_by(Cycle.cycle_number)
        .all()
    )


# ── Government deal ───────────────────────────────────────────────────────────

@router.post("/gov", response_model=GovDealOut, status_code=201,
             summary="Record a government deal negotiated offline.")
def create_gov_deal(
    body: GovDealCreate,
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Record a backroom deal. The bribe is deducted from the buyer's funds
    immediately. Event rows for the next cycle are generated automatically.

    For RED_* offensive deals, target_team_id is required.
    For GREEN_* self-buff deals, target_team_id must be omitted.

    Use override_params to set deal-specific parameters the server cannot
    infer — e.g. for green_gov_purchase, set {"units": 100, "price_per_unit": 2800}.
    """
    cycle  = _assert_backroom(game, db)
    buyer  = _get_team(body.buyer_team_id, game.id, db)
    target = _get_team(body.target_team_id, game.id, db) \
             if body.target_team_id else None

    try:
        deal = record_gov_deal(
            db              = db,
            game            = game,
            cycle           = cycle,
            buyer_team      = buyer,
            deal_type       = body.deal_type,
            bribe_amount    = body.bribe_amount,
            target_team     = target,
            override_params = body.override_params,
            notes           = body.notes,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    db.commit()
    return deal


# ── Inter-team loan ───────────────────────────────────────────────────────────

@router.post("/inter-team", response_model=LoanCreatedOut, status_code=201,
             summary="Record an inter-team loan negotiated offline.")
def create_inter_team_loan(
    body: InterTeamLoanCreate,
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Transfer principal from lender to borrower immediately.
    Pre-generate one LOAN_INTEREST Event per cycle for the duration.

    Interest per cycle = principal × interest_rate.
    Events are created for cycles that already exist. If the game runs
    longer than the duration, no additional events are created automatically
    — the organiser must record a new loan if they want to extend.

    Note: If future cycles do not exist yet (game hasn't advanced that far),
    only events for existing cycles are created. The remainder will be created
    when those cycles are opened via create_events_for_pending_deals.
    """
    _assert_backroom(game, db)
    borrower = _get_team(body.borrower_team_id, game.id, db)
    lender   = _get_team(body.lender_team_id,   game.id, db)

    lender_inv = (
        db.query(Inventory).filter(Inventory.team_id == lender.id).first()
    )
    if lender_inv and lender_inv.funds < body.principal:
        raise HTTPException(400, "Lender has insufficient funds.")

    # Transfer principal immediately
    if lender_inv:
        lender_inv.funds -= body.principal
    borrower_inv = (
        db.query(Inventory).filter(Inventory.team_id == borrower.id).first()
    )
    if borrower_inv:
        borrower_inv.funds += body.principal

    # Find current cycle to know where to start interest events
    current_cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )

    amount_per_cycle = round(body.principal * body.interest_rate, 2)
    target_cycles    = _get_future_cycles(
        db, game.id, current_cycle.cycle_number, body.duration_cycles
    )

    events = create_loan_events(
        db               = db,
        game             = game,
        db_cycles        = target_cycles,
        borrower_team_id = borrower.id,
        lender_team_id   = lender.id,
        amount_per_cycle = amount_per_cycle,
        notes            = body.notes,
    )

    db.commit()

    return LoanCreatedOut(
        events_created    = len(events),
        borrower_team_id  = borrower.id,
        lender_team_id    = lender.id,
        principal         = body.principal,
        interest_rate     = body.interest_rate,
        amount_per_cycle  = amount_per_cycle,
        duration_cycles   = body.duration_cycles,
        total_interest    = round(amount_per_cycle * body.duration_cycles, 2),
    )


# ── Government loan ───────────────────────────────────────────────────────────

@router.post("/gov-loan", response_model=LoanCreatedOut, status_code=201,
             summary="Issue a government loan to a struggling team.")
def create_gov_loan(
    body: GovLoanCreate,
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Credit principal to borrower immediately.
    Interest rate is fixed at GOV_LOAN_INTEREST_RATE (15% per cycle).
    While the loan is active, the team cannot make backroom deals and
    their brand score takes a hit.

    One LOAN_INTEREST Event is generated per cycle for the duration.
    """
    _assert_backroom(game, db)
    borrower = _get_team(body.borrower_team_id, game.id, db)

    inv = db.query(Inventory).filter(Inventory.team_id == borrower.id).first()
    if inv:
        inv.funds        += body.principal
        inv.has_gov_loan  = True
        inv.brand_score   = max(0.0, inv.brand_score + BRAND_DELTA_GOV_LOAN)

    current_cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )

    amount_per_cycle = round(body.principal * GOV_LOAN_INTEREST_RATE, 2)
    target_cycles    = _get_future_cycles(
        db, game.id, current_cycle.cycle_number, body.duration_cycles
    )

    events = create_loan_events(
        db               = db,
        game             = game,
        db_cycles        = target_cycles,
        borrower_team_id = borrower.id,
        lender_team_id   = None,            # None = government
        amount_per_cycle = amount_per_cycle,
        notes            = body.notes or f"Gov loan: {body.principal:.0f} CU",
    )

    db.commit()

    return LoanCreatedOut(
        events_created    = len(events),
        borrower_team_id  = borrower.id,
        lender_team_id    = None,
        principal         = body.principal,
        interest_rate     = GOV_LOAN_INTEREST_RATE,
        amount_per_cycle  = amount_per_cycle,
        duration_cycles   = body.duration_cycles,
        total_interest    = round(amount_per_cycle * body.duration_cycles, 2),
    )


# ── Global event ──────────────────────────────────────────────────────────────

@router.post("/global-event", response_model=List[EventOut], status_code=201,
             summary="Record a global market event affecting all teams.")
def create_global_event_endpoint(
    body: GlobalEventCreate,
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Create a GLOBAL_MARKET_SHIFT Event for each affected cycle.
    One Event row per cycle is pre-generated.

    The organiser informs teams verbally during the backroom phase.
    Effects fire automatically at the financial phase of each covered cycle.

    payload example:
        {"market_demand_multiplier_delta": -0.2}   # market shrinks 20% for N cycles
        {"qr_hard_delta": 5, "qr_soft_delta": 3}   # quality thresholds raised
    """
    _assert_backroom(game, db)

    current_cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    target_cycles = _get_future_cycles(
        db, game.id, current_cycle.cycle_number, body.duration_cycles
    )

    if not target_cycles:
        raise HTTPException(
            400,
            "No future cycles exist yet. Create the next cycle first, "
            "or use /organiser/cycle/next to advance.",
        )

    events = create_global_event(
        db          = db,
        game        = game,
        db_cycles   = target_cycles,
        payload     = body.payload,
        notes       = body.notes,
    )

    db.commit()
    return events


# ── List GovDeals for current cycle ──────────────────────────────────────────

@router.get("", response_model=List[GovDealOut],
            summary="List all government deals negotiated in the current cycle.")
def list_deals(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    if not cycle:
        return []
    return (
        db.query(GovDeal)
        .filter(GovDeal.negotiated_cycle_id == cycle.id)
        .order_by(GovDeal.id)
        .all()
    )


# ── Get one GovDeal ───────────────────────────────────────────────────────────

@router.get("/{deal_id}", response_model=GovDealOut,
            summary="Get one GovDeal.")
def get_deal(
    deal_id: int,
    game:    Game    = Depends(verify_organiser),
    db:      Session = Depends(get_db),
):
    deal = db.query(GovDeal).filter(
        GovDeal.id == deal_id, GovDeal.game_id == game.id
    ).first()
    if not deal:
        raise HTTPException(404, "Deal not found.")
    return deal


# ── Cancel a GovDeal ─────────────────────────────────────────────────────────

@router.delete("/{deal_id}", response_model=OkResponse,
               summary="Cancel a PENDING GovDeal. No refund issued.")
def cancel_deal(
    deal_id: int,
    game:    Game    = Depends(verify_organiser),
    db:      Session = Depends(get_db),
):
    """
    Cancels the GovDeal record and marks all its PENDING Event rows as APPLIED
    (cancellation). The bribe already paid is not refunded.
    """
    deal = db.query(GovDeal).filter(
        GovDeal.id == deal_id, GovDeal.game_id == game.id
    ).first()
    if not deal:
        raise HTTPException(404, "Deal not found.")
    if deal.status != GovDealStatus.PENDING:
        raise HTTPException(
            400,
            f"Cannot cancel a deal with status '{deal.status.value}'. "
            "Only PENDING deals can be cancelled.",
        )

    # Cancel pending Event rows
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

    deal.status = GovDealStatus.CANCELLED
    db.commit()
    return OkResponse(message=f"Deal {deal_id} cancelled. Event rows nullified.")


# ── Manual discovery roll ─────────────────────────────────────────────────────

@router.post("/discover", response_model=Dict,
             summary="Manually trigger discovery rolls for all PENDING deals.")
def trigger_discovery(
    game: Game    = Depends(verify_organiser),
    db:   Session = Depends(get_db),
):
    """
    Normally discovery is rolled automatically when /next or /end-game is
    called. Use this endpoint to roll early (e.g. for dramatic effect mid
    backroom phase).
    """
    cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    if not cycle:
        raise HTTPException(404, "No cycle found.")

    result = roll_discovery(db, cycle)
    db.commit()
    return result


# ── Event audit view ──────────────────────────────────────────────────────────

@router.get("/events/current", response_model=List[EventOut],
            summary="List all Event rows for the current cycle (organiser audit).")
def list_current_events(
    phase:   Optional[str] = Query(None,
        description="Filter by phase: procurement, production, sales, financial"),
    status:  Optional[str] = Query(None,
        description="Filter by status: pending, applied"),
    team_id: Optional[int] = Query(None,
        description="Filter by target team ID"),
    game:    Game    = Depends(verify_organiser),
    db:      Session = Depends(get_db),
):
    """
    Shows exactly what events will fire (or have fired) in the current cycle,
    grouped by phase. Useful for the organiser to verify deal effects before
    advancing.
    """
    cycle = (
        db.query(Cycle)
        .filter(Cycle.game_id == game.id)
        .order_by(Cycle.cycle_number.desc())
        .first()
    )
    if not cycle:
        return []

    q = db.query(Event).filter(Event.cycle_id == cycle.id)

    if phase:
        try:
            q = q.filter(Event.phase == EventPhase(phase))
        except ValueError:
            raise HTTPException(400, f"Unknown phase '{phase}'. "
                                "Use: procurement, production, sales, financial")

    if status:
        try:
            q = q.filter(Event.status == EventStatus(status))
        except ValueError:
            raise HTTPException(400, f"Unknown status '{status}'. "
                                "Use: pending, applied")

    if team_id is not None:
        q = q.filter(Event.target_team_id == team_id)

    return q.order_by(Event.phase, Event.event_type, Event.id).all()


@router.get("/events/history", response_model=List[EventOut],
            summary="List Event rows across all cycles (full audit history).")
def list_all_events(
    team_id:   Optional[int] = Query(None),
    event_type: Optional[str] = Query(None),
    game:      Game    = Depends(verify_organiser),
    db:        Session = Depends(get_db),
):
    """Full event history for post-game debrief or debugging."""
    q = db.query(Event).filter(Event.game_id == game.id)

    if team_id is not None:
        q = q.filter(Event.target_team_id == team_id)

    if event_type:
        try:
            q = q.filter(Event.event_type == EventType(event_type))
        except ValueError:
            raise HTTPException(400, f"Unknown event_type '{event_type}'.")

    return (
        q.order_by(Event.cycle_id, Event.phase, Event.id)
        .limit(500)
        .all()
    )