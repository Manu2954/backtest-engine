import apiClient from '../client'

export async function validateTicker(
  ticker: string,
  assetClass: string = 'STOCK'
): Promise<boolean> {
  const { data } = await apiClient.get('/tickers/validate', {
    params: { ticker, asset_class: assetClass },
  })
  return data.valid
}

export async function checkHealth(): Promise<{
  status: 'healthy' | 'degraded' | 'unhealthy'
  checks: Record<string, unknown>
  timestamp: string
}> {
  const { data } = await apiClient.get('/health')
  return data
}
