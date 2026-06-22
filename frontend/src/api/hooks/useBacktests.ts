import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getBacktests,
  getBacktest,
  createBacktest,
  deleteBacktest,
  getBacktestTrades,
} from '../endpoints/backtests'
import type { Backtest, BacktestConfig } from '@/types'

export const backtestKeys = {
  all: ['backtests'] as const,
  lists: () => [...backtestKeys.all, 'list'] as const,
  list: (params: { strategy_id?: string; limit?: number; offset?: number }) =>
    [...backtestKeys.lists(), params] as const,
  details: () => [...backtestKeys.all, 'detail'] as const,
  detail: (id: string) => [...backtestKeys.details(), id] as const,
  trades: (id: string) => [...backtestKeys.detail(id), 'trades'] as const,
}

export function useBacktests(params?: {
  strategy_id?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: backtestKeys.list(params || {}),
    queryFn: () => getBacktests(params),
    staleTime: 30 * 1000, // 30 seconds - backtests change more frequently
  })
}

export function useBacktest(id: string) {
  return useQuery({
    queryKey: backtestKeys.detail(id),
    queryFn: () => getBacktest(id),
    enabled: !!id,
    // Poll while pending or running
    refetchInterval: (query) => {
      const data = query.state.data as Backtest | undefined
      if (data?.status === 'PENDING' || data?.status === 'RUNNING') {
        return 2000 // Poll every 2 seconds
      }
      return false
    },
  })
}

export function useBacktestTrades(
  runId: string,
  params?: { limit?: number; offset?: number }
) {
  return useQuery({
    queryKey: [...backtestKeys.trades(runId), params],
    queryFn: () => getBacktestTrades(runId, params),
    enabled: !!runId,
    staleTime: 5 * 60 * 1000, // 5 minutes - trades don't change
  })
}

export function useCreateBacktest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (config: BacktestConfig) => createBacktest(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: backtestKeys.lists() })
    },
  })
}

export function useDeleteBacktest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteBacktest(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: backtestKeys.lists() })
      const previous = queryClient.getQueryData<Backtest[]>(backtestKeys.list({}))
      queryClient.setQueryData<Backtest[]>(backtestKeys.list({}), (old) =>
        old?.filter((b) => b.id !== id)
      )
      return { previous }
    },
    onError: (_, __, context) => {
      if (context?.previous) {
        queryClient.setQueryData(backtestKeys.list({}), context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: backtestKeys.lists() })
    },
  })
}
