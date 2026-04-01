import { create } from "zustand";
import { getProduction, patchProduction } from "../api/api";
import type {
  AutomationLevel,
  ComponentType,
  MaintenanceLevel,
  RndFocus,
  WageLevel,
} from "../types/game";

type ComponentDecision = {
  maintenance: MaintenanceLevel;
  rnd_invest: { focus: RndFocus; levels: number } | null;
};

interface ProductionState {
  selectedComponent: ComponentType;
  componentDecisions: Record<ComponentType, ComponentDecision>;
  wageLevel: WageLevel;
  targetHeadcount: number;
  upgradeAutomation: AutomationLevel;
  lastSavedAt: string;
  setComponent: (c: ComponentType) => void;
  setMaintenance: (c: ComponentType, m: MaintenanceLevel) => void;
  setRnd: (c: ComponentType, levels: number, focus: RndFocus) => void;
  setWage: (w: WageLevel) => void;
  setHeadcount: (n: number) => void;
  setAutomation: (a: AutomationLevel) => void;
  hydrate: () => Promise<void>;
  submit: () => Promise<void>;
}

const defaults = (): Record<ComponentType, ComponentDecision> => ({
  airframe: { maintenance: "none", rnd_invest: null },
  propulsion: { maintenance: "none", rnd_invest: null },
  avionics: { maintenance: "none", rnd_invest: null },
  fire_suppression: { maintenance: "none", rnd_invest: null },
  sensing_safety: { maintenance: "none", rnd_invest: null },
  battery: { maintenance: "none", rnd_invest: null },
});

export const useProductionStore = create<ProductionState>((set, get) => ({
  selectedComponent: "airframe",
  componentDecisions: defaults(),
  wageLevel: "market",
  targetHeadcount: 50,
  upgradeAutomation: "manual",
  lastSavedAt: "",
  setComponent: (c) => set({ selectedComponent: c }),
  setMaintenance: (c, m) =>
    set((s) => ({ componentDecisions: { ...s.componentDecisions, [c]: { ...s.componentDecisions[c], maintenance: m } } })),
  setRnd: (c, levels, focus) =>
    set((s) => ({
      componentDecisions: {
        ...s.componentDecisions,
        [c]: { ...s.componentDecisions[c], rnd_invest: levels > 0 ? { levels, focus } : null },
      },
    })),
  setWage: (w) => set({ wageLevel: w }),
  setHeadcount: (n) => set({ targetHeadcount: n }),
  setAutomation: (a) => set({ upgradeAutomation: a }),
  hydrate: async () => {
    const data = await getProduction();
    const current = defaults();
    const decisions = data.decisions as Record<string, unknown>;
    for (const key of Object.keys(current) as ComponentType[]) {
      const maybe = decisions[key] as Partial<ComponentDecision> | undefined;
      if (maybe) {
        current[key] = {
          maintenance: (maybe.maintenance as MaintenanceLevel) ?? "none",
          rnd_invest: (maybe.rnd_invest as ComponentDecision["rnd_invest"]) ?? null,
        };
      }
    }
    set({
      componentDecisions: current,
      wageLevel: (decisions.wage_level as WageLevel) ?? "market",
      targetHeadcount: (decisions.target_headcount as number) ?? 50,
      upgradeAutomation: (decisions.upgrade_automation as AutomationLevel) ?? "manual",
    });
  },
  submit: async () => {
    await patchProduction({
      component_decisions: get().componentDecisions,
      wage_level: get().wageLevel,
      target_headcount: get().targetHeadcount,
      upgrade_automation: get().upgradeAutomation,
    });
    set({ lastSavedAt: new Date().toLocaleTimeString() });
  },
}));
