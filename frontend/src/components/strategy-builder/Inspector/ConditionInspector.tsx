import { useMemo } from 'react'
import { useStrategyBuilderStore, type ConditionTarget } from '@/store/strategyBuilderStore'
import { OPERATORS, OPERAND_TYPES, OHLCV_COLUMNS, isUnaryOperator, getIndicatorOutputs } from '@/lib/constants'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import type { ConditionInput } from '@/types'

interface ConditionInspectorProps {
  condition: ConditionInput
  target: ConditionTarget
  index: number
}

export function ConditionInspector({ condition, target }: ConditionInspectorProps) {
  const updateConditionById = useStrategyBuilderStore((s) => s.updateConditionById)
  const indicators = useStrategyBuilderStore((s) => s.indicators)

  // Compute indicator aliases using centralized output definitions
  const indicatorAliases = useMemo(() => {
    return indicators.flatMap((ind) =>
      getIndicatorOutputs(ind.indicator_type, ind.alias)
    )
  }, [indicators])

  const isUnary = isUnaryOperator(condition.operator)

  const getValueOptions = (type: string): string[] => {
    if (type === 'INDICATOR') return indicatorAliases
    if (type === 'OHLCV') return [...OHLCV_COLUMNS]
    return []
  }

  const handleChange = (field: string, value: string) => {
    if (!condition.id) return

    // When operand type changes, auto-set a default value
    if (field === 'left_operand_type' || field === 'right_operand_type') {
      const side = field === 'left_operand_type' ? 'left' : 'right'
      const valueField = `${side}_operand_value`
      const options = getValueOptions(value)

      // Set default value based on new type
      let defaultValue = ''
      if (value === 'INDICATOR' && options.length > 0) {
        defaultValue = options[0]
      } else if (value === 'OHLCV') {
        defaultValue = 'close'
      } else if (value === 'SCALAR') {
        defaultValue = '0'
      }

      updateConditionById(condition.id, {
        [field]: value,
        [valueField]: defaultValue
      })
    } else {
      updateConditionById(condition.id, { [field]: value })
    }
  }

  const renderOperandValue = (
    side: 'left' | 'right',
    type: string,
    value: string
  ) => {
    const options = getValueOptions(type)
    const isInput = type === 'SCALAR' || type === 'LOOKBACK'
    const fieldName = `${side}_operand_value`

    if (isInput) {
      return (
        <Input
          value={value}
          placeholder={type === 'LOOKBACK' ? 'column:-offset' : 'Value'}
          onChange={(e) => handleChange(fieldName, e.target.value)}
        />
      )
    }

    return (
      <select
        value={value}
        onChange={(e) => handleChange(fieldName, e.target.value)}
        className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
      >
        {!value && <option value="">-- Select --</option>}
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    )
  }

  // Get display label for the target
  const getTargetLabel = () => {
    switch (target) {
      case 'entry': return 'ENTRY'
      case 'exit': return 'EXIT'
      case 'shortEntry': return 'SHORT ENTRY'
      case 'shortExit': return 'SHORT EXIT'
    }
  }

  // Get badge variant based on target
  const getBadgeVariant = (): 'default' | 'secondary' | 'destructive' | 'outline' => {
    switch (target) {
      case 'entry': return 'default'
      case 'exit': return 'secondary'
      case 'shortEntry': return 'outline'
      case 'shortExit': return 'destructive'
    }
  }

  return (
    <div className="p-4 space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
          Condition Properties
        </h3>
        <Badge variant={getBadgeVariant()}>
          {getTargetLabel()}
        </Badge>
      </div>

      {/* Left Operand */}
      <div className="space-y-3">
        <label className="text-sm font-medium">Left Operand</label>
        <div className="space-y-2">
          <select
            value={condition.left_operand_type}
            onChange={(e) => handleChange('left_operand_type', e.target.value)}
            className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
          >
            {OPERAND_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          {renderOperandValue('left', condition.left_operand_type, condition.left_operand_value)}
        </div>
      </div>

      {/* Operator */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Operator</label>
        <select
          value={condition.operator}
          onChange={(e) => handleChange('operator', e.target.value)}
          className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
        >
          {OPERATORS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label} ({o.description})
            </option>
          ))}
        </select>
      </div>

      {/* Right Operand (hidden for unary operators) */}
      {!isUnary && (
        <div className="space-y-3">
          <label className="text-sm font-medium">Right Operand</label>
          <div className="space-y-2">
            <select
              value={condition.right_operand_type}
              onChange={(e) => handleChange('right_operand_type', e.target.value)}
              className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
            >
              {OPERAND_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            {renderOperandValue('right', condition.right_operand_type, condition.right_operand_value)}
          </div>
        </div>
      )}

      {isUnary && (
        <p className="text-xs text-muted-foreground">
          This operator doesn't require a right operand.
        </p>
      )}
    </div>
  )
}
