import { useMemo } from 'react'
import { useStrategyBuilderStore } from '@/store/strategyBuilderStore'
import { IndicatorInspector } from './IndicatorInspector'
import { ConditionInspector } from './ConditionInspector'
import { Settings2 } from 'lucide-react'

export function BlockInspector() {
  const selectedBlockId = useStrategyBuilderStore((s) => s.selectedBlockId)
  const selectedBlockType = useStrategyBuilderStore((s) => s.selectedBlockType)
  const indicators = useStrategyBuilderStore((s) => s.indicators)
  const entry = useStrategyBuilderStore((s) => s.entry)
  const exit = useStrategyBuilderStore((s) => s.exit)

  // Compute selected indicator
  const selectedIndicator = useMemo(() => {
    if (selectedBlockType !== 'indicator' || !selectedBlockId) return null
    return indicators.find((ind) => ind.id === selectedBlockId) || null
  }, [selectedBlockType, selectedBlockId, indicators])

  // Compute selected condition
  const selectedConditionData = useMemo(() => {
    if (selectedBlockType !== 'condition' || !selectedBlockId) return null

    const entryIdx = entry.conditions.findIndex((c) => c.id === selectedBlockId)
    if (entryIdx !== -1) {
      return { condition: entry.conditions[entryIdx], target: 'entry' as const, index: entryIdx }
    }

    const exitIdx = exit.conditions.findIndex((c) => c.id === selectedBlockId)
    if (exitIdx !== -1) {
      return { condition: exit.conditions[exitIdx], target: 'exit' as const, index: exitIdx }
    }

    return null
  }, [selectedBlockType, selectedBlockId, entry.conditions, exit.conditions])

  // No selection
  if (!selectedBlockId || !selectedBlockType) {
    return (
      <div className="p-6 flex flex-col items-center justify-center h-full text-muted-foreground">
        <Settings2 className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-sm text-center">
          Select an indicator or condition to edit its properties
        </p>
      </div>
    )
  }

  // Indicator selected
  if (selectedBlockType === 'indicator') {
    if (!selectedIndicator) {
      return (
        <div className="p-6 text-muted-foreground text-sm">
          Indicator not found
        </div>
      )
    }
    return <IndicatorInspector indicator={selectedIndicator} />
  }

  // Condition selected
  if (selectedBlockType === 'condition') {
    if (!selectedConditionData) {
      return (
        <div className="p-6 text-muted-foreground text-sm">
          Condition not found
        </div>
      )
    }
    return (
      <ConditionInspector
        condition={selectedConditionData.condition}
        target={selectedConditionData.target}
        index={selectedConditionData.index}
      />
    )
  }

  return null
}
