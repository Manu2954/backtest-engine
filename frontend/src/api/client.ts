import axios from "axios";
import type {
  Strategy,
  StrategyCreate,
  Backtest,
  BacktestConfig,
  TradeLog,
} from "../types";

// Determine API base URL
const getBaseUrl = () => {
  // Check for environment variable first
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  // In development, use localhost
  if (import.meta.env.DEV) {
    return "http://localhost:8000/api/v1";
  }
  // In production, use relative URL (same origin)
  return "/api/v1";
};

export const api = axios.create({
  baseURL: getBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.debug(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "An unexpected error occurred";

    console.error(`[API Error] ${message}`, error.response?.data);

    // Re-throw with a cleaner error message
    return Promise.reject(new Error(message));
  }
);

// Strategy API functions
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

export async function updateStrategy(id: string, data: StrategyCreate): Promise<Strategy> {
  const response = await api.put<Strategy>(`/strategies/${id}`, data);
  return response.data;
}

export async function deleteStrategy(id: string): Promise<void> {
  await api.delete(`/strategies/${id}`);
}

// Backtest API functions
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

export async function deleteBacktest(id: string): Promise<void> {
  await api.delete(`/backtests/${id}`);
}

export async function getBacktestTrades(
  id: string,
  limit = 50,
  offset = 0
): Promise<TradeLog[]> {
  const response = await api.get<TradeLog[]>(`/backtests/${id}/trades`, {
    params: { limit, offset },
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
