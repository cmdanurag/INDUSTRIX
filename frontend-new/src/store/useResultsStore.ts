import { create } from "zustand";
import { getLeaderboard } from "../api/api";
import type { LeaderboardRow } from "../types/api";

interface ResultsState {
  cycleNumber: number;
  isFinal: boolean;
  rows: LeaderboardRow[];
  fetchLeaderboard: () => Promise<void>;
}

export const useResultsStore = create<ResultsState>((set) => ({
  cycleNumber: 0,
  isFinal: false,
  rows: [],
  fetchLeaderboard: async () => {
    const data = await getLeaderboard();
    set({ cycleNumber: data.cycle_number, isFinal: data.is_final, rows: data.rows });
  },
}));
