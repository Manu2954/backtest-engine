import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Header } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'
import { TradingChart } from '@/components/charts'
import { type CandleData, type LineDataPoint } from '@/features/live-chart'
import { useChartData } from '@/api/hooks'
import { Search, RefreshCw, AlertCircle } from 'lucide-react'

// Generate SMA indicator data from candles (client-side overlay)
function calculateSMA(data: CandleData[], period: number): LineDataPoint[] {
  const result: LineDataPoint[] = []
  for (let i = period - 1; i < data.length; i++) {
    let sum = 0
    for (let j = 0; j < period; j++) {
      sum += data[i - j].close
    }
    result.push({
      time: data[i].time,
      value: parseFloat((sum / period).toFixed(2)),
    })
  }
  return result
}

interface IndicatorData {
  id: string
  data: LineDataPoint[]
  color: string
  title: string
}

export function ChartPage() {
  const { ticker: paramTicker } = useParams<{ ticker?: string }>()
  const [ticker, setTicker] = useState(paramTicker || 'AAPL')
  const [searchInput, setSearchInput] = useState(paramTicker || 'AAPL')
  const [assetClass, setAssetClass] = useState<'STOCK' | 'CRYPTO'>('STOCK')

  const { data, isLoading, isError, error, refetch, isFetching } = useChartData({
    ticker,
    assetClass,
    resolution: '1d',
  })

  const candleData: CandleData[] = data?.candles ?? []

  // Compute SMA overlays from real candles
  const [indicators, setIndicators] = useState<IndicatorData[]>([])
  useEffect(() => {
    if (candleData.length > 0) {
      setIndicators([
        { id: 'sma20', data: calculateSMA(candleData, 20), color: 'hsl(var(--chart-1))', title: 'SMA 20' },
        { id: 'sma50', data: calculateSMA(candleData, 50), color: 'hsl(var(--chart-3))', title: 'SMA 50' },
      ])
    } else {
      setIndicators([])
    }
  }, [candleData])

  const handleSearch = () => {
    if (searchInput.trim()) {
      setTicker(searchInput.trim().toUpperCase())
    }
  }

  return (
    <>
      <Header title="Chart">
        <div className="flex items-center gap-2">
          <Select value={assetClass} onValueChange={(v) => setAssetClass(v as 'STOCK' | 'CRYPTO')}>
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="STOCK">Stock</SelectItem>
              <SelectItem value="CRYPTO">Crypto</SelectItem>
            </SelectContent>
          </Select>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder={assetClass === 'CRYPTO' ? 'BTCUSDT...' : 'AAPL...'}
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="pl-9 w-40"
            />
          </div>
          <Button onClick={handleSearch} size="sm">
            Load
          </Button>
        </div>
      </Header>

      <div className="p-6 space-y-4">
        {/* Chart Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold">{ticker}</h2>
            <Badge variant="outline">{assetClass}</Badge>
            {candleData.length > 0 && (
              <span className="text-sm text-muted-foreground">
                {candleData.length} bars
              </span>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Main Chart */}
        <Card>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="flex h-[500px] items-center justify-center">
                <div className="flex flex-col items-center gap-3 text-muted-foreground">
                  <Spinner size="lg" />
                  <p>Loading chart data...</p>
                </div>
              </div>
            ) : isError ? (
              <div className="flex h-[500px] items-center justify-center">
                <div className="flex max-w-md flex-col items-center gap-3 text-center">
                  <AlertCircle className="h-10 w-10 text-loss" />
                  <p className="font-medium">Failed to load chart data</p>
                  <p className="text-sm text-muted-foreground">
                    {error instanceof Error ? error.message : `No data found for ${ticker}.`}{' '}
                    Check the ticker symbol and asset class.
                  </p>
                  <Button variant="outline" size="sm" onClick={() => refetch()}>
                    <RefreshCw className="h-4 w-4" />
                    Retry
                  </Button>
                </div>
              </div>
            ) : candleData.length > 0 ? (
              <TradingChart
                candleData={candleData}
                indicators={indicators}
                height={500}
              />
            ) : (
              <div className="flex h-[500px] items-center justify-center">
                <p className="text-muted-foreground">No data available for {ticker}.</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Indicators Panel */}
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-sm">Active Indicators</CardTitle>
          </CardHeader>
          <CardContent className="py-2">
            <div className="flex flex-wrap gap-2">
              {indicators.map((ind) => (
                <Badge key={ind.id} variant="secondary" className="gap-2">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: ind.color }}
                  />
                  {ind.title}
                </Badge>
              ))}
              {indicators.length === 0 && (
                <span className="text-sm text-muted-foreground">
                  No indicators active
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
