import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
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
  deleteBacktest,
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
      toast.success("Strategy created successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to create strategy: ${error.message}`);
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
      toast.success("Strategy updated successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to update strategy: ${error.message}`);
    },
  });
}

export function useDeleteStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteStrategy(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      toast.success("Strategy deleted");
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete strategy: ${error.message}`);
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
      toast.success("Backtest started");
    },
    onError: (error: Error) => {
      toast.error(`Failed to start backtest: ${error.message}`);
    },
  });
}

export function useDeleteBacktest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteBacktest(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backtests"] });
      toast.success("Backtest deleted");
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete backtest: ${error.message}`);
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
