import { useEffect, useRef } from 'react'
import { ChartManager, type LineDataPoint } from '@/features/live-chart'
import { useUIStore, getEffectiveTheme } from '@/store/uiStore'

interface EquityCurveProps {
  data: Array<{ date: string; equity: number; benchmark?: number }>
  height?: number
  showBenchmark?: boolean
  className?: string
}

export function EquityCurve({
  data,
  height = 300,
  showBenchmark = true,
  className,
}: EquityCurveProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartManagerRef = useRef<ChartManager | null>(null)
  const { theme } = useUIStore()

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return

    // Initialize chart
    chartManagerRef.current = new ChartManager({
      container: containerRef.current,
      height,
      theme: getEffectiveTheme(theme),
    })

    // Deduplicate and sort data by date (keep last value for each date)
    const dateMap = new Map<string, { equity: number; benchmark?: number }>()
    for (const d of data) {
      // Normalize date to YYYY-MM-DD format
      const dateStr = d.date.split('T')[0].split(' ')[0]
      dateMap.set(dateStr, { equity: d.equity, benchmark: d.benchmark })
    }

    // Convert to sorted array
    const sortedDates = Array.from(dateMap.keys()).sort()
    const equityData: LineDataPoint[] = sortedDates.map((date) => ({
      time: date,
      value: dateMap.get(date)!.equity,
    }))

    // Add equity curve as area series
    chartManagerRef.current.addAreaSeries(equityData, {
      topColor: 'rgba(31, 111, 235, 0.3)',
      bottomColor: 'rgba(31, 111, 235, 0.0)',
      lineColor: '#1f6feb',
    })

    // Add benchmark if available
    if (showBenchmark) {
      const benchmarkData: LineDataPoint[] = sortedDates
        .filter((date) => dateMap.get(date)!.benchmark !== undefined)
        .map((date) => ({
          time: date,
          value: dateMap.get(date)!.benchmark!,
        }))

      if (benchmarkData.length > 0) {
        chartManagerRef.current.addLineSeries('benchmark', benchmarkData, {
          color: '#8b949e',
          lineWidth: 1,
          title: 'Buy & Hold',
        })
      }
    }

    chartManagerRef.current.fitContent()

    // Cleanup
    return () => {
      chartManagerRef.current?.destroy()
      chartManagerRef.current = null
    }
  }, [data, height, showBenchmark])

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

  if (data.length === 0) {
    return (
      <div
        className={`flex items-center justify-center bg-surface-2 rounded-lg ${className}`}
        style={{ height }}
      >
        <p className="text-muted-foreground">No data available</p>
      </div>
    )
  }

  // Whether any benchmark data exists (for legend)
  const hasBenchmark = showBenchmark && data.some((d) => d.benchmark !== undefined)

  return (
    <div className={className}>
      {/* Legend */}
      <div className="mb-2 flex items-center gap-4 px-1 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-3 rounded-sm" style={{ background: 'hsl(var(--chart-1))' }} />
          <span className="text-muted-foreground">Strategy</span>
        </div>
        {hasBenchmark && (
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-3 rounded-sm" style={{ background: 'hsl(var(--muted-foreground))' }} />
            <span className="text-muted-foreground">Buy &amp; Hold</span>
          </div>
        )}
      </div>
      <div ref={containerRef} />
    </div>
  )
}
