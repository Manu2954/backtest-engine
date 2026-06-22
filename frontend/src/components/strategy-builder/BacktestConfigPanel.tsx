import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStrategyBuilderStore } from '@/store/strategyBuilderStore'
import { createStrategy, updateStrategy, createBacktest } from '@/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ChevronUp, ChevronDown, Play } from 'lucide-react'
import type { ConditionGroupInput } from '@/types'

interface BacktestConfigPanelProps {
  strategyId?: string
}

export function BacktestConfigPanel({ strategyId }: BacktestConfigPanelProps) {
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Backtest config
  const [ticker, setTicker] = useState('AAPL')
  const [assetClass, setAssetClass] = useState<'STOCK' | 'CRYPTO'>('STOCK')
  const [startDate, setStartDate] = useState('2020-01-01')
  const [endDate, setEndDate] = useState('2023-12-31')
  const [initialCapital, setInitialCapital] = useState('10000')
  const [resolution, setResolution] = useState('1d')

  // Store
  const name = useStrategyBuilderStore((s) => s.name)
  const description = useStrategyBuilderStore((s) => s.description)
  const indicators = useStrategyBuilderStore((s) => s.indicators)
  const entry = useStrategyBuilderStore((s) => s.entry)
  const exit = useStrategyBuilderStore((s) => s.exit)

  const resolutionOptions =
    assetClass === 'CRYPTO'
      ? ['1m', '5m', '15m', '1h', '4h', '1d']
      : ['1m', '5m', '15m', '1h', '1d']

  const handleRunBacktest = async () => {
    if (!name.trim()) {
      setError('Strategy name is required')
      return
    }

    if (indicators.length === 0) {
      setError('Add at least one indicator')
      return
    }

    if (entry.conditions.length === 0) {
      setError('Add at least one entry condition')
      return
    }

    // Validate all conditions have operand values
    const allConditions = [...entry.conditions, ...exit.conditions]
    for (const cond of allConditions) {
      if (!cond.left_operand_value?.trim()) {
        setError('All conditions must have a left operand value')
        return
      }
      // Right operand required for non-unary operators
      const unaryOps = ['IS_RISING', 'IS_FALLING', 'IS_TRUE', 'IS_FALSE']
      if (!unaryOps.includes(cond.operator) && !cond.right_operand_value?.trim()) {
        setError('All conditions must have a right operand value')
        return
      }
    }

    setLoading(true)
    setError(null)

    try {
      // Save strategy first
      const strategyPayload = {
        name,
        description,
        indicators: indicators.map(({ id: _id, ...rest }) => rest),
        entry: {
          logic: entry.logic,
          conditions: entry.conditions.map(({ id: _id, ...rest }) => rest),
        } as ConditionGroupInput,
        exit: {
          logic: exit.logic,
          conditions: exit.conditions.map(({ id: _id, ...rest }) => rest),
        } as ConditionGroupInput,
      }

      const strategy = strategyId
        ? await updateStrategy(strategyId, strategyPayload)
        : await createStrategy(strategyPayload)

      // Create backtest
      const backtest = await createBacktest({
        strategy_id: strategy.id,
        ticker,
        asset_class: assetClass,
        start_date: startDate,
        end_date: endDate,
        bar_resolution: resolution,
        initial_capital: Number(initialCapital),
      })

      navigate(`/backtests/${backtest.id}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to run backtest')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border-t border-border bg-card">
      {/* Collapsed Bar */}
      <div
        className="px-4 py-2 flex items-center justify-between cursor-pointer hover:bg-surface-2"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium">Backtest Configuration</span>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline">{ticker}</Badge>
            <span>{startDate} → {endDate}</span>
            <Badge variant="outline">${Number(initialCapital).toLocaleString()}</Badge>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={(e) => {
              e.stopPropagation()
              handleRunBacktest()
            }}
            disabled={loading}
          >
            <Play className="h-4 w-4 mr-2" />
            {loading ? 'Running...' : 'Run Backtest'}
          </Button>
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Expanded Config */}
      {expanded && (
        <div
          className="px-4 py-4 border-t border-border space-y-4"
          onClick={(e) => e.stopPropagation()}
        >
          {error && (
            <div className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded">
              {error}
            </div>
          )}

          <div className="grid grid-cols-6 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Ticker</label>
              <Input
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="h-9"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Asset Class</label>
              <select
                value={assetClass}
                onChange={(e) => setAssetClass(e.target.value as 'STOCK' | 'CRYPTO')}
                className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm"
              >
                <option value="STOCK">Stock</option>
                <option value="CRYPTO">Crypto</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Start Date</label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="h-9"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">End Date</label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="h-9"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Resolution</label>
              <select
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm"
              >
                {resolutionOptions.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Initial Capital</label>
              <Input
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(e.target.value)}
                className="h-9"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
