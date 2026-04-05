# This file is the central home for all tunable data in the game.

from pydantic_settings import BaseSettings
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

ADMIN_CODE = "adolf_hitler"

"""
core/config.py
==============
Every tunable game constant lives here.
Rule: never hardcode a number in a service file.
"""


# ── Quality scale ─────────────────────────────────────────────────────────────
QUALITY_MAX: int   = 100
MIN_USABLE_GRADE: int = 1

# ── Transport ─────────────────────────────────────────────────────────────────
# base_cost        : minimum cost charged irrespective of material quantity
# var_cost         : cost charged scaling with material quantity
# sigma_add        : added to source quality_sigma during draw
# mean_reduce      : subtracted from source quality_mean during draw
# p_damage         : probability of partial damage event
TRANSPORT: Dict[str, Dict] = {
    "air":   {"base_cost": 3000, "var_cost": 0.10,  "sigma_add": 0.0, "p_damage": 0.00, "mean_reduce": 0.00, "vulnerability": 0.00},
    "water": {"base_cost": 1500, "var_cost": 0.005, "sigma_add": 9.0, "p_damage": 0.18, "mean_reduce": 4.00, "vulnerability": 0.50},
    "rail":  {"base_cost": 500,  "var_cost": 0.02,  "sigma_add": 3.5, "p_damage": 0.07, "mean_reduce": 0.50, "vulnerability": 0.80},
    "road":  {"base_cost": 100,  "var_cost": 0.04,  "sigma_add": 6.0, "p_damage": 0.14, "mean_reduce": 1.50, "vulnerability": 1.00},
}

PARTIAL_DAMAGE_FRACTION: float = 0.25
PARTIAL_DAMAGE_PENALTY:  int   = 20

# ── Machine tiers ─────────────────────────────────────────────────────────────
# Keys: starting_grade, throughput, labour_required, degradation_rate,
#       purchase_cost, scrap_value
MACHINE_TIERS: Dict[str, Dict] = {
    "basic":      {"grade": 40, "throughput": 200,  "labour": 4, "degrade": 4.0, "buy": 15_000,  "scrap": 1_000},
    "standard":   {"grade": 60, "throughput": 400,  "labour": 8,  "degrade": 3.0, "buy": 35_000,  "scrap": 3_000},
    "industrial": {"grade": 75, "throughput": 700,  "labour": 10,  "degrade": 2.0, "buy": 80_000,  "scrap": 8_000},
    "precision":  {"grade": 90, "throughput": 1000, "labour": 20,  "degrade": 1.2, "buy": 180_000, "scrap": 25_000},
}
MACHINE_MAX_CONDITION:    float = 100.0
MACHINE_DEGRADED_AT:      float = 40.0
CONDITION_GRADE_EXPONENT: float = 0.6
OVERHAUL_RECOVERY_CAP:    float = 20.0

MAINTENANCE_COST: Dict[str, float] = {
    "none": 0.0, "basic": 500.0, "full": 1_500.0, "overhaul": 5_000.0,
}
MAINTENANCE_DEGRADE_MULT: Dict[str, float] = {
    "none": 1.0, "basic": 0.6, "full": 0.3, "overhaul": 0.1,
}

# ── Automation ────────────────────────────────────────────────────────────────
AUTOMATION_LABOUR_MULT: Dict[str, float] = {
    "manual": 1.0, "semi_auto": 0.60, "full_auto": 0.25,
}
AUTOMATION_SIGMA_MULT: Dict[str, float] = {
    "manual": 1.0, "semi_auto": 0.65, "full_auto": 0.35,
}
AUTOMATION_UPGRADE_COST: Dict[str, float] = {
    "manual": 0.0, "semi_auto": 200_000.0, "full_auto": 600_000.0,
}

# ── Labour ────────────────────────────────────────────────────────────────────
STARTING_SKILL:  float = 40.0
STARTING_MORALE: float = 60.0
MORALE_HIGH:     float = 70.0
MORALE_LOW:      float = 35.0
MORALE_RIOT:     float = 15.0

SKILL_GAIN_HIGH_MORALE: float =  2.0
SKILL_GAIN_LOW_MORALE:  float = -5.0

WAGE_MORALE_DELTA: Dict[str, float] = {
    "below_market": -10.0, "market": 0.0, "above_market": 8.0,
}
WAGE_COST_PER_WORKER: Dict[str, float] = {
    "below_market": 300.0, "market": 500.0, "above_market": 750.0,
}
UNDERSTAFFING_MORALE_PENALTY: float = 0.20  # per 1% understaffed

