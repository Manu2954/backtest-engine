import { useMemo } from 'react'
import { useStrategyBuilderStore, type ConditionTarget } from '@/store/strategyBuilderStore'
import { IndicatorInspector } from './IndicatorInspector'
import { ConditionInspector } from './ConditionInspector'
import { Settings2, Box } from 'lucide-react'
import type { ConditionGroupInput, ConditionInput } from '@/types'

export function BlockInspector() {
  const selectedBlockId = useStrategyBuilderStore((s) => s.selectedBlockId)
  const selectedBlockType = useStrategyBuilderStore((s) => s.selectedBlockType)
  const selectedGroupName = useStrategyBuilderStore((s) => s.selectedGroupName)
  const indicators = useStrategyBuilderStore((s) => s.indicators)
  const entryGroups = useStrategyBuilderStore((s) => s.entryGroups)
  const exitGroups = useStrategyBuilderStore((s) => s.exitGroups)
  const shortEntryGroups = useStrategyBuilderStore((s) => s.shortEntryGroups)
  const shortExitGroups = useStrategyBuilderStore((s) => s.shortExitGroups)
  const entry = useStrategyBuilderStore((s) => s.entry)
  const exit = useStrategyBuilderStore((s) => s.exit)
  const shortEntry = useStrategyBuilderStore((s) => s.shortEntry)
  const shortExit = useStrategyBuilderStore((s) => s.shortExit)

  // Compute selected indicator
  const selectedIndicator = useMemo(() => {
    if (selectedBlockType !== 'indicator' || !selectedBlockId) return null
    return indicators.find((ind) => ind.id === selectedBlockId) || null
  }, [selectedBlockType, selectedBlockId, indicators])

  // Compute selected condition
  const selectedConditionData = useMemo((): { condition: typeof entry.conditions[0]; target: ConditionTarget; groupName: string; index: number } | null => {
    if (selectedBlockType !== 'condition' || !selectedBlockId) return null

    // Helper to search in groups
    const searchInGroups = (groups: Record<string, ConditionGroupInput>, target: ConditionTarget) => {
      for (const [groupName, group] of Object.entries(groups)) {
        const idx = group.conditions.findIndex((c: ConditionInput) => c.id === selectedBlockId)
        if (idx !== -1) {
          return { condition: group.conditions[idx], target, groupName, index: idx }
        }
      }
      return null
    }

    // Search in named groups first
    let result = searchInGroups(entryGroups, 'entry')
    if (result) return result

    result = searchInGroups(exitGroups, 'exit')
    if (result) return result

    result = searchInGroups(shortEntryGroups, 'shortEntry')
    if (result) return result

    result = searchInGroups(shortExitGroups, 'shortExit')
    if (result) return result

    // Fallback to legacy single groups
    const entryIdx = entry.conditions.findIndex((c) => c.id === selectedBlockId)
    if (entryIdx !== -1) {
      return { condition: entry.conditions[entryIdx], target: 'entry', groupName: 'main', index: entryIdx }
    }

    const exitIdx = exit.conditions.findIndex((c) => c.id === selectedBlockId)
    if (exitIdx !== -1) {
      return { condition: exit.conditions[exitIdx], target: 'exit', groupName: 'main', index: exitIdx }
    }

    const shortEntryIdx = shortEntry.conditions.findIndex((c) => c.id === selectedBlockId)
    if (shortEntryIdx !== -1) {
      return { condition: shortEntry.conditions[shortEntryIdx], target: 'shortEntry', groupName: 'main', index: shortEntryIdx }
    }

    const shortExitIdx = shortExit.conditions.findIndex((c) => c.id === selectedBlockId)
    if (shortExitIdx !== -1) {
      return { condition: shortExit.conditions[shortExitIdx], target: 'shortExit', groupName: 'main', index: shortExitIdx }
    }

    return null
  }, [selectedBlockType, selectedBlockId, entryGroups, exitGroups, shortEntryGroups, shortExitGroups, entry.conditions, exit.conditions, shortEntry.conditions, shortExit.conditions])

  // No selection
  if (!selectedBlockId && !selectedGroupName) {
    return (
      <div className="p-6 flex flex-col items-center justify-center h-full text-muted-foreground">
        <Settings2 className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-sm text-center">
          Select an indicator, condition, or group to edit its properties
        </p>
      </div>
    )
  }

  // Group selected
  if (selectedBlockType === 'group' && selectedGroupName) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Box className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Group: {selectedGroupName}</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Group properties can be edited directly in the canvas.
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
