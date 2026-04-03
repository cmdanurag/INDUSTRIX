import { create } from 'zustand';
import type { ComponentType } from '../types';
import { teamApi } from '../api';

interface ProductionState {
  componentDecisions: Record<ComponentType, {
    maintenance: 'none' | 'basic' | 'full';
    rnd_invest: { focus: string; levels: number } | null;
  }>;
  wageLevel: 'below_market' | 'market' | 'above_market';
  targetHeadcount: number;
  upgradeAutomation: 'manual' | 'semi_auto' | 'full_auto';
  selectedComponent: ComponentType;

  setComponent: (c: ComponentType) => void;
  setMaintenance: (comp: ComponentType, level: 'none' | 'basic' | 'full') => void;
  setRndInvest: (comp: ComponentType, focus: string, levels: number) => void;
  clearRndInvest: (comp: ComponentType) => void;
  setWageLevel: (level: 'below_market' | 'market' | 'above_market') => void;
  setHeadcount: (count: number) => void;
  setAutomation: (level: 'manual' | 'semi_auto' | 'full_auto') => void;
  fetchExistingDecisions: () => Promise<void>;
  submitDecisions: () => Promise<void>;
}

const DEFAULT_COMP = { maintenance: 'none' as const, rnd_invest: null };

export const useProductionStore = create<ProductionState>((set, get) => ({
  componentDecisions: {
    airframe: { ...DEFAULT_COMP },
    propulsion: { ...DEFAULT_COMP },
    avionics: { ...DEFAULT_COMP },
    fire_suppression: { ...DEFAULT_COMP },
    sensing_safety: { ...DEFAULT_COMP },
    battery: { ...DEFAULT_COMP },
  },
  wageLevel: 'market',
  targetHeadcount: 0,
  upgradeAutomation: 'manual',
  selectedComponent: 'airframe',

  setComponent: (c) => set({ selectedComponent: c }),

  setMaintenance: (comp, level) => set((s) => ({
    componentDecisions: { ...s.componentDecisions, [comp]: { ...s.componentDecisions[comp], maintenance: level } }
  })),

  setRndInvest: (comp, focus, levels) => set((s) => ({
    componentDecisions: { ...s.componentDecisions, [comp]: { ...s.componentDecisions[comp], rnd_invest: { focus, levels } } }
  })),

  clearRndInvest: (comp) => set((s) => ({
    componentDecisions: { ...s.componentDecisions, [comp]: { ...s.componentDecisions[comp], rnd_invest: null } }
  })),

  setWageLevel: (l) => set({ wageLevel: l }),
  setHeadcount: (c) => set({ targetHeadcount: c }),
  setAutomation: (l) => set({ upgradeAutomation: l }),

  fetchExistingDecisions: async () => {
    try {
      const data = await teamApi.getProduction();
      if (data) {
        set({
          componentDecisions: data.component_decisions ? { ...get().componentDecisions, ...data.component_decisions } : get().componentDecisions,
          wageLevel: data.wage_level || 'market',
          targetHeadcount: data.target_headcount || 0,
          upgradeAutomation: data.upgrade_automation || 'manual',
        });
      }
    } catch (err) {
      console.error("No existing production decisions found", err);
    }
  },

  submitDecisions: async () => {
    await teamApi.patchProduction({
      component_decisions: get().componentDecisions,
      wage_level: get().wageLevel,
      target_headcount: get().targetHeadcount,
      upgrade_automation: get().upgradeAutomation,
    });
  },
}));
