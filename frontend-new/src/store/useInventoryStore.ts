import { create } from "zustand";
import { getInventory, patchSales } from "../api/api";

interface InventoryState {
  funds: number;
  brandScore: number;
  brandTier: string;
  droneStockTotal: number;
  workforceSize: number;
  skillLevel: number;
  morale: number;
  automationLevel: string;
  hasGovLoan: boolean;
  rawMaterialStocks: Record<string, number>;
  droneBreakdown: { reject: number; substandard: number; standard: number; premium: number };
  fetchInventory: () => Promise<void>;
  scrapRejectUnits: () => Promise<void>;
}

export const useInventoryStore = create<InventoryState>((set) => ({
  funds: 0,
  brandScore: 0,
  brandTier: "fair",
  droneStockTotal: 0,
  workforceSize: 0,
  skillLevel: 0,
  morale: 0,
  automationLevel: "manual",
  hasGovLoan: false,
  rawMaterialStocks: {
    airframe: 0,
    propulsion: 0,
    avionics: 0,
    fire_suppression: 0,
    sensing_safety: 0,
    battery: 0,
  },
  droneBreakdown: { reject: 0, substandard: 0, standard: 0, premium: 0 },
  fetchInventory: async () => {
    const inv = await getInventory();
    set({
      funds: inv.funds,
      brandScore: inv.brand_score,
      brandTier: inv.brand_tier,
      droneStockTotal: inv.drone_stock_total,
      workforceSize: inv.workforce_size,
      skillLevel: inv.skill_level,
      morale: inv.morale,
      automationLevel: inv.automation_level,
      hasGovLoan: inv.has_gov_loan,
    });
  },
  scrapRejectUnits: async () => {
    await patchSales({ reject: { action: "scrap" } });
  },
}));
