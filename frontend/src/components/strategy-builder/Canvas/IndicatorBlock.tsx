import { useStrategyBuilderStore } from '@/store/strategyBuilderStore'
import { getIndicatorOutputs } from '@/lib/constants'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { IndicatorInput } from '@/types'

interface IndicatorBlockProps {
  indicator: IndicatorInput
}

export function IndicatorBlock({ indicator }: IndicatorBlockProps) {
  const selectedBlockId = useStrategyBuilderStore((s) => s.selectedBlockId)
  const selectBlock = useStrategyBuilderStore((s) => s.selectBlock)
  const removeIndicatorById = useStrategyBuilderStore((s) => s.removeIndicatorById)

  const outputs = getIndicatorOutputs(indicator.indicator_type, indicator.alias)
  const isSelected = selectedBlockId === indicator.id

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    selectBlock(indicator.id || null, 'indicator')
  }

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (indicator.id) {
      removeIndicatorById(indicator.id)
    }
  }

  // Format params for display
  const paramSummary = Object.entries(indicator.params)
    .slice(0, 3)
    .map(([key, value]) => `${key}=${value}`)
    .join(', ')

  return (
    <Card
      onClick={handleClick}
      className={cn(
        'cursor-pointer transition-all hover:shadow-md',
        isSelected && 'ring-2 ring-primary border-primary'
      )}
    >
      <CardHeader className="py-3 px-4 flex flex-row items-start justify-between space-y-0">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="secondary" className="text-xs shrink-0">
              {indicator.indicator_type}
            </Badge>
          </div>
          <h4 className="font-semibold text-sm truncate">{indicator.alias}</h4>
          {paramSummary && (
            <p className="text-xs text-muted-foreground mt-1 truncate">
              {paramSummary}
            </p>
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
      </CardHeader>
      <CardContent className="pt-0 pb-3 px-4">
        <div className="flex flex-wrap gap-1">
          {outputs.map((output) => (
            <Badge key={output} variant="outline" className="text-xs font-mono">
              {output}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
