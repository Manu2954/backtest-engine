import apiClient from '../client'
import type { Backtest, BacktestConfig, TradeLog } from '@/types'

export async function getBacktests(params?: {
  strategy_id?: string
  limit?: number
  offset?: number
}): Promise<Backtest[]> {
  const { data } = await apiClient.get('/backtests', { params })
  return data
}

export async function getBacktest(id: string): Promise<Backtest> {
  const { data } = await apiClient.get(`/backtests/${id}`)
  return data
}

export async function createBacktest(config: BacktestConfig): Promise<Backtest> {
  const { data } = await apiClient.post('/backtests', config)
  return data
}

export async function deleteBacktest(id: string): Promise<void> {
  await apiClient.delete(`/backtests/${id}`)
}

export async function getBacktestTrades(
  runId: string,
  params?: { limit?: number; offset?: number }
): Promise<TradeLog[]> {
  const { data } = await apiClient.get(`/backtests/${runId}/trades`, { params })
  return data
}
