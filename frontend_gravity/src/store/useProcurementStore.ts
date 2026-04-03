import { create } from 'zustand';
import type { ComponentType, Source, ComponentDecision } from '../types';
import { teamApi } from '../api';

const DEFAULT_DECISION: ComponentDecision = {
  source_id: 1,
  quantity: 0,
  transport: 'road',
};

interface ProcurementState {
  decisions: Record<ComponentType, ComponentDecision>;
  initialDecisions: Record<ComponentType, ComponentDecision>;
  sources: Source[];
  selectedComponent: ComponentType;

  setComponent: (c: ComponentType) => void;
  setDecision: (component: ComponentType, field: keyof ComponentDecision, value: any) => void;
  fetchSources: () => Promise<void>;
  fetchExistingDecisions: () => Promise<void>;
  submitDecisions: () => Promise<void>;
}

export const useProcurementStore = create<ProcurementState>((set, get) => ({
  decisions: {
    airframe: { ...DEFAULT_DECISION },
    propulsion: { ...DEFAULT_DECISION },
    avionics: { ...DEFAULT_DECISION },
    fire_suppression: { ...DEFAULT_DECISION },
    sensing_safety: { ...DEFAULT_DECISION },
    battery: { ...DEFAULT_DECISION },
  },
  initialDecisions: {
    airframe: { ...DEFAULT_DECISION },
    propulsion: { ...DEFAULT_DECISION },
    avionics: { ...DEFAULT_DECISION },
    fire_suppression: { ...DEFAULT_DECISION },
    sensing_safety: { ...DEFAULT_DECISION },
    battery: { ...DEFAULT_DECISION },
  },
  sources: [],
  selectedComponent: 'airframe',

  setComponent: (c) => set({ selectedComponent: c }),

  setDecision: (component, field, value) => set((state) => ({
    decisions: {
      ...state.decisions,
      [component]: {
        ...state.decisions[component],
        [field]: value,
      },
    },
  })),

  fetchSources: async () => {
    const sources = await teamApi.getSources();
    set({ sources });
  },

  fetchExistingDecisions: async () => {
    try {
      const data = await teamApi.getProcurement();
      if (data && data.decisions) {
        // Only override if the backend returned an object
        if (Object.keys(data.decisions).length > 0) {
          const merged = { ...get().decisions, ...data.decisions };
          set({ decisions: merged, initialDecisions: merged });
        }
      }
    } catch (err) {
      console.error("No existing procurement decisions found", err);
    }
  },

  submitDecisions: async () => {
    const { decisions, initialDecisions } = get();
    const changed: Record<string, any> = {};
    (Object.keys(decisions) as ComponentType[]).forEach((comp) => {
      const next = decisions[comp];
      const prev = initialDecisions[comp];
      if (JSON.stringify(next) !== JSON.stringify(prev)) {
        changed[comp] = next;
      }
    });
    if (Object.keys(changed).length === 0) return;
    await teamApi.patchProcurement(changed);
    set({ initialDecisions: { ...decisions } });
  },
}));
