import { useStrategyBuilderStore } from '@/store/strategyBuilderStore'
import { ConditionBlock } from './ConditionBlock'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Plus, ArrowRightToLine, ArrowLeftFromLine } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ConditionInput } from '@/types'

interface ConditionGroupBlockProps {
  type: 'entry' | 'exit'
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
  const setEntryLogic = useStrategyBuilderStore((s) => s.setEntryLogic)
  const setExitLogic = useStrategyBuilderStore((s) => s.setExitLogic)
  const addConditionWithId = useStrategyBuilderStore((s) => s.addConditionWithId)

  const handleToggleLogic = () => {
    const newLogic = logic === 'AND' ? 'OR' : 'AND'
    if (type === 'entry') {
      setEntryLogic(newLogic)
    } else {
      setExitLogic(newLogic)
    }
  }

  const handleAddCondition = () => {
    addConditionWithId(type)
  }

  const isEntry = type === 'entry'
  const Icon = isEntry ? ArrowRightToLine : ArrowLeftFromLine

  return (
    <Card className={cn(
      'border-2',
      isEntry ? 'border-profit/30' : 'border-loss/30'
    )}>
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className={cn(
              'h-4 w-4',
              isEntry ? 'text-profit' : 'text-loss'
            )} />
            <CardTitle className="text-sm font-semibold">{title}</CardTitle>
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
