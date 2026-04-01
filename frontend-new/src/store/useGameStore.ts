import { create } from "zustand";
import { getStatus, setTeamHeaders, teamLogin } from "../api/api";
import type { GamePhase } from "../types/game";

interface GameState {
  teamId: number | null;
  teamName: string;
  pin: string;
  isLoggedIn: boolean;
  gameName: string;
  cycleNumber: number;
  phase: GamePhase;
  gameActive: boolean;
  lastError: string;
  setCredentials: (teamId: number, pin: string) => Promise<void>;
  logout: () => void;
  pollStatus: () => Promise<void>;
}

export const useGameStore = create<GameState>((set, get) => ({
  teamId: null,
  teamName: "",
  pin: "",
  isLoggedIn: false,
  gameName: "",
  cycleNumber: 0,
  phase: "waiting_for_first_cycle",
  gameActive: false,
  lastError: "",
  setCredentials: async (teamId, pin) => {
    setTeamHeaders(teamId, pin);
    localStorage.setItem("teamId", String(teamId));
    localStorage.setItem("teamPin", pin);
    try {
      const login = await teamLogin();
      set({
        teamId,
        pin,
        isLoggedIn: true,
        teamName: login.team_name,
        lastError: "",
      });
      await get().pollStatus();
    } catch (e: unknown) {
      set({ lastError: "Login failed", isLoggedIn: false });
      throw e;
    }
  },
  logout: () => {
    setTeamHeaders(null, null);
    localStorage.removeItem("teamId");
    localStorage.removeItem("teamPin");
    set({
      teamId: null,
      teamName: "",
      pin: "",
      isLoggedIn: false,
      gameName: "",
      cycleNumber: 0,
      phase: "waiting_for_first_cycle",
      gameActive: false,
    });
  },
  pollStatus: async () => {
    const status = await getStatus();
    set({
      gameName: status.game_name,
      cycleNumber: status.cycle_number,
      phase: status.phase,
      gameActive: status.game_active,
    });
  },
}));
