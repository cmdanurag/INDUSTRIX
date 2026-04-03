import { create } from 'zustand';
import { teamApi } from '../api';
import type { ComponentType } from '../types';

interface InventoryState {
  funds: number;
  brandScore: number;
  brandTier: string;
  droneStockTotal: number;
  droneBreakdown: {
    reject: number;
    substandard: number;
    standard: number;
    premium: number;
  };
  rawMaterialStocks: Record<ComponentType, number>;
  workforceSize: number;

  fetchInventory: () => Promise<void>;
  scrapRejectUnits: () => Promise<void>;
}

export const useInventoryStore = create<InventoryState>((set) => ({
  funds: 0,
  brandScore: 0,
  brandTier: 'fair',
  droneStockTotal: 0,
  droneBreakdown: { reject: 0, substandard: 0, standard: 0, premium: 0 },
  rawMaterialStocks: {
    airframe: 0, propulsion: 0, avionics: 0, fire_suppression: 0, sensing_safety: 0, battery: 0
  },
  workforceSize: 0,

  fetchInventory: async () => {
    try {
      const data = await teamApi.me();
      if (data) {
        set({
          funds: data.funds || 0,
          brandScore: data.brand_score || 0,
          brandTier: data.brand_tier || 'fair',
          droneStockTotal: data.drone_stock_total || 0,
          droneBreakdown: {
            reject: Array.isArray(data.drone_stock) ? data.drone_stock[0] : 0,
            substandard: Array.isArray(data.drone_stock) ? data.drone_stock[1] : 0,
            standard: Array.isArray(data.drone_stock) ? data.drone_stock[2] : 0,
            premium: Array.isArray(data.drone_stock) ? data.drone_stock[3] : 0,
          },
          rawMaterialStocks: data.raw_stocks || { airframe: 0, propulsion: 0, avionics: 0, fire_suppression: 0, sensing_safety: 0, battery: 0 },
          workforceSize: data.workforce_size || 0,
        });
      }
    } catch (err) {
      console.error("Failed to load inventory", err);
    }
  },

  scrapRejectUnits: async () => {
    try {
      await teamApi.patchSales({
        decisions: {
          reject: { action: 'scrap' }
        }
      });
      // Optionally trigger re-fetch of inventory
    } catch (err) {
      console.error("Failed to scrap rejects", err);
    }
  },
}));
