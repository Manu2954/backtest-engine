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
import { useStrategies } from '@/api/hooks'
import { useCreateBacktest } from '@/api/hooks'
import { Play, Loader2 } from 'lucide-react'
import type { BacktestConfig } from '@/types'

interface NewBacktestModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: (backtestId: string) => void
  defaultStrategyId?: string
}

const STOCK_RESOLUTIONS = ['1m', '5m', '15m', '1h', '1d']
const CRYPTO_RESOLUTIONS = ['1m', '5m', '15m', '1h', '4h', '1d']

const POSITION_SIZE_TYPES = [
  { value: 'full_capital', label: 'Full Capital' },
  { value: 'percent_capital', label: 'Percent of Capital' },
  { value: 'fixed_amount', label: 'Fixed Amount' },
]

export function NewBacktestModal({
  open,
  onOpenChange,
  onSuccess,
  defaultStrategyId,
}: NewBacktestModalProps) {
  const navigate = useNavigate()
  const { data: strategies, isLoading: loadingStrategies } = useStrategies({ limit: 100 })
  const createBacktest = useCreateBacktest()

  // Form state
  const [strategyId, setStrategyId] = useState(defaultStrategyId || '')
  const [ticker, setTicker] = useState('AAPL')
  const [assetClass, setAssetClass] = useState<'STOCK' | 'CRYPTO'>('STOCK')
  const [startDate, setStartDate] = useState('2020-01-01')
  const [endDate, setEndDate] = useState('2023-12-31')
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

  const [error, setError] = useState<string | null>(null)

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
    if (!resolutions.includes(resolution)) {
      setResolution('1d')
    }
  }, [assetClass, resolution])

  const resolutionOptions = assetClass === 'CRYPTO' ? CRYPTO_RESOLUTIONS : STOCK_RESOLUTIONS

  const handleSubmit = async () => {
    if (!strategyId) {
      setError('Please select a strategy')
      return
    }

    if (!ticker.trim()) {
      setError('Please enter a ticker symbol')
      return
    }

    if (!startDate || !endDate) {
      setError('Please select date range')
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
      ticker: ticker.toUpperCase(),
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
      if (!isNaN(sl) && sl > 0) {
        config.stop_loss_pct = sl
      }
    }

    if (takeProfitPct) {
      const tp = Number(takeProfitPct)
      if (!isNaN(tp) && tp > 0) {
        config.take_profit_pct = tp
      }
    }

    if (commissionPerTrade) {
      const comm = Number(commissionPerTrade)
      if (!isNaN(comm) && comm >= 0) {
        config.commission_per_trade = comm
      }
    }

    if (commissionPct) {
      const commP = Number(commissionPct)
      if (!isNaN(commP) && commP >= 0) {
        config.commission_pct = commP
      }
    }

    if (slippagePct) {
      const slip = Number(slippagePct)
      if (!isNaN(slip) && slip >= 0) {
        config.slippage_pct = slip
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
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>New Backtest</DialogTitle>
          <DialogDescription>
            Configure and run a new backtest for your trading strategy
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {error && (
            <div className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded">
              {error}
            </div>
          )}

          {/* Strategy Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Strategy</label>
            {loadingStrategies ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading strategies...
              </div>
            ) : strategies && strategies.length > 0 ? (
              <select
                value={strategyId}
                onChange={(e) => setStrategyId(e.target.value)}
                className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {strategies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            ) : (
              <div className="text-sm text-muted-foreground">
                No strategies found. Create a strategy first.
              </div>
            )}
          </div>

          {/* Ticker and Asset Class */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Ticker</label>
              <Input
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                placeholder="AAPL, BTC-USD, etc."
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Asset Class</label>
              <select
                value={assetClass}
                onChange={(e) => setAssetClass(e.target.value as 'STOCK' | 'CRYPTO')}
                className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="STOCK">Stock</option>
                <option value="CRYPTO">Crypto</option>
              </select>
            </div>
          </div>

          {/* Date Range */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Start Date</label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">End Date</label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>

          {/* Resolution and Initial Capital */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Bar Resolution</label>
              <select
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {resolutionOptions.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Initial Capital ($)</label>
              <Input
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(e.target.value)}
                min="0"
                step="1000"
              />
            </div>
          </div>

          {/* Position Sizing */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Position Sizing</label>
              <select
                value={positionSizeType}
                onChange={(e) => setPositionSizeType(e.target.value)}
                className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {POSITION_SIZE_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {positionSizeType === 'percent_capital'
                  ? 'Percent (%)'
                  : positionSizeType === 'fixed_amount'
                  ? 'Amount ($)'
                  : 'Value'}
              </label>
              <Input
                type="number"
                value={positionSizeValue}
                onChange={(e) => setPositionSizeValue(e.target.value)}
                min="0"
                disabled={positionSizeType === 'full_capital'}
              />
            </div>
          </div>

          {/* Optional: Risk Management */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">
              Risk Management (Optional)
            </label>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Stop Loss %</label>
                <Input
                  type="number"
                  value={stopLossPct}
                  onChange={(e) => setStopLossPct(e.target.value)}
                  placeholder="e.g., 2"
                  min="0"
                  step="0.1"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Take Profit %</label>
                <Input
                  type="number"
                  value={takeProfitPct}
                  onChange={(e) => setTakeProfitPct(e.target.value)}
                  placeholder="e.g., 5"
                  min="0"
                  step="0.1"
                />
              </div>
            </div>
          </div>

          {/* Optional: Transaction Costs */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">
              Transaction Costs (Optional)
            </label>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Commission ($)</label>
                <Input
                  type="number"
                  value={commissionPerTrade}
                  onChange={(e) => setCommissionPerTrade(e.target.value)}
                  placeholder="0"
                  min="0"
                  step="0.01"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Commission %</label>
                <Input
                  type="number"
                  value={commissionPct}
                  onChange={(e) => setCommissionPct(e.target.value)}
                  placeholder="0"
                  min="0"
                  step="0.01"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Slippage %</label>
                <Input
                  type="number"
                  value={slippagePct}
                  onChange={(e) => setSlippagePct(e.target.value)}
                  placeholder="0"
                  min="0"
                  step="0.01"
                />
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={createBacktest.isPending || !strategyId}
          >
            {createBacktest.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
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
