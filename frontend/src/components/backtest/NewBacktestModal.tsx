import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Card,
  CardContent,
} from '@/components/ui/card'
import { useStrategies } from '@/api/hooks'
import { useCreateBacktest } from '@/api/hooks'
import {
  Play,
  Loader2,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  Calendar,
  DollarSign,
  Shield,
  Settings2,
  AlertCircle,
  Repeat,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { BacktestConfig } from '@/types'

interface NewBacktestModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: (backtestId: string) => void
  defaultStrategyId?: string
}

const STOCK_RESOLUTIONS = [
  { value: '1m', label: '1 Minute' },
  { value: '5m', label: '5 Minutes' },
  { value: '15m', label: '15 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '1d', label: '1 Day' },
]

const CRYPTO_RESOLUTIONS = [
  { value: '1m', label: '1 Minute' },
  { value: '5m', label: '5 Minutes' },
  { value: '15m', label: '15 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: '1 Day' },
]

const POSITION_SIZE_TYPES = [
  { value: 'full_capital', label: 'Full Capital', description: 'Use all available capital' },
  { value: 'percent_capital', label: 'Percent of Capital', description: 'Use a percentage of capital' },
  { value: 'fixed_amount', label: 'Fixed Amount', description: 'Use a fixed dollar amount' },
]

const DCA_FREQUENCIES = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'interval_days', label: 'Custom Interval' },
]

// Get default dates (1 year back from today)
function getDefaultDates() {
  const end = new Date()
  const start = new Date()
  start.setFullYear(start.getFullYear() - 1)
  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0],
  }
}

