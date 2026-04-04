import { create } from 'zustand';
import { teamApi } from '../api';

interface GameState {
  teamId: number | null;
  teamName: string;
  pin: string;
  isLoggedIn: boolean;

  gameName: string;
  cycleNumber: number;
  phase: string;
  gameActive: boolean;

  // Sync indicator support
  lastSyncTs: number | null;
  connectionOk: boolean;

  login: (teamId: number, pin: string) => Promise<void>;
  logout: () => void;
  pollStatus: () => Promise<void>;
}

export const useGameStore = create<GameState>((set) => {
  // Try to load auth from localStorage
  const saved = localStorage.getItem('industrix-auth');
  let initial = { teamId: null, teamName: '', pin: '', isLoggedIn: false };
  if (saved) {
    try {
      initial = JSON.parse(saved).state;
    } catch {}
  }

  return {
    ...initial,
    gameName: '',
    cycleNumber: 0,
    phase: '',
    gameActive: false,
    lastSyncTs: null,
    connectionOk: true,

    login: async (teamId: number, pin: string) => {
      const res = await teamApi.login(teamId, pin);
      const newState = {
        teamId,
        teamName: res.team_name || `Team ${teamId}`,
        pin,
        isLoggedIn: true,
      };
      set(newState);
      localStorage.setItem('industrix-auth', JSON.stringify({ state: newState }));
    },

    logout: () => {
      localStorage.removeItem('industrix-auth');
      set({ teamId: null, teamName: '', pin: '', isLoggedIn: false });
      // Navigation will be handled by the useEffect in SharedLayout
    },

    pollStatus: async () => {
      try {
        const status = await teamApi.status();
        set({
          gameName: status.game_name,
          cycleNumber: status.cycle_number,
          phase: status.phase,
          gameActive: status.game_active,
          lastSyncTs: Date.now(),
          connectionOk: true,
        });
      } catch (err) {
        console.error("Failed to poll status", err);
        set({ connectionOk: false });
      }
    },
  };
});