RIOT_SURVIVAL:   float = 0.0
STRIKE_SURVIVAL: float = 0.5
POACH_SKILL_HIT: float = 15.0

# ── Production formula ────────────────────────────────────────────────────────
RM_WEIGHT:              float = 0.40
BASE_SIGMA:             float = 15.0
SKILL_SIGMA_REDUCTION:  float = 0.50
ASSEMBLY_LAMBDA:        float = 0.60
ASSEMBLY_BETA:          float = 0.30

# ── R&D ───────────────────────────────────────────────────────────────────────
MAX_RND_LEVEL:           int   = 5
RND_COST_PER_LEVEL:      float = 100_000.0
RND_CYCLES_PER_LEVEL:    int   = 2
RND_DECAY_PROBABILITY:   float = 0.05

RND_QUALITY_BONUS:     float = 3.0   # per level: +3 to machine output mean
RND_CONSISTENCY_BONUS: float = 2.0   # per level: -2 sigma (floor 2.0)
RND_YIELD_BONUS:       float = 0.04  # per level: -4% raw material consumed

# ── Sales & market ────────────────────────────────────────────────────────────
PRICE_REJECT_SCRAP:     float = 200.0
PRICE_REJECT_BLACK_MKT: float = 600.0
PRICE_SUBSTANDARD:      float = 1_400.0
PRICE_STANDARD:         float = 3_000.0
PRICE_PREMIUM_NORMAL:   float = 3_000.0
PRICE_PREMIUM_SELL:     float = 4_800.0

HOLDING_COST_PER_UNIT:  float = 40.0

BLACK_MKT_DISCOVERY_BASE:     float = 0.55
BLACK_MKT_FINE_MULTIPLIER:    float = 3.0

BRAND_DECAY:                  float = 0.94
BRAND_DELTA_PREMIUM_SELL:     float = 6.0
BRAND_DELTA_STANDARD_SELL:    float = 1.5
BRAND_DELTA_SUBSTANDARD_SELL: float = -5.0
BRAND_DELTA_BLACK_MKT_FOUND:  float = -25.0
BRAND_DELTA_BLACK_MKT_HIDDEN: float = -3.0
BRAND_DELTA_AUDIT_PASS:       float = 4.0
BRAND_DELTA_AUDIT_FAIL:       float = -18.0
BRAND_DELTA_GOV_LOAN:         float = -8.0
BRAND_DELTA_DEAL_FOUND:       float = -20.0

BRAND_TIERS: Dict[str, float] = {
    "poor": 0.0, "fair": 25.0, "good": 55.0, "excellent": 80.0,
}
MAX_BRAND_LENIENCY: float = 0.15

BASE_MARKET_CAPACITY: int   = 2_000
PRICE_ELASTICITY:     float = 1.4
BRAND_DEMAND_EXPONENT: float = 1.2
MAX_MARKET_SHARE:     float = 0.70

# ── Loans ─────────────────────────────────────────────────────────────────────
GOV_LOAN_INTEREST_RATE:    float = 0.15
GOV_LOAN_MIN_QUALITY_FLOOR: float = 25.0
INTER_LOAN_MIN_RATE:       float = 0.02
INTER_LOAN_MAX_RATE:       float = 0.12

# ── Backroom deals ────────────────────────────────────────────────────────────
DEAL_LOG_SCALE_DIVISOR:    float = 5.0
DEAL_EFFECT_CAP:           float = 2.0
DEAL_DISCOVERY_DECAY:      float = 0.80
DEAL_SIZE_DISCOVERY_RATE:  float = 0.02
DEAL_REPEAT_STACK_RATE:    float = 0.08
DEAL_FINE_MULTIPLIER:      float = 2.5

DEAL_BRIBE_FLOOR: Dict[str, float] = {
    "red_supply_sabotage": 5_000, "red_price_inflation": 4_000,
    "green_priority_supply": 4_000, "green_subsidised_inputs": 3_000,
    "red_machine_sabotage": 8_000, "red_infra_delay": 6_000,
    "green_fast_track_infra": 5_000, "red_labour_strike": 7_000,
    "red_labour_poach": 6_000, "red_rnd_sabotage": 8_000,
    "green_skilled_labour": 4_000, "green_research_grant": 12_000,
    "red_market_limit": 7_000, "red_demand_suppression": 6_000,
    "red_price_pressure": 5_000, "green_demand_boost": 6_000,
    "green_gov_purchase": 10_000, "red_targeted_audit": 4_000,
    "red_arbitrary_fine": 5_000, "green_audit_immunity": 8_000,
    "green_quality_waiver": 6_000, "green_tax_evasion": 5_000,
}

