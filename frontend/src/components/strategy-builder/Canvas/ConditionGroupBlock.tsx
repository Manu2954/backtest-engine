import { useState } from 'react'
import { useStrategyBuilderStore, type ConditionTarget } from '@/store/strategyBuilderStore'
import { ConditionBlock } from './ConditionBlock'
import { ConditionGroupFocusModal } from './ConditionGroupFocusModal'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Plus, ArrowRightToLine, ArrowLeftFromLine, TrendingDown, TrendingUp, Maximize2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ConditionInput } from '@/types'

interface ConditionGroupBlockProps {
  type: ConditionTarget
  conditions: ConditionInput[]
  logic: 'AND' | 'OR'
}

export function ConditionGroupBlock({
  type,
  conditions,
  logic,
}: ConditionGroupBlockProps) {
  const setConditionLogic = useStrategyBuilderStore((s) => s.setConditionLogic)
  const addConditionWithId = useStrategyBuilderStore((s) => s.addConditionWithId)
  const [focusModalOpen, setFocusModalOpen] = useState(false)

  const handleToggleLogic = () => {
    const newLogic = logic === 'AND' ? 'OR' : 'AND'
    setConditionLogic(type, newLogic)
  }

  const handleAddCondition = () => {
    addConditionWithId(type)
  }

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
    <>
      <Card className={cn('border-2', getBorderClass())}>
        <CardHeader className="py-3 px-4">
          <div className="flex items-center justify-between gap-2 min-w-0">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <Icon className={cn('h-4 w-4 flex-shrink-0', getIconClass())} />
              <Badge variant="outline" className="text-xs flex-shrink-0">
                {conditions.length}
              </Badge>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFocusModalOpen(true)}
                className="h-7 w-7 p-0"
                title="Focus mode"
              >
                <Maximize2 className="h-3 w-3" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleToggleLogic}
                className="h-7 px-2 text-xs font-mono"
              >
                {logic}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleAddCondition}
                className="h-7 px-2"
              >
                <Plus className="h-3 w-3" />
                <span className="ml-1 hidden sm:inline">Add</span>
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

      <ConditionGroupFocusModal
        open={focusModalOpen}
        onOpenChange={setFocusModalOpen}
        target={type}
        isNamedGroup={false}
      />
    </>
  )
}
