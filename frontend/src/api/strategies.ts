import { api } from "./client";
import type { Strategy, StrategyCreate } from "@/types";

export async function getStrategies(): Promise<Strategy[]> {
  const response = await api.get<Strategy[]>("/strategies");
  return response.data;
}

export async function getStrategy(id: string): Promise<Strategy> {
  const response = await api.get<Strategy>(`/strategies/${id}`);
  return response.data;
}

export async function createStrategy(data: StrategyCreate): Promise<Strategy> {
  const response = await api.post<Strategy>("/strategies", data);
  return response.data;
}

export async function updateStrategy(
  id: string,
  data: StrategyCreate
): Promise<Strategy> {
  const response = await api.put<Strategy>(`/strategies/${id}`, data);
  return response.data;
}

export async function deleteStrategy(id: string): Promise<void> {
  await api.delete(`/strategies/${id}`);
}