export function NewBacktestModal({
  open,
  onOpenChange,
  onSuccess,
  defaultStrategyId,
}: NewBacktestModalProps) {
  const navigate = useNavigate()
  const { data: strategies, isLoading: loadingStrategies } = useStrategies({ limit: 100 })
  const createBacktest = useCreateBacktest()

  const defaultDates = getDefaultDates()

  // Form state
  const [strategyId, setStrategyId] = useState(defaultStrategyId || '')
  const [ticker, setTicker] = useState('')
  const [assetClass, setAssetClass] = useState<'STOCK' | 'CRYPTO'>('STOCK')
  const [startDate, setStartDate] = useState(defaultDates.start)
  const [endDate, setEndDate] = useState(defaultDates.end)
  const [resolution, setResolution] = useState('1d')
  const [initialCapital, setInitialCapital] = useState('10000')

  // Position sizing
  const [positionSizeType, setPositionSizeType] = useState('full_capital')
  const [positionSizeValue, setPositionSizeValue] = useState('100')

  // Optional: Risk management
  const [stopLossPct, setStopLossPct] = useState('')
  const [takeProfitPct, setTakeProfitPct] = useState('')

  // Optional: Transaction costs
  const [commissionPerTrade, setCommissionPerTrade] = useState('')
  const [commissionPct, setCommissionPct] = useState('')
  const [slippagePct, setSlippagePct] = useState('')

  // Optional: Dollar Cost Averaging
  const [dcaEnabled, setDcaEnabled] = useState(false)
  const [dcaAmount, setDcaAmount] = useState('')
  const [dcaFrequency, setDcaFrequency] = useState('monthly')
  const [dcaIntervalDays, setDcaIntervalDays] = useState('')
  const [dcaIncludeStart, setDcaIncludeStart] = useState(false)

  // Optional: Leverage
  const [leverage, setLeverage] = useState('1')

  // UI state
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [touched, setTouched] = useState<Record<string, boolean>>({})

  // Reset form when modal opens
  useEffect(() => {
    if (open) {
      setError(null)
      setTouched({})
      if (!defaultStrategyId && strategies && strategies.length > 0) {
        setStrategyId(strategies[0].id)
      }
    }
  }, [open, strategies, defaultStrategyId])

  // Set default strategy when strategies load
  useEffect(() => {
    if (defaultStrategyId) {
      setStrategyId(defaultStrategyId)
    } else if (strategies && strategies.length > 0 && !strategyId) {
      setStrategyId(strategies[0].id)
    }
  }, [strategies, defaultStrategyId, strategyId])

  // Reset resolution when asset class changes
  useEffect(() => {
    const resolutions = assetClass === 'CRYPTO' ? CRYPTO_RESOLUTIONS : STOCK_RESOLUTIONS
    if (!resolutions.find(r => r.value === resolution)) {
      setResolution('1d')
    }
    // Update ticker placeholder
    if (assetClass === 'CRYPTO' && !ticker) {
      setTicker('BTCUSDT')
    } else if (assetClass === 'STOCK' && ticker === 'BTCUSDT') {
      setTicker('AAPL')
    }
  }, [assetClass, resolution, ticker])

  const resolutionOptions = assetClass === 'CRYPTO' ? CRYPTO_RESOLUTIONS : STOCK_RESOLUTIONS
  const selectedStrategy = strategies?.find(s => s.id === strategyId)

  // Validation
  const tickerError = touched.ticker && !ticker.trim() ? 'Ticker is required' : null
  const dateError = touched.dates && new Date(startDate) >= new Date(endDate)
    ? 'Start date must be before end date' : null
  const capitalError = touched.capital && (isNaN(Number(initialCapital)) || Number(initialCapital) <= 0)
    ? 'Must be a positive number' : null

  const canSubmit = strategyId && ticker.trim() && !dateError && !capitalError

  const handleSubmit = async () => {
    // Mark all fields as touched for validation
    setTouched({ ticker: true, dates: true, capital: true })

    if (!strategyId) {
      setError('Please select a strategy')
      return
    }

    if (!ticker.trim()) {
      setError('Please enter a ticker symbol')
      return
    }

    if (new Date(startDate) >= new Date(endDate)) {
      setError('Start date must be before end date')
      return
    }

    const capital = Number(initialCapital)
    if (isNaN(capital) || capital <= 0) {
      setError('Initial capital must be a positive number')
      return
    }

    setError(null)

    const config: BacktestConfig = {
      strategy_id: strategyId,
      ticker: ticker.toUpperCase().trim(),
      asset_class: assetClass,
      start_date: startDate,
      end_date: endDate,
      bar_resolution: resolution,
      initial_capital: capital,
      position_size_type: positionSizeType,
      position_size_value: Number(positionSizeValue) || 100,
    }

    // Add optional fields if provided
    if (stopLossPct) {
      const sl = Number(stopLossPct)
      if (!isNaN(sl) && sl > 0) config.stop_loss_pct = sl
    }
    if (takeProfitPct) {
      const tp = Number(takeProfitPct)
      if (!isNaN(tp) && tp > 0) config.take_profit_pct = tp
    }
    if (commissionPerTrade) {
      const comm = Number(commissionPerTrade)
      if (!isNaN(comm) && comm >= 0) config.commission_per_trade = comm
    }
    if (commissionPct) {
      const commP = Number(commissionPct)
      if (!isNaN(commP) && commP >= 0) config.commission_pct = commP
    }
    if (slippagePct) {
      const slip = Number(slippagePct)
      if (!isNaN(slip) && slip >= 0) config.slippage_pct = slip
    }

    // Add leverage if > 1
    const lev = Number(leverage)
    if (!isNaN(lev) && lev > 1) {
      config.leverage = lev
    }

    // Add periodic contribution (DCA) if enabled with valid amount
    if (dcaEnabled) {
      const amount = Number(dcaAmount)
      if (!isNaN(amount) && amount > 0) {
        const contribution: BacktestConfig['periodic_contribution'] = {
          amount,
          frequency: dcaFrequency,
          include_start: dcaIncludeStart,
        }
        // Add interval_days only when frequency is interval_days
        if (dcaFrequency === 'interval_days') {
          const intervalDays = Number(dcaIntervalDays)
          if (!isNaN(intervalDays) && intervalDays > 0) {
            contribution.interval_days = intervalDays
          }
        }
        config.periodic_contribution = contribution
      }
    }

    try {
      const backtest = await createBacktest.mutateAsync(config)
      onOpenChange(false)
      if (onSuccess) {
        onSuccess(backtest.id)
      } else {
        navigate(`/backtests/${backtest.id}`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create backtest')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            New Backtest
          </DialogTitle>
          <DialogDescription>
            Test your strategy against historical market data
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2 max-h-[60vh] overflow-y-auto pr-2">
          {/* Error Alert */}
          {error && (
            <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-md">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Strategy Selection */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-muted-foreground" />
              Strategy
            </Label>
            {loadingStrategies ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading strategies...
              </div>
            ) : strategies && strategies.length > 0 ? (
              <div className="space-y-2">
                <select
                  value={strategyId}
                  onChange={(e) => setStrategyId(e.target.value)}
                  className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
                >
                  {strategies.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
                {selectedStrategy && (
                  <p className="text-xs text-muted-foreground">
                    {selectedStrategy.description || 'No description'}
                  </p>
                )}
              </div>
            ) : (
              <Card className="border-dashed">
                <CardContent className="py-4 text-center">
                  <p className="text-sm text-muted-foreground">
                    No strategies found. Create a strategy first.
                  </p>
                  <Button variant="link" size="sm" className="mt-1" onClick={() => {
                    onOpenChange(false)
                    navigate('/strategies/new')
                  }}>
                    Create Strategy →
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>

          <Separator />

          {/* Market Selection */}
          <div className="space-y-3">
            <Label className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              Market
            </Label>

            <div className="grid grid-cols-2 gap-3">
              {/* Asset Class Toggle */}
              <div className="space-y-1.5">
                <span className="text-xs text-muted-foreground">Asset Class</span>
                <div className="flex rounded-md border border-input overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setAssetClass('STOCK')}
                    className={cn(
                      "flex-1 py-2 text-sm font-medium transition-colors",
                      assetClass === 'STOCK'
                        ? "bg-primary text-primary-foreground"
                        : "bg-background hover:bg-muted"
                    )}
                  >
                    Stock
                  </button>
                  <button
                    type="button"
                    onClick={() => setAssetClass('CRYPTO')}
                    className={cn(
                      "flex-1 py-2 text-sm font-medium transition-colors",
                      assetClass === 'CRYPTO'
                        ? "bg-primary text-primary-foreground"
                        : "bg-background hover:bg-muted"
                    )}
                  >
                    Crypto
                  </button>
                </div>
              </div>

              {/* Ticker */}
              <div className="space-y-1.5">
                <span className="text-xs text-muted-foreground">Ticker Symbol</span>
                <Input
                  value={ticker}
                  onChange={(e) => {
                    setTicker(e.target.value.toUpperCase())
                    setTouched(t => ({ ...t, ticker: true }))
                  }}
                  placeholder={assetClass === 'CRYPTO' ? 'BTCUSDT' : 'AAPL'}
                  className={cn(tickerError && "border-destructive")}
                />
                {tickerError && (
                  <p className="text-xs text-destructive">{tickerError}</p>
                )}
              </div>
            </div>
          </div>

          {/* Date Range */}
          <div className="space-y-3">
            <Label className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              Date Range
            </Label>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <span className="text-xs text-muted-foreground">Start Date</span>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => {
                    setStartDate(e.target.value)
                    setTouched(t => ({ ...t, dates: true }))
                  }}
                  className={cn(dateError && "border-destructive")}
                />
              </div>
              <div className="space-y-1.5">
                <span className="text-xs text-muted-foreground">End Date</span>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => {
                    setEndDate(e.target.value)
                    setTouched(t => ({ ...t, dates: true }))
                  }}
                  className={cn(dateError && "border-destructive")}
                />
              </div>
            </div>
            {dateError && (
              <p className="text-xs text-destructive">{dateError}</p>
            )}
          </div>

          {/* Resolution & Capital */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Bar Resolution</Label>
              <select
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
              >
                {resolutionOptions.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label className="flex items-center gap-1 text-xs text-muted-foreground">
                <DollarSign className="h-3 w-3" />
                Initial Capital
              </Label>
              <Input
                type="number"
                value={initialCapital}
                onChange={(e) => {
                  setInitialCapital(e.target.value)
                  setTouched(t => ({ ...t, capital: true }))
                }}
                min="0"
                step="1000"
                className={cn(capitalError && "border-destructive")}
              />
              {capitalError && (
                <p className="text-xs text-destructive">{capitalError}</p>
              )}
            </div>
          </div>

          {/* Advanced Settings Toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-full py-2"
          >
            {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            Advanced Settings
            {(stopLossPct || takeProfitPct || commissionPerTrade || commissionPct || slippagePct || dcaEnabled || Number(leverage) > 1) && (
              <Badge variant="secondary" className="ml-auto text-xs">Configured</Badge>
            )}
          </button>

          {/* Advanced Settings */}
          {showAdvanced && (
            <div className="space-y-4 pl-2 border-l-2 border-border">
              {/* Position Sizing */}
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Position Sizing</Label>
                <div className="grid grid-cols-2 gap-3">
                  <select
                    value={positionSizeType}
                    onChange={(e) => setPositionSizeType(e.target.value)}
                    className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
                  >
                    {POSITION_SIZE_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                  <Input
                    type="number"
                    value={positionSizeValue}
                    onChange={(e) => setPositionSizeValue(e.target.value)}
                    min="0"
                    disabled={positionSizeType === 'full_capital'}
                    placeholder={positionSizeType === 'percent_capital' ? '% of capital' : '$ amount'}
                    className="h-9"
                  />
                </div>
              </div>

              {/* Leverage */}
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Leverage</Label>
                <div className="space-y-1">
                  <Input
                    type="number"
                    value={leverage}
                    onChange={(e) => setLeverage(e.target.value)}
                    min="1"
                    max="125"
                    step="1"
                    placeholder="1"
                    className="h-9 w-24"
                  />
                  {Number(leverage) > 1 && (
                    <p className="text-xs text-amber-600">
                      Leveraged positions can be liquidated if price moves against you
                    </p>
                  )}
                </div>
              </div>

              {/* Risk Management */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Shield className="h-3 w-3" />
                  Risk Management
                </Label>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground">Stop Loss %</span>
                    <Input
                      type="number"
                      value={stopLossPct}
                      onChange={(e) => setStopLossPct(e.target.value)}
                      placeholder="e.g., 2"
                      min="0"
                      step="0.5"
                      className="h-9"
                    />
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground">Take Profit %</span>
                    <Input
                      type="number"
                      value={takeProfitPct}
                      onChange={(e) => setTakeProfitPct(e.target.value)}
                      placeholder="e.g., 5"
                      min="0"
                      step="0.5"
                      className="h-9"
                    />
                  </div>
                </div>
              </div>

              {/* Transaction Costs */}
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Transaction Costs</Label>
                <div className="grid grid-cols-3 gap-2">
                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground">Commission $</span>
                    <Input
                      type="number"
                      value={commissionPerTrade}
                      onChange={(e) => setCommissionPerTrade(e.target.value)}
                      placeholder="0"
                      min="0"
                      step="0.01"
                      className="h-9"
                    />
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground">Commission %</span>
                    <Input
                      type="number"
                      value={commissionPct}
                      onChange={(e) => setCommissionPct(e.target.value)}
                      placeholder="0"
                      min="0"
                      step="0.01"
                      className="h-9"
                    />
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground">Slippage %</span>
                    <Input
                      type="number"
                      value={slippagePct}
                      onChange={(e) => setSlippagePct(e.target.value)}
                      placeholder="0"
                      min="0"
                      step="0.01"
                      className="h-9"
                    />
                  </div>
                </div>
              </div>

              {/* Dollar Cost Averaging */}
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setDcaEnabled(!dcaEnabled)}
                  className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors w-full"
                >
                  <div className={cn(
                    "w-4 h-4 rounded border flex items-center justify-center transition-colors",
                    dcaEnabled ? "bg-primary border-primary" : "border-input"
                  )}>
                    {dcaEnabled && (
                      <svg className="w-3 h-3 text-primary-foreground" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </div>
                  <Repeat className="h-3 w-3" />
                  Dollar Cost Averaging (Periodic Contributions)
                </button>

                {dcaEnabled && (
                  <div className="space-y-3 pt-2 pl-6">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <span className="text-xs text-muted-foreground">Contribution Amount ($)</span>
                        <Input
                          type="number"
                          value={dcaAmount}
                          onChange={(e) => setDcaAmount(e.target.value)}
                          placeholder="e.g., 500"
                          min="0"
                          step="100"
                          className="h-9"
                        />
                      </div>
                      <div className="space-y-1">
                        <span className="text-xs text-muted-foreground">Frequency</span>
                        <select
                          value={dcaFrequency}
                          onChange={(e) => setDcaFrequency(e.target.value)}
                          className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
                        >
                          {DCA_FREQUENCIES.map((f) => (
                            <option key={f.value} value={f.value}>
                              {f.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {dcaFrequency === 'interval_days' && (
                      <div className="space-y-1">
                        <span className="text-xs text-muted-foreground">Interval (days)</span>
                        <Input
                          type="number"
                          value={dcaIntervalDays}
                          onChange={(e) => setDcaIntervalDays(e.target.value)}
                          placeholder="e.g., 14"
                          min="1"
                          step="1"
                          className="h-9 w-32"
                        />
                      </div>
                    )}

                    <label className="flex items-center gap-2 cursor-pointer">
                      <div className={cn(
                        "w-4 h-4 rounded border flex items-center justify-center transition-colors",
                        dcaIncludeStart ? "bg-primary border-primary" : "border-input"
                      )}>
                        {dcaIncludeStart && (
                          <svg className="w-3 h-3 text-primary-foreground" viewBox="0 0 12 12" fill="none">
                            <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        )}
                      </div>
                      <input
                        type="checkbox"
                        checked={dcaIncludeStart}
                        onChange={(e) => setDcaIncludeStart(e.target.checked)}
                        className="sr-only"
                      />
                      <span className="text-xs text-muted-foreground">Include contribution at start date</span>
                    </label>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={createBacktest.isPending || !canSubmit || !strategies?.length}
          >
            {createBacktest.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Backtest
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
