import { create } from 'zustand';
import type { ComponentType, Source, ProcurementDecision, TransportOut, CostProjectionOut } from '../types';
import { teamApi } from '../api';

let projectionTimeout: ReturnType<typeof setTimeout>;

const DEFAULT_DECISION: ProcurementDecision = {
  source_id: 1,
  quantity: 0,
  transport: 'road',
};

interface ProcurementState {
  decisions: Record<ComponentType, ProcurementDecision>;
  initialDecisions: Record<ComponentType, ProcurementDecision>;
  sources: Source[];
  sourcesByComponent: Record<string, Source[]>;
  selectedComponent: ComponentType;

  transports: Record<string, TransportOut>;
  isBuying: Record<ComponentType, boolean>;
  projectedCosts: CostProjectionOut | null;

  setComponent: (c: ComponentType) => void;
  setDecision: (component: ComponentType, field: keyof ProcurementDecision, value: any) => void;
  setIsBuying: (component: ComponentType, val: boolean) => void;
  fetchSources: () => Promise<void>;
  fetchTransports: () => Promise<void>;
  fetchProjectedCosts: () => void;
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
  sourcesByComponent: {},
  selectedComponent: 'airframe',
  transports: {},
  isBuying: {
    airframe: false,
    propulsion: false,
    avionics: false,
    fire_suppression: false,
    sensing_safety: false,
    battery: false,
  },
  projectedCosts: null,

  setComponent: (c) => set({ selectedComponent: c }),

  setIsBuying: (component, val) => {
    set((state) => {
      const currentComp = state.decisions[component];
      const sources = state.sourcesByComponent[component] || [];
      let newQuantity = currentComp.quantity;
      let newSourceId = currentComp.source_id;

      if (!val) {
          newQuantity = 0;
          if (sources.length > 0) newSourceId = sources[0].id;
      } else {
          if (newQuantity === 0) {
              const src = sources.find(s => s.id === newSourceId) || sources[0];
              if (src) {
                  newSourceId = src.id;
                  newQuantity = src.min_order;
              }
          }
      }

      return {
        isBuying: { ...state.isBuying, [component]: val },
        decisions: {
          ...state.decisions,
          [component]: { ...currentComp, quantity: newQuantity, source_id: newSourceId }
        }
      };
    });
    get().fetchProjectedCosts();
  },

  setDecision: (component, field, value) => {
    set((state) => ({
      decisions: {
        ...state.decisions,
        [component]: {
          ...state.decisions[component],
          [field]: value,
        },
      },
    }));
    get().fetchProjectedCosts();
  },

  fetchProjectedCosts: () => {
    clearTimeout(projectionTimeout);
    const { decisions } = get();
    projectionTimeout = setTimeout(async () => {
        try {
            const res = await teamApi.projectProcurementCosts(decisions);
            set({ projectedCosts: res });
        } catch(e) {
            console.error(e);
        }
    }, 300);
  },

  fetchSources: async () => {
    try {
      const sources = await teamApi.getSources();
      const grouped: Record<string, Source[]> = {};
      sources.forEach(src => {
        if (!grouped[src.component]) {
          grouped[src.component] = [];
        }
        grouped[src.component].push(src);
      });
      set({ sources, sourcesByComponent: grouped });
    } catch (err) {
      console.error("Failed to load sources", err);
    }
  },

  fetchTransports: async () => {
    try {
      const transports = await teamApi.getTransports();
      set({ transports });
    } catch (err) {
      console.error("Failed to load transports", err);
    }
  },

  fetchExistingDecisions: async () => {
    try {
      const data = await teamApi.getProcurement();
      if (data && data.decisions) {
        if (Object.keys(data.decisions).length > 0) {
          const merged = { ...get().decisions };
          const newIsBuying = { ...get().isBuying };
          (Object.keys(data.decisions) as ComponentType[]).forEach(comp => {
            if (data.decisions[comp]) {
              merged[comp] = { ...merged[comp], ...data.decisions[comp] };
              newIsBuying[comp] = merged[comp].quantity > 0;
            }
          });
          set({ decisions: merged, initialDecisions: merged, isBuying: newIsBuying });
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
    set({ initialDecisions: JSON.parse(JSON.stringify(decisions)) });
  },
}));
