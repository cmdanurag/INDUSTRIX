export type ComponentType =
  | 'airframe'
  | 'propulsion'
  | 'avionics'
  | 'fire_suppression'
  | 'sensing_safety'
  | 'battery';

export interface Source {
  id: number;
  component: string;
  name: string;
  quality_mean: number;
  quality_sigma: number;
  base_cost_per_unit: number;
  distance: number;
  min_order: number;
  max_order: number;
}

export interface InventoryOut {
  funds: number;
  brand_score: number;
  brand_tier: string;
  drone_stock_total: number;
  drone_stock: number[]; // Index 0: reject, 1: substandard, 2: standard, 3: premium
  raw_stocks?: Record<ComponentType, number>; // Needs to map correctly from wherever raw_stock exists
  workforce_size: number;
  produced_this_cycle?: number;
  carried_from_previous?: number;
  has_gov_loan?: boolean;
}

export interface ComponentDecision {
  source_id: number;
  quantity: number;
  transport: 'road' | 'rail' | 'air';
  maintenance?: 'none' | 'basic' | 'full' | 'overhaul';
  rnd_invest?: { focus: string; levels: number } | null;
  upgrade_to?: 'basic' | 'standard' | 'industrial' | 'precision' | null;
  machine_condition?: number;
  machine_tier?: 'basic' | 'standard' | 'industrial' | 'precision';
}

export interface ProcurementMemoryOut {
  decisions: Record<ComponentType, ComponentDecision>;
}

export interface ProductionMemoryOut {
  component_decisions: Record<
    ComponentType,
    {
      maintenance: 'none' | 'basic' | 'full' | 'overhaul';
      rnd_invest: { focus: string; levels: number } | null;
      upgrade_to?: 'basic' | 'standard' | 'industrial' | 'precision' | null;
      machine_condition?: number;
      machine_tier?: 'basic' | 'standard' | 'industrial' | 'precision';
    }
  >;
  wage_level: 'below_market' | 'market' | 'above_market';
  target_headcount: number;
  upgrade_automation: 'manual' | 'semi_auto' | 'full_auto';
}

export interface LeaderboardRow {
  team_id?: number;
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

export interface GameStatusOut {
  game_name: string;
  cycle_number: number;
  phase:
    | 'procurement_open'
    | 'production_open'
    | 'sales_open'
    | 'backroom'
    | 'game_over'
    | 'waiting_for_first_cycle'
    | 'no_active_game';
  game_active: boolean;
}
