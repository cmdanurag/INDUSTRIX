# This file is the central home for all tunable data in the game.

from pydantic_settings import BaseSettings
from dataclasses import dataclass
from typing import Dict

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    APP_ENV: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()

ADMIN_CODE = "adolf hitler"


# ─────────────────────────────────────────────────────────────────────────────
# Quality grade constants
# ─────────────────────────────────────────────────────────────────────────────

# Grades run from 1 to QUALITY_MAX inclusive.
# Index 0 in the storage array is always the "unusable / lost" bucket.
QUALITY_MAX: int = 100

# Minimum usable grade. Units drawn below this threshold are moved to index 0.
MIN_USABLE_GRADE: int = 1


# ─────────────────────────────────────────────────────────────────────────────
# Procurement
# ─────────────────────────────────────────────────────────────────────────────

# Minimum and maximum units per procurement order.
MIN_ORDER_UNITS: int = 1
MAX_ORDER_UNITS: int = 10_000

# Transport mode parameters:
#   cost_multiplier     — multiplied onto the source's base_cost_per_unit
#   damage_sigma_add    — added to the source's quality_sigma during transit
#                         (wider spread = more variance in what actually arrives)
#   p_partial_damage    — probability that the shipment suffers partial damage
#   p_total_loss        — probability of total shipment loss
#
# Note: p_total_loss is checked first; if that fails, p_partial_damage is checked.

@dataclass(frozen=True)
class TransportConfig:
    cost_multiplier:  float   # × source base_cost_per_unit
    damage_sigma_add: float   # Added to quality_sigma during transit draw
    p_partial_damage: float   # Probability of partial damage event
    p_total_loss:     float   # Probability of complete loss


TRANSPORT_CONFIG: Dict[str, TransportConfig] = {
    "air":  TransportConfig(cost_multiplier=2.5,  damage_sigma_add=1.0,  p_partial_damage=0.05, p_total_loss=0.01),
    "rail": TransportConfig(cost_multiplier=1.4,  damage_sigma_add=4.0,  p_partial_damage=0.12, p_total_loss=0.03),
    "road": TransportConfig(cost_multiplier=1.0,  damage_sigma_add=8.0,  p_partial_damage=0.20, p_total_loss=0.05),
}

# When partial damage occurs, this fraction of units are degraded.
# Degraded units have their grade reduced by PARTIAL_DAMAGE_GRADE_PENALTY.
# Units that fall below MIN_USABLE_GRADE after penalty go to index 0.
PARTIAL_DAMAGE_FRACTION:      float = 0.25   # 25% of units affected
PARTIAL_DAMAGE_GRADE_PENALTY: int   = 20     # Affected units lose this many grade points

# When a shipment is sabotaged by a rival (via government), this fraction
# of units are forcibly moved to index 0 (lost/destroyed).
# The exact fraction is set in the GovDeal parameters, but this is the default.
SABOTAGE_DEFAULT_LOSS_FRACTION: float = 0.40


# ─────────────────────────────────────────────────────────────────────────────
# Source event modifiers
# ─────────────────────────────────────────────────────────────────────────────

# When an over-extraction event fires on a source, these deltas are applied
# to that source's parameters for subsequent cycles.
OVEREXTRACTION_QUALITY_MEAN_DELTA:  float = -8.0   # Mean grade drops
OVEREXTRACTION_COST_MULTIPLIER:     float = 1.20   # Price rises 20%

# When a supply disruption event fires, cost rises but quality is unaffected.
DISRUPTION_COST_MULTIPLIER: float = 1.35


# ─────────────────────────────────────────────────────────────────────────────
# Machines
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MachineTierConfig:
    starting_grade:    float  # Machine's output quality mean at birth (1-100 scale)
    throughput:        int    # Max units this machine can process per cycle
    labour_required:   int    # Headcount needed at MANUAL automation
    degradation_rate:  float  # Condition points lost per cycle (at NONE maintenance)
    purchase_cost:     float  # CU to buy
    scrap_value:       float  # CU recovered when machine is scrapped/destroyed


MACHINE_TIER_CONFIG: Dict[str, MachineTierConfig] = {
    "basic":      MachineTierConfig(40,  200, 10, 4.0, 15_000,  1_000),
    "standard":   MachineTierConfig(60,  400, 8,  3.0, 35_000,  3_000),
    "industrial": MachineTierConfig(75,  700, 6,  2.0, 80_000,  8_000),
    "precision":  MachineTierConfig(90, 1000, 4,  1.2,180_000, 25_000),
}

# Machine condition runs 0–100. Machine starts at 100 (full condition).
MACHINE_STARTING_CONDITION: float = 100.0

