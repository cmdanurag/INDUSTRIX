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
          set({ decisions: { ...get().decisions, ...data.decisions } });
        }
      }
    } catch (err) {
      console.error("No existing procurement decisions found", err);
    }
  },

  submitDecisions: async () => {
    await teamApi.patchProcurement(get().decisions);
  },
}));
