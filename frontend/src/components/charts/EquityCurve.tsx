import { useEffect, useRef } from 'react'
import { ChartManager, type LineDataPoint } from '@/features/live-chart'
import { useUIStore } from '@/store/uiStore'

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
      theme,
    })

    // Convert data to LineDataPoint format
    const equityData: LineDataPoint[] = data.map((d) => ({
      time: d.date,
      value: d.equity,
    }))

    // Add equity curve as area series
    chartManagerRef.current.addAreaSeries(equityData, {
      topColor: 'rgba(31, 111, 235, 0.3)',
      bottomColor: 'rgba(31, 111, 235, 0.0)',
      lineColor: '#1f6feb',
    })

    // Add benchmark if available
    if (showBenchmark) {
      const benchmarkData: LineDataPoint[] = data
        .filter((d) => d.benchmark !== undefined)
        .map((d) => ({
          time: d.date,
          value: d.benchmark!,
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
    chartManagerRef.current?.setTheme(theme)
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

  return <div ref={containerRef} className={className} />
}
