import type {
  AutomationLevel,
  ComponentType,
  GamePhase,
  MaintenanceLevel,
  RndFocus,
  SalesAction,
  SalesTier,
  TransportMode,
  WageLevel,
} from "./game";

export interface TeamLoginResponse {
  team_id: number;
  team_name: string;
  message?: string;
}

export interface PhaseStatusResponse {
  game_name: string;
  cycle_number: number;
  phase: GamePhase;
  game_active: boolean;
}

export interface InventoryOut {
  funds: number;
  brand_score: number;
  brand_tier: string;
  drone_stock_total: number;
  workforce_size: number;
  skill_level: number;
  morale: number;
  automation_level: string;
  has_gov_loan: boolean;
}

export interface ProcurementDecision {
  source_id: number;
  quantity: number;
  transport: TransportMode;
}

export interface ProcurementMemoryOut {
  decisions: Partial<Record<ComponentType, ProcurementDecision>>;
}

export interface ProductionComponentDecision {
  maintenance?: MaintenanceLevel | "overhaul";
  rnd_invest?: { focus: RndFocus; levels: number } | null;
  upgrade_to?: "basic" | "standard" | "industrial" | "precision" | null;
}

export interface ProductionMemoryOut {
  decisions: Record<string, unknown>;
}

export interface SalesTierDecision {
  action: SalesAction;
  price_override?: number | null;
}

export interface SalesMemoryOut {
  decisions: Partial<Record<SalesTier, SalesTierDecision>>;
}

export interface LeaderboardRow {
  rank: number;
  team_name: string;
  composite_score: number;
  closing_funds: number;
  cumulative_profit: number;
  brand_score: number;
  quality_avg: number;
  inventory_penalty: number;
}

export interface LeaderboardOut {
  cycle_number: number;
  is_final: boolean;
  rows: LeaderboardRow[];
}

export interface OkResponse {
  ok: boolean;
  message: string;
}

export interface ProductionPatchBody {
  component_decisions: Partial<Record<ComponentType, ProductionComponentDecision>>;
  wage_level?: WageLevel;
  target_headcount?: number;
  upgrade_automation?: AutomationLevel;
}
