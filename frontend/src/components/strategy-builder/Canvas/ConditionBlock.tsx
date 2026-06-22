import { useStrategyBuilderStore } from '@/store/strategyBuilderStore'
import { OPERATORS, isUnaryOperator } from '@/lib/constants'
import { Button } from '@/components/ui/button'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ConditionInput } from '@/types'

interface ConditionBlockProps {
  condition: ConditionInput
}

export function ConditionBlock({ condition }: ConditionBlockProps) {
  const selectedBlockId = useStrategyBuilderStore((s) => s.selectedBlockId)
  const selectBlock = useStrategyBuilderStore((s) => s.selectBlock)
  const removeConditionById = useStrategyBuilderStore((s) => s.removeConditionById)

  const isSelected = selectedBlockId === condition.id
  const isUnary = isUnaryOperator(condition.operator)

  // Validation: check if condition is complete
  const isLeftEmpty = !condition.left_operand_value?.trim()
  const isRightEmpty = !isUnary && !condition.right_operand_value?.trim()
  const isIncomplete = isLeftEmpty || isRightEmpty

  // Find operator label
  const operatorInfo = OPERATORS.find((o) => o.value === condition.operator)
  const operatorLabel = operatorInfo?.label || condition.operator

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    selectBlock(condition.id || null, 'condition')
  }

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (condition.id) {
      removeConditionById(condition.id)
    }
  }

  // Format operand for display
  const formatOperand = (type: string, value: string) => {
    if (type === 'SCALAR') return value || '?'
    if (type === 'OHLCV') return value || 'price'
    if (type === 'INDICATOR') return value || 'indicator'
    if (type === 'LOOKBACK') return value || 'lookback'
    return value || '?'
  }

  return (
    <div
      onClick={handleClick}
      className={cn(
        'flex items-center gap-2 p-3 rounded-lg border bg-card cursor-pointer transition-all',
        'hover:bg-surface-2',
        isSelected && 'ring-2 ring-primary border-primary',
        isIncomplete && !isSelected && 'border-warning/50 bg-warning/5'
      )}
    >
      {isIncomplete && (
        <span className="text-warning text-xs" title="Incomplete condition">⚠</span>
      )}
      <div className="flex-1 flex items-center gap-2 font-mono text-sm">
        <span className={cn('text-primary', isLeftEmpty && 'text-warning')}>
          {formatOperand(condition.left_operand_type, condition.left_operand_value)}
        </span>
        <span className="text-muted-foreground font-semibold">
          {operatorLabel}
        </span>
        {!isUnary && (
          <span className={cn('text-primary', isRightEmpty && 'text-warning')}>
            {formatOperand(condition.right_operand_type, condition.right_operand_value)}
          </span>
        )}
      </div>
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 shrink-0 text-muted-foreground hover:text-destructive"
        onClick={handleRemove}
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  )
}
