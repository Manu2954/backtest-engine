import apiClient from '../client'

export interface ChartCandle {
  time: string
  open: number
  high: number
  low: number
  close: number
}

export interface ChartVolumePoint {
  time: string
  value: number
}

export interface ChartDataResponse {
  ticker: string
  asset_class: string
  resolution: string
  start_date: string
  end_date: string
  count: number
  candles: ChartCandle[]
  volume: ChartVolumePoint[]
}

export interface ChartDataParams {
  ticker: string
  assetClass?: string
  resolution?: string
  startDate?: string
  endDate?: string
}

export async function getChartData(
  params: ChartDataParams
): Promise<ChartDataResponse> {
  const { data } = await apiClient.get('/charts/ohlcv', {
    params: {
      ticker: params.ticker,
      asset_class: params.assetClass ?? 'STOCK',
      resolution: params.resolution ?? '1d',
      start_date: params.startDate,
      end_date: params.endDate,
    },
  })
  return data
}