# Degradation rate multipliers per maintenance level.
MAINTENANCE_DEGRADATION_MULTIPLIER: Dict[str, float] = {
    "none":     1.0,
    "basic":    0.5,
    "full":     0.0,
    "overhaul": 0.0,   # Also recovers — handled separately
}

# Maintenance costs per cycle (CU).
MAINTENANCE_COST: Dict[str, float] = {
    "none":     0.0,
    "basic":    500.0,
    "full":    1_500.0,
    "overhaul": 5_000.0,
}

# How much condition an overhaul can recover.
# Recovery = min(overhaul_recovery_cap, ratchet_ceiling - current_condition)
OVERHAUL_RECOVERY_CAP: float = 20.0

# At what condition level the machine becomes DEGRADED (still runs, grade penalty applied).
MACHINE_DEGRADED_THRESHOLD: float = 40.0

# Grade penalty applied to machine output when machine is DEGRADED.
# effective_machine_grade = machine_grade * (condition / 100) ** CONDITION_GRADE_EXPONENT
CONDITION_GRADE_EXPONENT: float = 0.6

# Scrap payout for a grade-0 finished component (CU per unit).
COMPONENT_SCRAP_PAYOUT: float = 50.0

# When a machine is sabotaged, its condition is reduced by this amount.
SABOTAGE_MACHINE_CONDITION_HIT: float = 60.0


# ─────────────────────────────────────────────────────────────────────────────
# Production quality formula
# ─────────────────────────────────────────────────────────────────────────────

# Weight of raw material grade vs machine output grade in computing
# the finished component grade.
# final_grade = RM_WEIGHT * rm_grade + (1-RM_WEIGHT) * machine_output_grade
RM_WEIGHT: float = 0.40

# Base sigma of the output Normal distribution (before labour/automation adjustments).
BASE_PRODUCTION_SIGMA: float = 15.0

# Assembly formula parameters (combining six component grades into one drone grade).
# drone_grade = (1 - ASSEMBLY_LAMBDA) * simple_avg
#             + ASSEMBLY_LAMBDA * softmax_weakest_link_avg
ASSEMBLY_LAMBDA: float = 0.60   # How much weakest-link dominates (0=pure avg, 1=full WL)
ASSEMBLY_BETA:   float = 0.30   # Sharpness of weakest-link softmax


# ─────────────────────────────────────────────────────────────────────────────
# Labour & Automation
# ─────────────────────────────────────────────────────────────────────────────

# Automation level adjustments to labour headcount requirement.
# effective_labour_required = base_labour_required * AUTOMATION_HEADCOUNT_MULTIPLIER
AUTOMATION_HEADCOUNT_MULTIPLIER: Dict[str, float] = {
    "manual":    1.0,
    "semi_auto": 0.60,
    "full_auto": 0.25,
}

# Automation sigma multiplier — higher automation = tighter output.
# effective_sigma = base_sigma * AUTOMATION_SIGMA_MULTIPLIER
AUTOMATION_SIGMA_MULTIPLIER: Dict[str, float] = {
    "manual":    1.0,
    "semi_auto": 0.65,
    "full_auto": 0.35,
}

# Automation upgrade costs (one-time, applied at purchase).
AUTOMATION_UPGRADE_COST: Dict[str, float] = {
    "manual":    0.0,
    "semi_auto": 20_000.0,
    "full_auto": 60_000.0,
}

# Labour skill runs 0–100. Starting skill for a new team.
STARTING_SKILL: float = 40.0

# Passive skill gain per cycle when turnover is low (morale >= MORALE_HIGH_THRESHOLD).
SKILL_GAIN_LOW_TURNOVER:  float = 2.0
SKILL_GAIN_HIGH_TURNOVER: float = -5.0   # Skill lost per cycle when turnover is high

# Morale thresholds.
MORALE_HIGH_THRESHOLD:   float = 70.0   # Above this: low turnover, skill grows
MORALE_LOW_THRESHOLD:    float = 35.0   # Below this: high turnover, skill drops
MORALE_RIOT_THRESHOLD:   float = 15.0   # Below this: riot triggered

# Starting morale for a new team.
STARTING_MORALE: float = 60.0

# Morale effects of wage level per cycle.
WAGE_MORALE_DELTA: Dict[str, float] = {
    "below_market": -10.0,
    "market":         0.0,
    "above_market":  +8.0,
}

# Morale effect of understaffing (per % below required headcount).
UNDERSTAFFING_MORALE_PENALTY_PER_PCT: float = 0.20  # 0.20 morale per 1% understaffed

# Wage costs per worker per cycle (CU).
WAGE_COST_PER_WORKER: Dict[str, float] = {
    "below_market": 300.0,
    "market":       500.0,
    "above_market": 750.0,
}

