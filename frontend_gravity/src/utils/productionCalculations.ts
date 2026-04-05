import { 
  MAINTENANCE_DEGRADE_MULT, 
  MACHINE_MAX_CONDITION, 
  OVERHAUL_RECOVERY_CAP, 
  WAGE_MORALE_DELTA, 
  UNDERSTAFFING_MORALE_PENALTY,
  BASE_SIGMA,
  AUTOMATION_SIGMA_MULT,
  SKILL_SIGMA_REDUCTION,
  RND_CONSISTENCY_BONUS,
  CONDITION_GRADE_EXPONENT,
  MACHINE_TIERS,
  RND_QUALITY_BONUS
} from '../constants/production';

/**
 * Calculates projected condition for a machine after one cycle.
 */
export const calculateProjectedCondition = (current: number, maintenance: string, tier: string): number => {
  const cfg = MACHINE_TIERS[tier as keyof typeof MACHINE_TIERS] || MACHINE_TIERS.standard;
  const degradeMult = MAINTENANCE_DEGRADE_MULT[maintenance as keyof typeof MAINTENANCE_DEGRADE_MULT] || 1.0;
  const degrade = cfg.degrade * degradeMult;

  if (maintenance === 'overhaul') {
    const recovery = Math.min(OVERHAUL_RECOVERY_CAP, MACHINE_MAX_CONDITION - current);
    return Math.min(MACHINE_MAX_CONDITION, current + recovery);
  } else {
    return Math.max(0.0, current - degrade);
  }
};

/**
 * Calculates morale delta based on wage and understaffing percent.
 */
export const calculateMoraleDelta = (wageLevel: string, understaffingPct: number): number => {
  let delta = WAGE_MORALE_DELTA[wageLevel as keyof typeof WAGE_MORALE_DELTA] || 0.0;
  if (understaffingPct > 0) {
    delta -= understaffingPct * UNDERSTAFFING_MORALE_PENALTY;
  }
  return delta;
};

/**
 * Calculates projected sigma (variance).
 */
export const calculateProjectedSigma = (automation: string, skill: number, rndConsistency: number): number => {
  let sigma = BASE_SIGMA * (AUTOMATION_SIGMA_MULT[automation as keyof typeof AUTOMATION_SIGMA_MULT] || 1.0);
  const skillFactor = Math.max(0.1, Math.min(1.0, skill / 100.0));
  sigma *= (1.0 - skillFactor * SKILL_SIGMA_REDUCTION);
  sigma -= rndConsistency * RND_CONSISTENCY_BONUS;
  return Math.max(2.0, sigma);
};

/**
 * Calculates effective output grade for a collection of machines.
 */
export const calculateEffectiveGrade = (machines: any[], rndQuality: number): number => {
  if (!machines || machines.length === 0) return 0;
  let totalTp = 0;
  let gradeSum = 0.0;

  machines.forEach(m => {
    const cfg = MACHINE_TIERS[m.tier as keyof typeof MACHINE_TIERS] || MACHINE_TIERS.standard;
    const factor = Math.pow(m.condition / MACHINE_MAX_CONDITION, CONDITION_GRADE_EXPONENT);
    gradeSum += cfg.throughput * cfg.grade * factor;
    totalTp += cfg.throughput;
  });

  const base = totalTp > 0 ? gradeSum / totalTp : 0.0;
  return base + rndQuality * RND_QUALITY_BONUS;
};
