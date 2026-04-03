import { create } from 'zustand';
import type { ComponentType } from '../types';
import { teamApi } from '../api';

interface ProductionState {
  componentDecisions: Record<ComponentType, {
    maintenance: 'none' | 'basic' | 'full' | 'overhaul';
    rnd_invest: { focus: string; levels: number } | null;
    upgrade_to?: 'basic' | 'standard' | 'industrial' | 'precision' | null;
    machine_condition?: number;
    machine_tier?: 'basic' | 'standard' | 'industrial' | 'precision';
  }>;
  wageLevel: 'below_market' | 'market' | 'above_market';
  targetHeadcount: number;
  upgradeAutomation: 'manual' | 'semi_auto' | 'full_auto';
  selectedComponent: ComponentType;
  initialState: {
    componentDecisions: Record<ComponentType, {
      maintenance: 'none' | 'basic' | 'full' | 'overhaul';
      rnd_invest: { focus: string; levels: number } | null;
      upgrade_to?: 'basic' | 'standard' | 'industrial' | 'precision' | null;
      machine_condition?: number;
      machine_tier?: 'basic' | 'standard' | 'industrial' | 'precision';
    }>;
    wageLevel: 'below_market' | 'market' | 'above_market';
    targetHeadcount: number;
    upgradeAutomation: 'manual' | 'semi_auto' | 'full_auto';
  };

  setComponent: (c: ComponentType) => void;
  setMaintenance: (comp: ComponentType, level: 'none' | 'basic' | 'full' | 'overhaul') => void;
  setRndInvest: (comp: ComponentType, focus: string, levels: number) => void;
  setUpgradeTo: (comp: ComponentType, tier: 'basic' | 'standard' | 'industrial' | 'precision' | null) => void;
  clearRndInvest: (comp: ComponentType) => void;
  setWageLevel: (level: 'below_market' | 'market' | 'above_market') => void;
  setHeadcount: (count: number) => void;
  setAutomation: (level: 'manual' | 'semi_auto' | 'full_auto') => void;
  fetchExistingDecisions: () => Promise<void>;
  submitDecisions: () => Promise<void>;
}

const DEFAULT_COMP = { maintenance: 'none' as const, rnd_invest: null, upgrade_to: null };

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
  initialState: {
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
  },

  setComponent: (c) => set({ selectedComponent: c }),

  setMaintenance: (comp, level) => set((s) => ({
    componentDecisions: { ...s.componentDecisions, [comp]: { ...s.componentDecisions[comp], maintenance: level } }
  })),

  setRndInvest: (comp, focus, levels) => set((s) => ({
    componentDecisions: { ...s.componentDecisions, [comp]: { ...s.componentDecisions[comp], rnd_invest: { focus, levels } } }
  })),
  setUpgradeTo: (comp, tier) => set((s) => ({
    componentDecisions: { ...s.componentDecisions, [comp]: { ...s.componentDecisions[comp], upgrade_to: tier } }
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
        const nextComp = data.component_decisions ? { ...get().componentDecisions, ...data.component_decisions } : get().componentDecisions;
        const nextWage = data.wage_level || 'market';
        const nextHead = data.target_headcount || 0;
        const nextAuto = data.upgrade_automation || 'manual';
        set({
          componentDecisions: nextComp,
          wageLevel: nextWage,
          targetHeadcount: nextHead,
          upgradeAutomation: nextAuto,
          initialState: {
            componentDecisions: nextComp,
            wageLevel: nextWage,
            targetHeadcount: nextHead,
            upgradeAutomation: nextAuto,
          },
        });
      }
    } catch (err) {
      console.error("No existing production decisions found", err);
    }
  },

  submitDecisions: async () => {
    const { componentDecisions, wageLevel, targetHeadcount, upgradeAutomation, initialState } = get();
    const payload: any = {};
    const changedComponents: Record<string, any> = {};
    (Object.keys(componentDecisions) as ComponentType[]).forEach((comp) => {
      if (JSON.stringify(componentDecisions[comp]) !== JSON.stringify(initialState.componentDecisions[comp])) {
        changedComponents[comp] = componentDecisions[comp];
      }
    });
    if (Object.keys(changedComponents).length > 0) payload.component_decisions = changedComponents;
    if (wageLevel !== initialState.wageLevel) payload.wage_level = wageLevel;
    if (targetHeadcount !== initialState.targetHeadcount) payload.target_headcount = targetHeadcount;
    if (upgradeAutomation !== initialState.upgradeAutomation) payload.upgrade_automation = upgradeAutomation;
    if (Object.keys(payload).length === 0) return;
    await teamApi.patchProduction(payload);
    set({
      initialState: {
        componentDecisions: { ...componentDecisions },
        wageLevel,
        targetHeadcount,
        upgradeAutomation,
      },
    });
  },
}));