# How much skill reduces sigma.
# sigma_after_skill = sigma_before * (1 - skill_factor * SKILL_SIGMA_REDUCTION)
# skill_factor = skill_score / 100   clamped [0.1, 1.0]
SKILL_SIGMA_REDUCTION: float = 0.50   # Max 50% sigma reduction at skill=100

# Poaching event — how many skill points the target loses.
POACH_SKILL_HIT:   float = 15.0
POACH_RND_STEAL_PROBABILITY: float = 0.40  # Probability that a poach also steals an R&D level

# Riot — production fraction that survives.
RIOT_PRODUCTION_SURVIVAL: float = 0.0   # Full halt when riot fires

# Strike — production fraction that survives.
STRIKE_PRODUCTION_SURVIVAL: float = 0.50


# ─────────────────────────────────────────────────────────────────────────────
# R&D
# ─────────────────────────────────────────────────────────────────────────────

# Maximum R&D level per focus area per component.
MAX_RND_LEVEL: int = 5

# CU cost to research one level (per focus area — same cost for all).
RND_LEVEL_COST: float = 10_000.0

# R&D takes this many cycles to complete one level (multi-cycle process).
RND_CYCLES_PER_LEVEL: int = 2

# Passive R&D decay per cycle if no investment is made (fraction of level lost).
# Modelled as a probability: each cycle there is this chance of losing 1 level.
RND_DECAY_PROBABILITY: float = 0.05   # 5% per cycle per focus area

# Bonus per R&D level for each focus area.
RND_QUALITY_BONUS_PER_LEVEL:     float = 3.0   # +3 to effective machine output mean
RND_CONSISTENCY_BONUS_PER_LEVEL: float = 2.0   # -2 from sigma (floor: sigma >= 2.0)
RND_YIELD_BONUS_PER_LEVEL:       float = 0.04  # -4% raw material units consumed per level

# R&D profile reward/penalty parameters (applied at assembly time).
# See rnd_profile_multiplier() in production_service for the formula.
RND_UNIFORM_REWARD_RATE:       float = 0.02   # +2% drone grade per level of minimum across components
RND_SPECIALISATION_REWARD_RATE: float = 0.015  # Convex bonus for deep specialisation
RND_MEDIOCRITY_PENALTY_RATE:   float = 0.01   # Penalty for mediocre spread


# ─────────────────────────────────────────────────────────────────────────────
# Sales & Market
# ─────────────────────────────────────────────────────────────────────────────

# Base market prices per quality tier (CU per drone unit).
# These are the reference prices before brand, demand, and competition adjustments.
PRICE_REJECT_SCRAP:      float = 200.0    # Scrap value — always available
PRICE_REJECT_BLACK_MKT:  float = 600.0    # Black market price per reject unit
PRICE_SUBSTANDARD:       float = 1_400.0  # Discounted sale price
PRICE_STANDARD:          float = 3_000.0  # Standard market price
PRICE_PREMIUM_NORMAL:    float = 3_000.0  # Premium units sold at standard price (brand signal)
PRICE_PREMIUM_PREMIUM:   float = 4_800.0  # Premium units sold at premium price

# Inventory holding cost per unsold drone per cycle (CU).
INVENTORY_HOLDING_COST_PER_UNIT: float = 40.0

# Black market discovery probability.
# P(discovery) = BASE * (units_black_mkt / total_produced) * (1 - brand_leniency)
BLACK_MARKET_DISCOVERY_BASE: float = 0.55

# Fine multiplier when black market is discovered (× revenue from black market sales).
BLACK_MARKET_FINE_MULTIPLIER: float = 3.0

# Brand impact constants (applied at cycle end to brand_score).
BRAND_DECAY_PER_CYCLE:             float = 0.94   # Brand score × this each cycle
BRAND_DELTA_PREMIUM_SELL:          float = +6.0   # Sold premium tier at premium price
BRAND_DELTA_STANDARD_SELL:         float = +1.5   # Sold standard tier
BRAND_DELTA_SUBSTANDARD_SELL:      float = -5.0   # Sold sub-standard
BRAND_DELTA_BLACK_MARKET_FOUND:    float = -25.0  # Black market discovered
BRAND_DELTA_BLACK_MARKET_UNFOUND:  float = -3.0   # Black market not discovered (small risk signal)
BRAND_DELTA_AUDIT_PASS:            float = +4.0
BRAND_DELTA_AUDIT_FAIL:            float = -18.0
BRAND_DELTA_GOV_LOAN:              float = -8.0   # Taking a government loan signals distress

# Brand tier thresholds (score → tier).
BRAND_TIER_THRESHOLDS: Dict[str, float] = {
    "poor": 0.0, "fair": 25.0, "good": 55.0, "excellent": 80.0,
}

# Brand leniency: max fraction by which effective q_soft is lowered for excellent brand.
MAX_BRAND_LENIENCY: float = 0.15   # Excellent brand → q_soft effectively 15% lower


