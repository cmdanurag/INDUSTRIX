import { create } from "zustand";
import { getProcurement, patchProcurement } from "../api/api";
import { COMPONENTS, type ComponentType, type TransportMode } from "../types/game";

type Decision = { source_id: number; quantity: number; transport: TransportMode };

interface ProcurementState {
  selectedComponent: ComponentType;
  decisions: Record<ComponentType, Decision>;
  lastSavedAt: string;
  setComponent: (c: ComponentType) => void;
  setDecision: (c: ComponentType, patch: Partial<Decision>) => void;
  hydrate: () => Promise<void>;
  submit: () => Promise<void>;
}

const defaultDecision: Decision = { source_id: 1, quantity: 0, transport: "road" };

const buildDefaults = (): Record<ComponentType, Decision> => ({
  airframe: { ...defaultDecision },
  propulsion: { ...defaultDecision },
  avionics: { ...defaultDecision },
  fire_suppression: { ...defaultDecision },
  sensing_safety: { ...defaultDecision },
  battery: { ...defaultDecision },
});

export const useProcurementStore = create<ProcurementState>((set, get) => ({
  selectedComponent: "airframe",
  decisions: buildDefaults(),
  lastSavedAt: "",
  setComponent: (c) => set({ selectedComponent: c }),
  setDecision: (c, patch) => {
    const curr = get().decisions;
    set({ decisions: { ...curr, [c]: { ...curr[c], ...patch } } });
  },
  hydrate: async () => {
    const data = await getProcurement();
    const next = buildDefaults();
    for (const comp of COMPONENTS) {
      const val = data.decisions[comp];
      if (val) next[comp] = val;
    }
    set({ decisions: next });
  },
  submit: async () => {
    await patchProcurement(get().decisions);
    set({ lastSavedAt: new Date().toLocaleTimeString() });
  },
}));
