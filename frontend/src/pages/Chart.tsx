import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Header } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { TradingChart } from '@/components/charts'
import { type CandleData, type LineDataPoint } from '@/features/live-chart'
import { Search, RefreshCw } from 'lucide-react'

// Demo data generator for chart testing
function generateDemoData(days: number = 100): CandleData[] {
  const data: CandleData[] = []
  let price = 100 + Math.random() * 50
  const now = new Date()
  now.setDate(now.getDate() - days)

  for (let i = 0; i < days; i++) {
    const date = new Date(now)
    date.setDate(date.getDate() + i)

    const volatility = 0.02
    const change = (Math.random() - 0.5) * 2 * volatility * price
    const open = price
    const close = price + change
    const high = Math.max(open, close) + Math.random() * volatility * price
    const low = Math.min(open, close) - Math.random() * volatility * price

    data.push({
      time: date.toISOString().split('T')[0],
      open: parseFloat(open.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      close: parseFloat(close.toFixed(2)),
    })

    price = close
  }

  return data
}

// Generate SMA indicator data
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
  const [ticker, setTicker] = useState(paramTicker || 'DEMO')
  const [searchInput, setSearchInput] = useState(paramTicker || '')
  const [candleData, setCandleData] = useState<CandleData[]>([])
  const [indicators, setIndicators] = useState<IndicatorData[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // Load demo data on mount
  useEffect(() => {
    loadDemoData()
  }, [])

  const loadDemoData = () => {
    setIsLoading(true)
    // Simulate API delay
    setTimeout(() => {
      const data = generateDemoData(200)
      setCandleData(data)

      // Calculate indicators
      const sma20 = calculateSMA(data, 20)
      const sma50 = calculateSMA(data, 50)

      setIndicators([
        { id: 'sma20', data: sma20, color: '#1f6feb', title: 'SMA 20' },
        { id: 'sma50', data: sma50, color: '#d29922', title: 'SMA 50' },
      ])

      setIsLoading(false)
    }, 300)
  }

  const handleSearch = () => {
    if (searchInput.trim()) {
      setTicker(searchInput.trim().toUpperCase())
      loadDemoData() // In real app, would fetch actual data
    }
  }

  return (
    <>
      <Header title="Chart">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Enter ticker..."
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
            <Badge variant="outline">Demo Data</Badge>
            {candleData.length > 0 && (
              <span className="text-sm text-muted-foreground">
                {candleData.length} bars
              </span>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={loadDemoData}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Main Chart */}
        <Card>
          <CardContent className="p-0">
            {candleData.length > 0 ? (
              <TradingChart
                candleData={candleData}
                indicators={indicators}
                height={500}
              />
            ) : (
              <div className="flex items-center justify-center h-[500px]">
                <p className="text-muted-foreground">Loading chart data...</p>
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
                <Badge
                  key={ind.id}
                  variant="secondary"
                  className="gap-2"
                >
                  <span
                    className="w-2 h-2 rounded-full"
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

        {/* Info */}
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-muted-foreground">
              This is a demo chart using generated data. In production, this would connect
              to real market data via the backend API. The chart supports candlesticks,
              line indicators, and trade markers.
            </p>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
