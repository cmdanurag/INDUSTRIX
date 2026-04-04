import api from './client';
import type {
  GameStatusOut,
  InventoryOut,
  ProcurementMemoryOut,
  ProductionMemoryOut,
  LeaderboardOut,
  Source,
} from '../types';

// Thin wrapper around backend endpoints. No hardcoded data.
export const teamApi = {
  // Team auth is lightweight; backend may not strictly validate here.
  login: async (teamId: number, pin: string) => {
    // Persist locally for interceptors; backend login optional
    // match EXACT structure expected by interceptor
  const authData = {
    state: {
      teamId: teamId,
      pin: pin,
    },
  };

  localStorage.setItem("industrix-auth", JSON.stringify(authData));

  return { team_id: teamId, team_name: `Team ${teamId}` };
  },

  // Public status endpoint (no auth headers required)
  status: async (): Promise<GameStatusOut> => {
    const { data } = await api.get<GameStatusOut>('/team/status', {
      // Ensure no auth headers are forced (interceptor adds only if present)
    });
    return data;
  },

  // Team inventory/me
  me: async (): Promise<InventoryOut> => {
    const { data } = await api.get<InventoryOut>('/team/me');
    return data;
  },

  // Sources catalog — if not available on backend, this should be wired when provided.
  // Fallback to procurement GET if sources are embedded elsewhere.
  getSources: async (component?: string): Promise<Source[]> => {
    const params = component ? { component } : undefined;
    const { data } = await api.get<Source[]>('/team/procurement/sources', { params });
    return data;
  },

  // Procurement memory
  getProcurement: async (): Promise<ProcurementMemoryOut> => {
    const { data } = await api.get<ProcurementMemoryOut>('/team/procurement');
    return data;
  },

  // PATCH semantics: caller should pass only changed fields
  patchProcurement: async (decisions: Record<string, any>) => {
    const { data } = await api.patch('/team/procurement', { decisions });
    return data;
  },

  // Production memory
  getProduction: async (): Promise<ProductionMemoryOut> => {
    const { data } = await api.get<ProductionMemoryOut>('/team/production');
    return data;
  },

  patchProduction: async (payload: any) => {
    const { data } = await api.patch('/team/production', payload);
    return data;
  },

  // Sales memory and updates
  getSales: async () => {
    const { data } = await api.get('/team/sales');
    return data;
  },

  patchSales: async (payload: any) => {
    const { data } = await api.patch('/team/sales', payload);
    return data;
  },

  // Public leaderboard (works only during backroom/game_over)
  getLeaderboard: async (): Promise<LeaderboardOut> => {
    const { data } = await api.get<LeaderboardOut>('/team/leaderboard');
    return data;
  },
};

