import { useEffect, useRef } from 'react'
import { ChartManager, type CandleData, type LineDataPoint } from '@/features/live-chart'
import { useUIStore, getEffectiveTheme } from '@/store/uiStore'

interface TradingChartProps {
  candleData: CandleData[]
  indicators?: Array<{
    id: string
    data: LineDataPoint[]
    color?: string
    title?: string
  }>
  height?: number
  className?: string
}

export function TradingChart({
  candleData,
  indicators = [],
  height = 500,
  className,
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartManagerRef = useRef<ChartManager | null>(null)
  const { theme } = useUIStore()

  useEffect(() => {
    if (!containerRef.current || candleData.length === 0) return

    // Initialize chart
    chartManagerRef.current = new ChartManager({
      container: containerRef.current,
      height,
      theme: getEffectiveTheme(theme),
    })

    // Add candlestick data
    chartManagerRef.current.addCandlestickSeries(candleData)

    // Add indicators
    indicators.forEach((indicator) => {
      chartManagerRef.current?.addLineSeries(indicator.id, indicator.data, {
        color: indicator.color,
        title: indicator.title || indicator.id,
      })
    })

    chartManagerRef.current.fitContent()

    // Cleanup
    return () => {
      chartManagerRef.current?.destroy()
      chartManagerRef.current = null
    }
  }, [candleData, indicators, height])

  // Handle theme changes
  useEffect(() => {
    chartManagerRef.current?.setTheme(getEffectiveTheme(theme))
  }, [theme])

  // Handle resize
  useEffect(() => {
    if (!containerRef.current) return

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        chartManagerRef.current?.resize(width, height)
      }
    })

    resizeObserver.observe(containerRef.current)

    return () => resizeObserver.disconnect()
  }, [height])

  if (candleData.length === 0) {
    return (
      <div
        className={`flex items-center justify-center bg-surface-2 rounded-lg ${className}`}
        style={{ height }}
      >
        <p className="text-muted-foreground">No data available</p>
      </div>
    )
  }

  return <div ref={containerRef} className={className} />
}
