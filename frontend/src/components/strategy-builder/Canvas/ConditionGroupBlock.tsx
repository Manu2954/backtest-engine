import { useStrategyBuilderStore, type ConditionTarget } from '@/store/strategyBuilderStore'
import { ConditionBlock } from './ConditionBlock'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Plus, ArrowRightToLine, ArrowLeftFromLine, TrendingDown, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ConditionInput } from '@/types'

interface ConditionGroupBlockProps {
  type: ConditionTarget
  title: string
  conditions: ConditionInput[]
  logic: 'AND' | 'OR'
}

export function ConditionGroupBlock({
  type,
  title,
  conditions,
  logic,
}: ConditionGroupBlockProps) {
  const setConditionLogic = useStrategyBuilderStore((s) => s.setConditionLogic)
  const addConditionWithId = useStrategyBuilderStore((s) => s.addConditionWithId)

  const handleToggleLogic = () => {
    const newLogic = logic === 'AND' ? 'OR' : 'AND'
    setConditionLogic(type, newLogic)
  }

  const handleAddCondition = () => {
    addConditionWithId(type)
  }

  // Determine styling based on type
  const isShort = type === 'shortEntry' || type === 'shortExit'

  // Choose icon based on type
  const getIcon = () => {
    if (type === 'entry') return ArrowRightToLine
    if (type === 'exit') return ArrowLeftFromLine
    if (type === 'shortEntry') return TrendingDown
    return TrendingUp // shortExit
  }
  const Icon = getIcon()

  // Border color: entry/shortEntry = profit (green), exit/shortExit = loss (red)
  // But for shorts, we can use orange to differentiate
  const getBorderClass = () => {
    if (type === 'entry') return 'border-profit/30'
    if (type === 'exit') return 'border-loss/30'
    if (type === 'shortEntry') return 'border-orange-500/30'
    return 'border-purple-500/30' // shortExit
  }

  const getIconClass = () => {
    if (type === 'entry') return 'text-profit'
    if (type === 'exit') return 'text-loss'
    if (type === 'shortEntry') return 'text-orange-500'
    return 'text-purple-500' // shortExit
  }

  return (
    <Card className={cn('border-2', getBorderClass())}>
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className={cn('h-4 w-4', getIconClass())} />
            <CardTitle className="text-sm font-semibold">{title}</CardTitle>
            {isShort && (
              <Badge variant="outline" className="text-xs bg-muted">
                Short
              </Badge>
            )}
            <Badge variant="outline" className="text-xs">
              {conditions.length}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleToggleLogic}
              className="h-7 text-xs font-mono"
            >
              {logic}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleAddCondition}
              className="h-7"
            >
              <Plus className="h-3 w-3 mr-1" />
              Add
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0 pb-4 px-4">
        {conditions.length === 0 ? (
          <div className="text-center py-6 text-muted-foreground text-sm border border-dashed border-border rounded-lg">
            No conditions. Click "Add" to create one.
          </div>
        ) : (
          <div className="space-y-2">
            {conditions.map((condition, index) => (
              <div key={condition.id || `cond-${index}`}>
                {index > 0 && (
                  <div className="text-center text-xs text-muted-foreground font-mono my-2">
                    {logic}
                  </div>
                )}
                <ConditionBlock condition={condition} />
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
