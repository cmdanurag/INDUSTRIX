"""
core/enums.py
=============
All enumerations for Industrix. One source of truth —
never define game constants anywhere else.
"""
import enum


# ── Components ────────────────────────────────────────────────────────────────

class ComponentType(str, enum.Enum):
    AIRFRAME         = "airframe"
    PROPULSION       = "propulsion"
    AVIONICS         = "avionics"
    FIRE_SUPPRESSION = "fire_suppression"
    SENSING_SAFETY   = "sensing_safety"
    BATTERY          = "battery"


# ── Procurement ───────────────────────────────────────────────────────────────

class TransportMode(str, enum.Enum):
    AIR  = "air"
    RAIL = "rail"
    ROAD = "road"
    WATER = "water"


# ── Production ────────────────────────────────────────────────────────────────

class MachineTier(str, enum.Enum):
    BASIC      = "basic"
    STANDARD   = "standard"
    INDUSTRIAL = "industrial"
    PRECISION  = "precision"


class MaintenanceLevel(str, enum.Enum):
    NONE     = "none"
    BASIC    = "basic"
    FULL     = "full"
    OVERHAUL = "overhaul"


class AutomationLevel(str, enum.Enum):
    MANUAL    = "manual"
    SEMI_AUTO = "semi_auto"
    FULL_AUTO = "full_auto"


class WageLevel(str, enum.Enum):
    BELOW_MARKET = "below_market"
    MARKET       = "market"
    ABOVE_MARKET = "above_market"


class RndFocus(str, enum.Enum):
    QUALITY     = "quality"
    CONSISTENCY = "consistency"
    YIELD       = "yield"


# ── Sales ─────────────────────────────────────────────────────────────────────

class QualityTier(str, enum.Enum):
    REJECT      = "reject"
    SUBSTANDARD = "substandard"
    STANDARD    = "standard"
    PREMIUM     = "premium"


class SalesAction(str, enum.Enum):
    SELL_MARKET     = "sell_market"
    SELL_PREMIUM    = "sell_premium"
    SELL_DISCOUNTED = "sell_discounted"
    HOLD            = "hold"
    SCRAP           = "scrap"
    BLACK_MARKET    = "black_market"


class BrandTier(str, enum.Enum):
    POOR      = "poor"
    FAIR      = "fair"
    GOOD      = "good"
    EXCELLENT = "excellent"


# ── Cycle ─────────────────────────────────────────────────────────────────────

class CyclePhase(str, enum.Enum):
    """
    Linear phase machine. Organiser calls /advance at each arrow.

    PROCUREMENT_OPEN  →  PRODUCTION_OPEN  →  SALES_OPEN  →  BACKROOM
          ↑ advance           ↑ advance         ↑ advance
    From BACKROOM the organiser calls /next (new cycle) or /end-game.
    """
    PROCUREMENT_OPEN = "procurement_open"
    PRODUCTION_OPEN  = "production_open"
    SALES_OPEN       = "sales_open"
    BACKROOM         = "backroom"
    GAME_OVER        = "game_over"


# ── Events ────────────────────────────────────────────────────────────────────

class EventPhase(str, enum.Enum):
    """
    Which resolution service owns and consumes this event.

    PROCUREMENT — consumed at the start of procurement resolution.
                  Applied before quality draws so sabotage/subsidy
                  affects what actually arrives.

    PRODUCTION  — consumed at the start of production resolution.
                  Applied before output is calculated so machine
                  sabotage, strikes, poaching etc. affect this cycle.

    SALES       — consumed at the start of sales resolution.
                  Applied before tier actions run so demand suppression,
                  market limits, price pressure etc. affect this cycle.

    FINANCIAL   — consumed at the END of sales resolution, after
                  revenue is booked. Covers loan interest, fines,
                  tax refunds, and global market shifts.
    """
    PROCUREMENT = "procurement"
    PRODUCTION = "production"
    SALES = "sales"
    FINANCIAL = "financial"


