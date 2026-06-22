import {
  createChart,
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type Time,
  type LineWidth,
  CandlestickSeries,
  LineSeries,
  AreaSeries,
} from 'lightweight-charts'

export interface ChartColors {
  background: string
  text: string
  grid: string
  upColor: string
  downColor: string
  borderUpColor: string
  borderDownColor: string
  wickUpColor: string
  wickDownColor: string
}

export const darkThemeColors: ChartColors = {
  background: 'transparent',
  text: '#8b949e',
  grid: 'rgba(48, 54, 61, 0.3)',
  upColor: '#2ea043',
  downColor: '#f85149',
  borderUpColor: '#2ea043',
  borderDownColor: '#f85149',
  wickUpColor: '#2ea043',
  wickDownColor: '#f85149',
}

export const lightThemeColors: ChartColors = {
  background: 'transparent',
  text: '#57606a',
  grid: 'rgba(208, 215, 222, 0.5)',
  upColor: '#1a7f37',
  downColor: '#cf222e',
  borderUpColor: '#1a7f37',
  borderDownColor: '#cf222e',
  wickUpColor: '#1a7f37',
  wickDownColor: '#cf222e',
}

export interface ChartManagerOptions {
  container: HTMLElement
  width?: number
  height?: number
  theme?: 'dark' | 'light'
}

export interface CandleData {
  time: string
  open: number
  high: number
  low: number
  close: number
}

export interface LineDataPoint {
  time: string
  value: number
}

export class ChartManager {
  private chart: IChartApi
  private candlestickSeries: ISeriesApi<'Candlestick'> | null = null
  private lineSeries: Map<string, ISeriesApi<'Line'>> = new Map()
  private areaSeries: ISeriesApi<'Area'> | null = null
  private colors: ChartColors

  constructor(options: ChartManagerOptions) {
    this.colors = options.theme === 'light' ? lightThemeColors : darkThemeColors

    this.chart = createChart(options.container, {
      width: options.width || options.container.clientWidth,
      height: options.height || 400,
      layout: {
        background: { type: ColorType.Solid, color: this.colors.background },
        textColor: this.colors.text,
      },
      grid: {
        vertLines: { color: this.colors.grid },
        horzLines: { color: this.colors.grid },
      },
      crosshair: {
        mode: 1, // Normal
        vertLine: {
          width: 1,
          color: 'rgba(139, 148, 158, 0.4)',
          style: 2, // Dashed
        },
        horzLine: {
          width: 1,
          color: 'rgba(139, 148, 158, 0.4)',
          style: 2,
        },
      },
      rightPriceScale: {
        borderColor: this.colors.grid,
      },
      timeScale: {
        borderColor: this.colors.grid,
        timeVisible: true,
        secondsVisible: false,
      },
    })
  }

  setTheme(theme: 'dark' | 'light') {
    this.colors = theme === 'light' ? lightThemeColors : darkThemeColors
    this.chart.applyOptions({
      layout: {
        background: { type: ColorType.Solid, color: this.colors.background },
        textColor: this.colors.text,
      },
      grid: {
        vertLines: { color: this.colors.grid },
        horzLines: { color: this.colors.grid },
      },
      rightPriceScale: {
        borderColor: this.colors.grid,
      },
      timeScale: {
        borderColor: this.colors.grid,
      },
    })

    // Update candlestick colors
    if (this.candlestickSeries) {
      this.candlestickSeries.applyOptions({
        upColor: this.colors.upColor,
        downColor: this.colors.downColor,
        borderUpColor: this.colors.borderUpColor,
        borderDownColor: this.colors.borderDownColor,
        wickUpColor: this.colors.wickUpColor,
        wickDownColor: this.colors.wickDownColor,
      })
    }
  }

  resize(width: number, height: number) {
    this.chart.resize(width, height)
  }

  addCandlestickSeries(data: CandleData[]) {
    if (this.candlestickSeries) {
      this.chart.removeSeries(this.candlestickSeries)
    }

    this.candlestickSeries = this.chart.addSeries(CandlestickSeries, {
      upColor: this.colors.upColor,
      downColor: this.colors.downColor,
      borderUpColor: this.colors.borderUpColor,
      borderDownColor: this.colors.borderDownColor,
      wickUpColor: this.colors.wickUpColor,
      wickDownColor: this.colors.wickDownColor,
    })

    const formattedData = data.map((d) => ({
      time: d.time as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }))

    this.candlestickSeries.setData(formattedData)
    this.chart.timeScale().fitContent()

    return this.candlestickSeries
  }

  addLineSeries(id: string, data: LineDataPoint[], options: {
    color?: string
    lineWidth?: number
    title?: string
  } = {}) {
    // Remove existing series with same id
    if (this.lineSeries.has(id)) {
      const existing = this.lineSeries.get(id)!
      this.chart.removeSeries(existing)
    }

    const series = this.chart.addSeries(LineSeries, {
      color: options.color || '#1f6feb',
      lineWidth: (options.lineWidth || 2) as LineWidth,
      title: options.title || id,
      priceLineVisible: false,
      lastValueVisible: true,
    })

    const formattedData = data.map((d) => ({
      time: d.time as Time,
      value: d.value,
    }))

    series.setData(formattedData)
    this.lineSeries.set(id, series)

    return series
  }

  addAreaSeries(data: LineDataPoint[], options: {
    topColor?: string
    bottomColor?: string
    lineColor?: string
  } = {}) {
    if (this.areaSeries) {
      this.chart.removeSeries(this.areaSeries)
    }

    this.areaSeries = this.chart.addSeries(AreaSeries, {
      topColor: options.topColor || 'rgba(31, 111, 235, 0.4)',
      bottomColor: options.bottomColor || 'rgba(31, 111, 235, 0.0)',
      lineColor: options.lineColor || '#1f6feb',
      lineWidth: 2 as LineWidth,
    })

    const formattedData = data.map((d) => ({
      time: d.time as Time,
      value: d.value,
    }))

    this.areaSeries.setData(formattedData)
    this.chart.timeScale().fitContent()

    return this.areaSeries
  }

  removeLineSeries(id: string) {
    if (this.lineSeries.has(id)) {
      const series = this.lineSeries.get(id)!
      this.chart.removeSeries(series)
      this.lineSeries.delete(id)
    }
  }

  clearAllIndicators() {
    this.lineSeries.forEach((series) => {
      this.chart.removeSeries(series)
    })
    this.lineSeries.clear()
  }

  fitContent() {
    this.chart.timeScale().fitContent()
  }

  getChart() {
    return this.chart
  }

  destroy() {
    this.chart.remove()
  }
}
