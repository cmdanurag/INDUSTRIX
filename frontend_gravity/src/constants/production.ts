/**
 * backend/core/config.py aligned constants for the frontend.
 * Authoritative for current game balance.
 */

export const MACHINE_TIERS = {
  basic:      { grade: 40, throughput: 200,  labour: 4, degrade: 4.0, buy: 15000,  scrap: 1000 },
  standard:   { grade: 60, throughput: 400,  labour: 8, degrade: 3.0, buy: 35000,  scrap: 3000 },
  industrial: { grade: 75, throughput: 700,  labour: 10, degrade: 2.0, buy: 80000,  scrap: 8000 },
  precision:  { grade: 90, throughput: 1000, labour: 20, degrade: 1.2, buy: 180000, scrap: 25000 },
};

export const MAINTENANCE_COSTS = {
  none: 0,
  basic: 500,
  full: 1500,
  overhaul: 5000,
};

export const MAINTENANCE_DEGRADE_MULT = {
  none: 1.0,
  basic: 0.6,
  full: 0.3,
  overhaul: 0.1,
};

export const OVERHAUL_RECOVERY_CAP = 20.0;
export const MACHINE_MAX_CONDITION = 100.0;

export const WAGE_COSTS = {
  below_market: 300,
  market: 500,
  above_market: 750,
};

export const WAGE_MORALE_DELTA = {
  below_market: -10.0,
  market: 0.0,
  above_market: 8.0,
};

export const UNDERSTAFFING_MORALE_PENALTY = 0.20; // per 1% understaffed

export const AUTOMATION_LABOUR_MULT = {
  manual: 1.0,
  semi_auto: 0.6,
  full_auto: 0.25,
};

export const AUTOMATION_SIGMA_MULT = {
  manual: 1.0,
  semi_auto: 0.65,
  full_auto: 0.35,
};

export const AUTOMATION_UPGRADE_COST = {
  manual: 0.0,
  semi_auto: 200000,
  full_auto: 600000,
};

export const RND_COST_PER_LEVEL = 100000.0;
export const RND_QUALITY_BONUS = 3.0;
export const RND_CONSISTENCY_BONUS = 2.0;
export const RND_YIELD_BONUS = 0.04;

export const BASE_SIGMA = 15.0;
export const SKILL_SIGMA_REDUCTION = 0.50;
export const CONDITION_GRADE_EXPONENT = 0.6;