class EventType(str, enum.Enum):
    """
    Fine-grained type. The phase column says who resolves it;
    the type says what the payload means.

    ── PROCUREMENT phase ────────────────────────────────────────────
    SUPPLY_SABOTAGE
        payload: {"component": str, "loss_fraction": float}
        Effect: that fraction of arriving units moved to scrap bucket.

    PRICE_INFLATION
        payload: {"component": str, "cost_multiplier": float}
        Effect: transport + material cost multiplied for that component.

    PRIORITY_SUPPLY
        payload: {"component": str, "mean_bonus": float}
        Effect: quality_mean for that component raised by bonus.

    SUBSIDISED_INPUTS
        payload: {"component": str, "cost_multiplier": float}  (<1.0)
        Effect: procurement cost for that component reduced.

    ── PRODUCTION phase ─────────────────────────────────────────────
    MACHINE_SABOTAGE
        payload: {"component": str, "condition_hit": float}
        Effect: machine condition for that component reduced.

    INFRA_DELAY
        payload: {"component": str}
        Effect: any machine upgrade decision for that component
                is ignored this cycle.

    FAST_TRACK_INFRA
        payload: {"component": str,
                  "condition_bonus": float, "quality_bonus": float}
        Effect: if a new machine is bought this cycle for that component,
                starting condition and grade are boosted.

    LABOUR_STRIKE
        payload: {}
        Effect: production_survival set to STRIKE_SURVIVAL (0.5).

    LABOUR_POACH
        payload: {"skill_hit": float}
        Effect: team's skill_level reduced.

    RND_SABOTAGE
        payload: {"component": str, "focus": str, "levels_stolen": int}
        Effect: rnd level for that component+focus reduced.

    SKILLED_LABOUR
        payload: {"skill_bonus": float}
        Effect: team's skill_level increased.

    RND_INVESTMENT
        payload: {"component": str, "focus": str, "level_arriving": int}
        Effect: rnd level incremented when this event is consumed.
                Created by the team's production decision; scheduled
                for the cycle when it matures.

    ── SALES phase ──────────────────────────────────────────────────
    MARKET_LIMIT
        payload: {"block_fraction": float}
        Effect: that fraction of sellable drones blocked from market.

    DEMAND_SUPPRESSION
        payload: {"demand_multiplier": float}  (<1.0)
        Effect: team's brand_demand_weight multiplied.

    PRICE_PRESSURE
        payload: {}
        Effect: effective sell price capped at PRICE_SUBSTANDARD.

    DEMAND_BOOST
        payload: {"demand_multiplier": float}  (>1.0)
        Effect: team's brand_demand_weight multiplied.

    GOV_PURCHASE
        payload: {"units": int, "price_per_unit": float}
        Effect: government buys this many drones at guaranteed price,
                added to revenue before market allocation.

    QUALITY_WAIVER
        payload: {"threshold_reduction": float}
        Effect: effective qr_hard lowered by this amount for this cycle.

    AUDIT_IMMUNITY
        payload: {}
        Effect: team skips any audit triggered this cycle.

    ── FINANCIAL phase (end of sales) ───────────────────────────────
    LOAN_INTEREST
        payload: {"amount": float, "lender_team_id": int|null}
        Effect: amount deducted from borrower; if lender_team_id is
                set, same amount credited to lender.

    ARBITRARY_FINE
        payload: {"fine_amount": float}
        Effect: fine_amount deducted from team's funds.

    TAX_EVASION_REFUND
        payload: {"refund_fraction": float}
        Effect: refund_fraction × total_costs_this_cycle credited back.
                Resolved after all costs are known.

    GLOBAL_MARKET_SHIFT
        payload: {
            "market_demand_multiplier_delta": float,  # optional
            "qr_hard_delta":    float,                # optional
            "qr_soft_delta":    float,                # optional
            "qr_premium_delta": float,                # optional
        }
        Effect: adjusts the Game record's global parameters.
                target_team_id is NULL (affects all teams via game state).
    """
    # Procurement
    SUPPLY_SABOTAGE = "supply_sabotage"
    PRICE_INFLATION = "price_inflation"
    PRIORITY_SUPPLY = "priority_supply"
    SUBSIDISED_INPUTS = "subsidised_inputs"

    # Production
    MACHINE_SABOTAGE = "machine_sabotage"
    INFRA_DELAY = "infra_delay"
    FAST_TRACK_INFRA = "fast_track_infra"
    LABOUR_STRIKE = "labour_strike"
    LABOUR_POACH = "labour_poach"
    RND_SABOTAGE = "rnd_sabotage"
    SKILLED_LABOUR = "skilled_labour"
    RND_INVESTMENT = "rnd_investment"

    # Sales
    MARKET_LIMIT = "market_limit"
    DEMAND_SUPPRESSION = "demand_suppression"
    PRICE_PRESSURE = "price_pressure"
    DEMAND_BOOST = "demand_boost"
    GOV_PURCHASE = "gov_purchase"
    QUALITY_WAIVER = "quality_waiver"
    AUDIT_IMMUNITY = "audit_immunity"

    # Financial
    LOAN_INTEREST = "loan_interest"
    ARBITRARY_FINE = "arbitrary_fine"
    TAX_EVASION_REFUND = "tax_evasion_refund"
    GLOBAL_MARKET_SHIFT = "global_market_shift"


class EventStatus(str, enum.Enum):
    PENDING = "pending"  # created, waiting to be consumed
    APPLIED = "applied"  # consumed by its phase — soft delete for audit trail


# ── Government deals (backroom negotiation records) ───────────────────────────

class GovDealType(str, enum.Enum):
    # Procurement
    RED_SUPPLY_SABOTAGE = "red_supply_sabotage"
    RED_PRICE_INFLATION = "red_price_inflation"
    GREEN_PRIORITY_SUPPLY = "green_priority_supply"
    GREEN_SUBSIDISED_INPUTS = "green_subsidised_inputs"
    # Infrastructure
    RED_MACHINE_SABOTAGE = "red_machine_sabotage"
    RED_INFRA_DELAY = "red_infra_delay"
    GREEN_FAST_TRACK_INFRA = "green_fast_track_infra"
    # Labour & R&D
    RED_LABOUR_STRIKE = "red_labour_strike"
    RED_LABOUR_POACH = "red_labour_poach"
    RED_RND_SABOTAGE = "red_rnd_sabotage"
    GREEN_SKILLED_LABOUR = "green_skilled_labour"
    GREEN_RESEARCH_GRANT = "green_research_grant"
    # Sales & market
    RED_MARKET_LIMIT = "red_market_limit"
    RED_DEMAND_SUPPRESSION = "red_demand_suppression"
    RED_PRICE_PRESSURE = "red_price_pressure"
    GREEN_DEMAND_BOOST = "green_demand_boost"
    GREEN_GOV_PURCHASE = "green_gov_purchase"
    # Legal
    RED_TARGETED_AUDIT = "red_targeted_audit"
    RED_ARBITRARY_FINE = "red_arbitrary_fine"
    GREEN_AUDIT_IMMUNITY = "green_audit_immunity"
    GREEN_QUALITY_WAIVER = "green_quality_waiver"
    GREEN_TAX_EVASION = "green_tax_evasion"


class GovDealStatus(str, enum.Enum):
    PENDING = "pending"
    APPLIED = "applied"
    DISCOVERED = "discovered"
    CANCELLED = "cancelled"
