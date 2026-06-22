import { useStrategyBuilderStore } from '@/store/strategyBuilderStore'
import { getIndicatorConfig } from '@/lib/constants'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import type { IndicatorInput } from '@/types'

interface IndicatorInspectorProps {
  indicator: IndicatorInput
}

export function IndicatorInspector({ indicator }: IndicatorInspectorProps) {
  const updateIndicatorById = useStrategyBuilderStore((s) => s.updateIndicatorById)

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
    </div>
  )
}
