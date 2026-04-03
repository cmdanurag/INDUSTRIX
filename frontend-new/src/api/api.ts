import axios from "axios";
import type {
  InventoryOut,
  LeaderboardOut,
  OkResponse,
  PhaseStatusResponse,
  ProcurementMemoryOut,
  ProductionMemoryOut,
  ProductionPatchBody,
  SalesMemoryOut,
  TeamLoginResponse,
} from "../types/api";
import type { ComponentType, SalesTier } from "../types/game";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

export const setTeamHeaders = (teamId: number | null, pin: string | null) => {
  if (teamId && pin) {
    api.defaults.headers.common["x-team-id"] = String(teamId);
    api.defaults.headers.common["x-team-pin"] = pin;
  } else {
    delete api.defaults.headers.common["x-team-id"];
    delete api.defaults.headers.common["x-team-pin"];
  }
};

export const teamLogin = async (): Promise<TeamLoginResponse> => {
  const { data } = await api.post<TeamLoginResponse>("/team/login");
  return data;
};

export const getStatus = async (): Promise<PhaseStatusResponse> => {
  const { data } = await api.get<PhaseStatusResponse>("/team/status");
  return data;
};

export const getInventory = async (): Promise<InventoryOut> => {
  const { data } = await api.get<InventoryOut>("/team/me");
  return data;
};

export const getProcurement = async (): Promise<ProcurementMemoryOut> => {
  const { data } = await api.get<ProcurementMemoryOut>("/team/procurement");
  return data;
};

export const patchProcurement = async (decisions: Record<ComponentType, { source_id: number; quantity: number; transport: "road" | "rail" | "air" }>): Promise<OkResponse> => {
  const { data } = await api.patch<OkResponse>("/team/procurement", { decisions });
  return data;
};

export const getProduction = async (): Promise<ProductionMemoryOut> => {
  const { data } = await api.get<ProductionMemoryOut>("/team/production");
  return data;
};

export const patchProduction = async (body: ProductionPatchBody): Promise<OkResponse> => {
  const { data } = await api.patch<OkResponse>("/team/production", body);
  return data;
};

export const getSales = async (): Promise<SalesMemoryOut> => {
  const { data } = await api.get<SalesMemoryOut>("/team/sales");
  return data;
};

export const patchSales = async (decisions: Partial<Record<SalesTier, { action: string; price_override?: number | null }>>): Promise<OkResponse> => {
  const { data } = await api.patch<OkResponse>("/team/sales", { decisions });
  return data;
};

export const getLeaderboard = async (): Promise<LeaderboardOut> => {
  const { data } = await api.get<LeaderboardOut>("/team/leaderboard");
  return data;
};

export default api;
