import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  startParameterSensitivity,
  startWalkForward,
  startRegimeDetection,
  startFeatureConditioning,
  getRobustnessAnalysis,
  deleteRobustnessAnalysis,
  type ParameterSensitivityCreate,
  type WalkForwardCreate,
  type RegimeDetectionCreate,
  type FeatureConditioningCreate,
} from '../endpoints/robustness'
import type { RobustnessAnalysis } from '@/types'

export const robustnessKeys = {
  all: ['robustness'] as const,
  details: () => [...robustnessKeys.all, 'detail'] as const,
  detail: (id: string) => [...robustnessKeys.details(), id] as const,
}

export function useRobustnessAnalysis(id: string) {
  return useQuery({
    queryKey: robustnessKeys.detail(id),
    queryFn: () => getRobustnessAnalysis(id),
    enabled: !!id,
    // Poll while pending or running
    refetchInterval: (query) => {
      const data = query.state.data as RobustnessAnalysis | undefined
      if (data?.status === 'PENDING' || data?.status === 'RUNNING') {
        return 3000 // Poll every 3 seconds
      }
      return false
    },
  })
}

export function useStartParameterSensitivity() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: ParameterSensitivityCreate) =>
      startParameterSensitivity(params),
    onSuccess: (data) => {
      queryClient.setQueryData(robustnessKeys.detail(data.id), data)
    },
  })
}

export function useStartWalkForward() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: WalkForwardCreate) => startWalkForward(params),
    onSuccess: (data) => {
      queryClient.setQueryData(robustnessKeys.detail(data.id), data)
    },
  })
}

export function useStartRegimeDetection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: RegimeDetectionCreate) => startRegimeDetection(params),
    onSuccess: (data) => {
      queryClient.setQueryData(robustnessKeys.detail(data.id), data)
    },
  })
}

export function useStartFeatureConditioning() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: FeatureConditioningCreate) =>
      startFeatureConditioning(params),
    onSuccess: (data) => {
      queryClient.setQueryData(robustnessKeys.detail(data.id), data)
    },
  })
}

export function useDeleteRobustnessAnalysis() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteRobustnessAnalysis(id),
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: robustnessKeys.detail(id) })
    },
  })
}