# ── Market simulation parameters ─────────────────────────────────────────────

# Base market capacity per cycle (total drones the market can absorb at standard price).
# Organiser can adjust this between cycles via game settings.
BASE_MARKET_CAPACITY: int = 2_000

# How sensitively market demand responds to price relative to tier base price.
# price_factor = (base_price / actual_price) ^ PRICE_ELASTICITY
# Selling below base → price_factor > 1 (more sales). Above → factor < 1.
PRICE_ELASTICITY: float = 1.4

# How much brand score affects a team's share of market demand.
# market_share_weight = brand_score ^ BRAND_DEMAND_EXPONENT (then normalised across teams)
BRAND_DEMAND_EXPONENT: float = 1.2

# Maximum fraction of market any single team can capture (prevents monopoly lock-out).
MAX_MARKET_SHARE: float = 0.70

# Paid diagnostic costs (CU) — teams can buy deeper analysis during PHASE1_DISPLAY.
DIAGNOSTIC_COST_PRODUCTION_DETAIL:  float = 2_000.0   # Exact component means + sigmas
DIAGNOSTIC_COST_MARKET_INTEL:       float = 3_000.0   # Rival brand scores + last-cycle volumes
DIAGNOSTIC_COST_DEMAND_FORECAST:    float = 1_500.0   # Next-cycle demand estimate


# ─────────────────────────────────────────────────────────────────────────────
# Loans & Government restrictions
# ─────────────────────────────────────────────────────────────────────────────

# Government loan interest rate per cycle (applied to outstanding principal).
GOV_LOAN_INTEREST_RATE: float = 0.15   # 15% per cycle

# Minimum quality floor imposed on government loan borrowers.
# If a team's drone_weighted_mean falls below this, bankruptcy is triggered.
GOV_LOAN_MIN_QUALITY_FLOOR: float = 25.0

# Inter-team loan: minimum and maximum interest rates the organiser will approve.
INTER_TEAM_LOAN_MIN_RATE: float = 0.02   # 2% per cycle minimum
INTER_TEAM_LOAN_MAX_RATE: float = 0.12   # 12% per cycle maximum


# ─────────────────────────────────────────────────────────────────────────────
# Leaderboard scoring weights
# All weights should sum to 1.0 for a clean 0-1 score range.
# ─────────────────────────────────────────────────────────────────────────────

SCORE_WEIGHT_FUNDS:     float = 0.40   # Liquid capital share
SCORE_WEIGHT_BRAND:     float = 0.30   # Brand score / 100
SCORE_WEIGHT_REVENUE:   float = 0.20   # Cumulative revenue share
SCORE_WEIGHT_INVENTORY: float = 0.10   # Penalises holding too much unsold stock


# ─────────────────────────────────────────────────────────────────────────────
# Backroom deals phase
# ─────────────────────────────────────────────────────────────────────────────

# Base discovery probability for black market sales (already in sales config).
# Additional discovery events checked at end-of-cycle in backroom phase.

# Discovery probability for each type of fraudulent activity.
# These are independent rolls — each fraud type is checked separately.
DISCOVERY_PROB_BLACK_MARKET_ONGOING: float = 0.20  # Per cycle the team keeps selling BM
DISCOVERY_PROB_GOVT_DEAL_FRAUD:      float = 0.15  # Per cycle of active shady govt deal
DISCOVERY_PROB_CARTEL_PRICING:       float = 0.12  # If team is in a price-fixing arrangement

# Fine multipliers when discovered (× the relevant revenue / deal value).
FINE_MULTIPLIER_BLACK_MARKET_STD:    float = 3.0
FINE_MULTIPLIER_BLACK_MARKET_BOMBERICA: float = 15.0  # The easter egg
FINE_MULTIPLIER_GOVT_FRAUD:          float = 5.0
FINE_MULTIPLIER_CARTEL:              float = 4.0

# Probability that a black market discovery triggers the Bomberica easter egg.
P_BOMBERICA:                         float = 0.25

# Base probability that a government-brokered deal is discovered by the public.
DEAL_DISCOVERY_BASE_PROB:            float = 0.10
# Each CU of bribe paid reduces discovery probability (more money = better cover-up).
DEAL_DISCOVERY_BRIBE_REDUCTION_PER_K: float = 0.01  # -1% per 1000 CU bribed

# Effect queue: how many cycles ahead an effect can be scheduled.
MAX_EFFECT_SCHEDULE_CYCLES_AHEAD:    int   = 3

# Global event cost range (CU the organiser "earns" from triggering events — flavour).
GLOBAL_EVENT_CHAOS_BONUS_MIN: float = 0.0
GLOBAL_EVENT_CHAOS_BONUS_MAX: float = 0.0   # Set > 0 to make events pay the gov
