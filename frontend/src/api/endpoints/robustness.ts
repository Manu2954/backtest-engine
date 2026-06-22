import apiClient from '../client'
import type { RobustnessAnalysis } from '@/types'

export interface ParameterSensitivityCreate {
  strategy_id: string
  ticker: string
  asset_class: string
  start_date: string
  end_date: string
  initial_capital: number
  bar_resolution?: string
}

export interface WalkForwardCreate {
  strategy_id: string
  ticker: string
  asset_class: string
  start_date: string
  end_date: string
  initial_capital: number
  windows?: number
  bar_resolution?: string
}

export interface RegimeDetectionCreate {
  strategy_id: string
  ticker: string
  asset_class: string
  start_date: string
  end_date: string
  initial_capital: number
  strategy?: 'l1_trend' | 'pelt_directional' | 'pelt_volatility'
  bar_resolution?: string
}

export interface FeatureConditioningCreate {
  strategy_id: string
  ticker: string
  asset_class: string
  start_date: string
  end_date: string
  initial_capital: number
  bar_resolution?: string
}

export async function startParameterSensitivity(
  params: ParameterSensitivityCreate
): Promise<RobustnessAnalysis> {
  const { data } = await apiClient.post('/robustness/parameter-sensitivity', params)
  return data
}

export async function startWalkForward(
  params: WalkForwardCreate
): Promise<RobustnessAnalysis> {
  const { data } = await apiClient.post('/robustness/walk-forward', params)
  return data
}

export async function startRegimeDetection(
  params: RegimeDetectionCreate
): Promise<RobustnessAnalysis> {
  const { data } = await apiClient.post('/robustness/regime-detection', params)
  return data
}

export async function startFeatureConditioning(
  params: FeatureConditioningCreate
): Promise<RobustnessAnalysis> {
  const { data } = await apiClient.post('/robustness/feature-conditioning', params)
  return data
}

export async function getRobustnessAnalysis(id: string): Promise<RobustnessAnalysis> {
  const { data } = await apiClient.get(`/robustness/${id}`)
  return data
}

export async function deleteRobustnessAnalysis(id: string): Promise<void> {
  await apiClient.delete(`/robustness/${id}`)
}
