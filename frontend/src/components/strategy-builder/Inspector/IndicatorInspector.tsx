import { useState } from 'react'
import { useStrategyBuilderStore } from '@/store/strategyBuilderStore'
import { getIndicatorConfig } from '@/lib/constants'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { IndicatorInput } from '@/types'

interface IndicatorInspectorProps {
  indicator: IndicatorInput
}

export function IndicatorInspector({ indicator }: IndicatorInspectorProps) {
  const updateIndicatorById = useStrategyBuilderStore((s) => s.updateIndicatorById)
  const strategyChartType = useStrategyBuilderStore((s) => s.chartType)
  const [advancedOpen, setAdvancedOpen] = useState(false)

  const config = getIndicatorConfig(indicator.indicator_type)

  const handleAliasChange = (alias: string) => {
    if (indicator.id) {
      updateIndicatorById(indicator.id, { alias })
    }
  }

  const handleParamChange = (key: string, value: string | number) => {
    if (indicator.id) {
      updateIndicatorById(indicator.id, {
        params: { ...indicator.params, [key]: value },
      })
    }
  }

  const handleChartTypeOverride = (value: string) => {
    if (indicator.id) {
      // Empty string means inherit from strategy
      updateIndicatorById(indicator.id, {
        chart_type: value || undefined,
      })
    }
  }

  const inheritedLabel = strategyChartType === 'heikinashi' ? 'Heikin Ashi' : 'Candlestick'

  return (
    <div className="p-4 space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
          Indicator Properties
        </h3>
        <Badge variant="secondary" className="mb-4">
          {indicator.indicator_type}
        </Badge>
      </div>

      {/* Alias */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Alias</label>
        <Input
          value={indicator.alias}
          onChange={(e) => handleAliasChange(e.target.value)}
          placeholder="Indicator alias"
        />
        <p className="text-xs text-muted-foreground">
          Used to reference this indicator in conditions
        </p>
      </div>

      {/* Parameters */}
      {config && config.params.length > 0 && (
        <div className="space-y-4">
          <label className="text-sm font-medium">Parameters</label>
          {[...config.params].map((param) => (
            <div key={param.key} className="space-y-1">
              <label className="text-xs text-muted-foreground">{param.label}</label>
              {param.type === 'select' ? (
                <select
                  value={String(indicator.params[param.key] ?? param.default)}
                  onChange={(e) => handleParamChange(param.key, e.target.value)}
                  className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
                >
                  {param.options?.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <Input
                  type="number"
                  value={Number(indicator.params[param.key] ?? param.default)}
                  onChange={(e) => handleParamChange(param.key, Number(e.target.value))}
                />
              )}
            </div>
          ))}
        </div>
      )}

      {config && config.params.length === 0 && (
        <p className="text-sm text-muted-foreground">
          This indicator has no configurable parameters.
        </p>
      )}

      {/* Advanced Section */}
      <div className="border-t border-border pt-4">
        <button
          type="button"
          onClick={() => setAdvancedOpen(!advancedOpen)}
          className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors w-full"
        >
          {advancedOpen ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          Advanced
        </button>

        {advancedOpen && (
          <div className="mt-4 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Chart Type Override</label>
              <select
                value={indicator.chart_type || ''}
                onChange={(e) => handleChartTypeOverride(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
              >
                <option value="">Inherit from Strategy</option>
                <option value="ohlcv">Candlestick</option>
                <option value="heikinashi">Heikin Ashi</option>
              </select>
              <p className="text-xs text-muted-foreground">
                Inherited: {inheritedLabel}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
