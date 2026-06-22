import apiClient from '../client'
import type { Strategy, StrategyCreate } from '@/types'

export async function getStrategies(params?: {
  limit?: number
  offset?: number
}): Promise<Strategy[]> {
  const { data } = await apiClient.get('/strategies', { params })
  return data
}

export async function getStrategy(id: string): Promise<Strategy> {
  const { data } = await apiClient.get(`/strategies/${id}`)
  return data
}

export async function createStrategy(strategy: StrategyCreate): Promise<Strategy> {
  const { data } = await apiClient.post('/strategies', strategy)
  return data
}

export async function updateStrategy(
  id: string,
  strategy: Partial<StrategyCreate>
): Promise<Strategy> {
  const { data } = await apiClient.put(`/strategies/${id}`, strategy)
  return data
}

export async function deleteStrategy(id: string): Promise<void> {
  await apiClient.delete(`/strategies/${id}`)
}
