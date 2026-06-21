import { api } from "./client";
import type { Backtest, BacktestConfig, Trade } from "@/types";

export async function getBacktests(): Promise<Backtest[]> {
  const response = await api.get<Backtest[]>("/backtests");
  return response.data;
}

export async function getBacktest(id: string): Promise<Backtest> {
  const response = await api.get<Backtest>(`/backtests/${id}`);
  return response.data;
}

export async function createBacktest(data: BacktestConfig): Promise<Backtest> {
  const response = await api.post<Backtest>("/backtests", data);
  return response.data;
}

export interface GetTradesParams {
  limit?: number;
  offset?: number;
}

export async function getBacktestTrades(
  id: string,
  params: GetTradesParams = {}
): Promise<Trade[]> {
  const response = await api.get<Trade[]>(`/backtests/${id}/trades`, {
    params: {
      limit: params.limit || 50,
      offset: params.offset || 0,
    },
  });
  return response.data;
}

export async function validateTicker(
  ticker: string,
  assetClass: string
): Promise<boolean> {
  try {
    const response = await api.get<{ valid: boolean }>("/tickers/validate", {
      params: { ticker, asset_class: assetClass },
    });
    return response.data.valid;
  } catch {
    return false;
  }
}
