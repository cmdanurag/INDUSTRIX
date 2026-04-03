import api from './client';
import type {
  GameStatusOut,
  InventoryOut,
  ProcurementMemoryOut,
  ProductionMemoryOut,
  LeaderboardOut,
  Source,
} from '../types';

export const teamApi = {
  login: async (teamId: number, pin: string) => {
    // ALWAYS succeed for testing
    return { team_id: teamId, team_name: `Team Alpha ${teamId}` };
  },
  
  status: async () => {
    return {
      game_name: "Mock Industrix Game",
      cycle_number: 1,
      phase: "procurement_open", // change this manually to test different phases
      game_active: true
    };
  },

  me: async () => {
    return {
      funds: 85000,
      brand_score: 55.2,
      brand_tier: "standard",
      drone_stock_total: 420,
      drone_stock: [5, 45, 300, 70], // index 0=reject, 1=sub, 2=std, 3=prem
      raw_stocks: { airframe: 100, propulsion: 150, avionics: 80, fire_suppression: 200, sensing_safety: 90, battery: 110 },
      workforce_size: 150
    };
  },

  getSources: async (): Promise<Source[]> => {
    return [
      { id: 1, name: 'AeroStruc Global', quality_mean: 0.92, quality_sigma: 0.04, base_cost_per_unit: 450 },
      { id: 2, name: 'TitanForge LLC', quality_mean: 0.85, quality_sigma: 0.08, base_cost_per_unit: 300 },
      { id: 3, name: 'CheapParts Inc', quality_mean: 0.70, quality_sigma: 0.15, base_cost_per_unit: 180 },
    ];
  },

  getProcurement: async () => {
    return { decisions: {} };
  },

  patchProcurement: async (data: Record<string, any>) => {
    return { status: "success" };
  },

  getProduction: async () => {
    return { 
      component_decisions: {}, 
      wage_level: "market", 
      target_headcount: 100, 
      upgrade_automation: "manual" 
    };
  },

  patchProduction: async (data: any) => {
    return { status: "success" };
  },

  patchSales: async (data: any) => {
    return { status: "success" };
  },

  getLeaderboard: async () => {
    return {
      cycle_number: 1,
      is_final: false,
      rows: [
        { rank: 1, team_name: "Team Alpha 01", composite_score: 88.5, closing_funds: 92000, cumulative_profit: 12000, brand_score: 55.2, quality_avg: 0.88, inventory_penalty: 500 },
        { rank: 2, team_name: "Beta Builders", composite_score: 75.3, closing_funds: 80000, cumulative_profit: -5000, brand_score: 42.1, quality_avg: 0.76, inventory_penalty: 1200 }
      ]
    };
  },
};

