import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getStrategies,
  getStrategy,
  createStrategy,
  updateStrategy,
  deleteStrategy,
} from '../endpoints/strategies'
import type { Strategy, StrategyCreate } from '@/types'

export const strategyKeys = {
  all: ['strategies'] as const,
  lists: () => [...strategyKeys.all, 'list'] as const,
  list: (params: { limit?: number; offset?: number }) =>
    [...strategyKeys.lists(), params] as const,
  details: () => [...strategyKeys.all, 'detail'] as const,
  detail: (id: string) => [...strategyKeys.details(), id] as const,
}

export function useStrategies(params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: strategyKeys.list(params || {}),
    queryFn: () => getStrategies(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useStrategy(id: string) {
  return useQuery({
    queryKey: strategyKeys.detail(id),
    queryFn: () => getStrategy(id),
    enabled: !!id,
  })
}

export function useCreateStrategy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (strategy: StrategyCreate) => createStrategy(strategy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: strategyKeys.lists() })
    },
  })
}

export function useUpdateStrategy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      id,
      strategy,
    }: {
      id: string
      strategy: Partial<StrategyCreate>
    }) => updateStrategy(id, strategy),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: strategyKeys.lists() })
      queryClient.setQueryData(strategyKeys.detail(data.id), data)
    },
  })
}

export function useDeleteStrategy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteStrategy(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: strategyKeys.lists() })
      const previous = queryClient.getQueryData<Strategy[]>(strategyKeys.list({}))
      queryClient.setQueryData<Strategy[]>(strategyKeys.list({}), (old) =>
        old?.filter((s) => s.id !== id)
      )
      return { previous }
    },
    onError: (_, __, context) => {
      if (context?.previous) {
        queryClient.setQueryData(strategyKeys.list({}), context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: strategyKeys.lists() })
    },
  })
}
