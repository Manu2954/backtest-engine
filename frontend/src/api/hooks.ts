import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getStrategies,
  getStrategy,
  createStrategy,
  updateStrategy,
  deleteStrategy,
} from "./strategies";
import {
  getBacktests,
  getBacktest,
  createBacktest,
  getBacktestTrades,
  type GetTradesParams,
} from "./backtests";
import type { StrategyCreate, BacktestConfig } from "@/types";

// Strategy hooks
export function useStrategies() {
  return useQuery({
    queryKey: ["strategies"],
    queryFn: getStrategies,
  });
}

export function useStrategy(id: string | undefined) {
  return useQuery({
    queryKey: ["strategy", id],
    queryFn: () => getStrategy(id!),
    enabled: !!id,
  });
}

export function useCreateStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: StrategyCreate) => createStrategy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
    },
  });
}

export function useUpdateStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: StrategyCreate }) =>
      updateStrategy(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      queryClient.invalidateQueries({ queryKey: ["strategy", id] });
    },
  });
}

export function useDeleteStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteStrategy(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
    },
  });
}

// Backtest hooks
export function useBacktests() {
  return useQuery({
    queryKey: ["backtests"],
    queryFn: getBacktests,
  });
}

export function useBacktest(id: string | undefined) {
  return useQuery({
    queryKey: ["backtest", id],
    queryFn: () => getBacktest(id!),
    enabled: !!id,
    // Poll while backtest is running
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "PENDING" || status === "RUNNING") {
        return 2000; // Poll every 2 seconds
      }
      return false;
    },
  });
}

export function useCreateBacktest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BacktestConfig) => createBacktest(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backtests"] });
    },
  });
}

export function useBacktestTrades(id: string | undefined, params: GetTradesParams = {}) {
  return useQuery({
    queryKey: ["backtest-trades", id, params],
    queryFn: () => getBacktestTrades(id!, params),
    enabled: !!id,
  });
}