DEAL_BASE_DISCOVERY: Dict[str, float] = {
    "red_supply_sabotage": 0.12, "red_price_inflation": 0.08,
    "green_priority_supply": 0.06, "green_subsidised_inputs": 0.07,
    "red_machine_sabotage": 0.18, "red_infra_delay": 0.10,
    "green_fast_track_infra": 0.08, "red_labour_strike": 0.14,
    "red_labour_poach": 0.13, "red_rnd_sabotage": 0.15,
    "green_skilled_labour": 0.06, "green_research_grant": 0.10,
    "red_market_limit": 0.20, "red_demand_suppression": 0.18,
    "red_price_pressure": 0.16, "green_demand_boost": 0.12,
    "green_gov_purchase": 0.09, "red_targeted_audit": 0.05,
    "red_arbitrary_fine": 0.07, "green_audit_immunity": 0.08,
    "green_quality_waiver": 0.09, "green_tax_evasion": 0.11,
}

# ── Leaderboard weights ───────────────────────────────────────────────────────
# All weights sum to 1.0 (inventory_penalty is subtracted).
LEADERBOARD_WEIGHTS: Dict[str, float] = {
    "closing_funds":     0.25,
    "cumulative_profit": 0.30,
    "brand_score":       0.20,
    "quality_avg":       0.15,
    "inventory_penalty": -0.10,
}
LEADERBOARD_NORMALISE: Dict[str, float] = {
    "closing_funds":     500_000.0,
    "cumulative_profit": 300_000.0,
    "brand_score":       100.0,
    "quality_avg":       100.0,
    "inventory_penalty": 5_000.0,
}
# ── Market factions ───────────────────────────────────────────────────────────
# Default faction definitions seeded on game creation.
# Each faction is a rational independent buyer with fixed constraints.
# Organiser can modify any of these between cycles via the admin API.
#
# Fields:
#   name            : display name
#   tier_preference : primary quality tier they want ("standard", "premium", etc.)
#   price_ceiling   : max CU/unit at full volume — they will NOT exceed this
#   volume          : units they want this cycle under ideal conditions
#   flexibility     : 0.0–1.0 — willingness to step down one tier when ideal
#                     is exhausted. Remaining appetite = volume_remaining × flexibility
#   brand_min       : minimum brand score required to sell to this faction (0 = none)
DEFAULT_MARKET_FACTIONS: list = [
    {
        "name":            "Government Procurement",
        "tier_preference": "premium",
        "price_ceiling":   4_500.0,
        "volume":          150,
        "flexibility":     0.0,    # Will not accept anything below premium
        "brand_min":       55.0,   # Only buys from GOOD or EXCELLENT brand
    },
    {
        "name":            "Industrial Operators",
        "tier_preference": "standard",
        "price_ceiling":   3_200.0,
        "volume":          400,
        "flexibility":     0.5,    # Will step down to substandard if needed
        "brand_min":       0.0,
    },
    {
        "name":            "Municipal Services",
        "tier_preference": "standard",
        "price_ceiling":   2_800.0,
        "volume":          300,
        "flexibility":     0.3,
        "brand_min":       25.0,   # Requires at least FAIR brand
    },
    {
        "name":            "NGO / Aid Sector",
        "tier_preference": "substandard",
        "price_ceiling":   1_600.0,
        "volume":          250,
        "flexibility":     0.8,    # Very flexible — will take almost anything
        "brand_min":       0.0,
    },
    {
        "name":            "Budget Resellers",
        "tier_preference": "substandard",
        "price_ceiling":   1_200.0,
        "volume":          350,
        "flexibility":     0.6,
        "brand_min":       0.0,
    },
    {
        "name":            "Private Collectors",
        "tier_preference": "premium",
        "price_ceiling":   5_000.0,
        "volume":          80,
        "flexibility":     0.1,    # Almost no flexibility but pay top price
        "brand_min":       0.0,
    },
]

# Tier hierarchy for faction stepping-down logic.
# When a faction's preferred tier is exhausted they step down by one.
TIER_FALLBACK: Dict[str, str] = {
    "premium":     "standard",
    "standard":    "substandard",
    "substandard": None,
    "reject":      None,           # No fallback from reject
}
