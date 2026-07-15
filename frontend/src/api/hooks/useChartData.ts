import { useQuery } from '@tanstack/react-query'
import { getChartData, type ChartDataParams } from '../endpoints/charts'

export const chartKeys = {
  all: ['charts'] as const,
  data: (params: ChartDataParams) => [...chartKeys.all, 'ohlcv', params] as const,
}

export function useChartData(params: ChartDataParams, enabled = true) {
  return useQuery({
    queryKey: chartKeys.data(params),
    queryFn: () => getChartData(params),
    enabled: enabled && !!params.ticker,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  })
}
