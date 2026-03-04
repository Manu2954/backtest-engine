import axios from "axios";
import type { BacktestCreate, BacktestOut, StrategyCreate, StrategyOut, TradeLog } from "../types";

const baseURL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== "undefined" && window.location?.hostname
    ? `http://${window.location.hostname}:8080`
    : "http://127.0.0.1:8080");

export const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

export async function createStrategy(payload: StrategyCreate): Promise<StrategyOut> {
  const { data } = await api.post<StrategyOut>("/strategies", payload);
  return data;
}

export async function getStrategy(id: string): Promise<StrategyOut> {
  const { data } = await api.get<StrategyOut>(`/strategies/${id}`);
  return data;
}

export async function updateStrategy(id: string, payload: StrategyCreate): Promise<StrategyOut> {
  const { data } = await api.put<StrategyOut>(`/strategies/${id}` , payload);
  return data;
}

export async function deleteStrategy(id: string): Promise<void> {
  await api.delete(`/strategies/${id}`);
}

export async function createBacktest(payload: BacktestCreate): Promise<BacktestOut> {
  const { data } = await api.post<BacktestOut>("/backtests", payload);
  return data;
}

export async function getBacktest(id: string): Promise<BacktestOut> {
  const { data } = await api.get<BacktestOut>(`/backtests/${id}`);
  return data;
}

export async function getBacktestTrades(
  id: string,
  limit = 100,
  offset = 0
): Promise<TradeLog[]> {
  const { data } = await api.get<TradeLog[]>(`/backtests/${id}/trades`, {
    params: { limit, offset },
  });
  return data;
}

export async function validateTicker(ticker: string, assetClass: string): Promise<boolean> {
  const { data } = await api.get<{ valid: boolean }>("/tickers/validate", {
    params: { ticker, asset_class: assetClass },
  });
  return data.valid;
}
