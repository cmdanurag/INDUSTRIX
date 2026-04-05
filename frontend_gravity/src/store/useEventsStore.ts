import { create } from 'zustand';
import { teamApi } from '../api';
import type { ProcurementSummary, ProductionSummary, SalesSummary } from '../types';

interface EventsState {
  procurement: ProcurementSummary | null;
  production: ProductionSummary | null;
  sales: SalesSummary | null;
  loadingProcurement: boolean;
  loadingProduction: boolean;
  loadingSales: boolean;
  fetchAll: (phase: string) => Promise<void>;
}

export const useEventsStore = create<EventsState>((set) => ({
  procurement: null,
  production: null,
  sales: null,
  loadingProcurement: false,
  loadingProduction: false,
  loadingSales: false,

  fetchAll: async (phase: string) => {
    const canSeeProcurement = ['production_open', 'sales_open', 'backroom', 'game_over'].includes(phase);
    const canSeeProduction  = ['sales_open', 'backroom', 'game_over'].includes(phase);
    const canSeeSales       = ['backroom', 'game_over'].includes(phase);

    if (canSeeProcurement) {
      set({ loadingProcurement: true });
      try {
        const data = await teamApi.getProcurementSummary();
        set({ procurement: data as ProcurementSummary });
      } catch {
        set({ procurement: null });
      } finally {
        set({ loadingProcurement: false });
      }
    }

    if (canSeeProduction) {
      set({ loadingProduction: true });
      try {
        const data = await teamApi.getProductionSummary();
        set({ production: data as ProductionSummary });
      } catch {
        set({ production: null });
      } finally {
        set({ loadingProduction: false });
      }
    }

    if (canSeeSales) {
      set({ loadingSales: true });
      try {
        const data = await teamApi.getSalesSummary();
        set({ sales: data as SalesSummary });
      } catch {
        set({ sales: null });
      } finally {
        set({ loadingSales: false });
      }
    }
  },
}));
