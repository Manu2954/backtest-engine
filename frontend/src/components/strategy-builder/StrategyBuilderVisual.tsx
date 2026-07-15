import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  DndContext,
  DragOverlay,
  useSensor,
  useSensors,
  PointerSensor,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core'
import { useStrategyBuilderStore } from '@/store/strategyBuilderStore'
import { useUnsavedChanges } from '@/hooks/useUnsavedChanges'
import { IndicatorPalette } from './IndicatorPalette'
import { BuilderCanvas } from './Canvas/BuilderCanvas'
import { BlockInspector } from './Inspector/BlockInspector'
import { getStrategy, createStrategy, updateStrategy } from '@/api'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { HelpTooltip } from '@/components/ui/help-tooltip'
import { Undo2, Redo2, Save } from 'lucide-react'
import type { Strategy, IndicatorInput, ConditionGroupInput, StrategyCreate } from '@/types'

interface DragData {
  type: 'palette-indicator' | 'canvas-indicator' | 'condition'
  indicatorType?: string
  id?: string
}

export function StrategyBuilderVisual() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeDrag, setActiveDrag] = useState<DragData | null>(null)

  // Store state
  const name = useStrategyBuilderStore((s) => s.name)
  const description = useStrategyBuilderStore((s) => s.description)
  const chartType = useStrategyBuilderStore((s) => s.chartType)
  const indicators = useStrategyBuilderStore((s) => s.indicators)
  const entry = useStrategyBuilderStore((s) => s.entry)
  const exit = useStrategyBuilderStore((s) => s.exit)
  const shortEntry = useStrategyBuilderStore((s) => s.shortEntry)
  const shortExit = useStrategyBuilderStore((s) => s.shortExit)
  const entryGroups = useStrategyBuilderStore((s) => s.entryGroups)
  const exitGroups = useStrategyBuilderStore((s) => s.exitGroups)
  const shortEntryGroups = useStrategyBuilderStore((s) => s.shortEntryGroups)
  const shortExitGroups = useStrategyBuilderStore((s) => s.shortExitGroups)
  const getExpression = useStrategyBuilderStore((s) => s.getExpression)
  const historyIndex = useStrategyBuilderStore((s) => s.historyIndex)
  const historyLength = useStrategyBuilderStore((s) => s.history.length)
  const isDirty = useStrategyBuilderStore((s) => s.isDirty)

  // Warn on navigation away with unsaved changes
  useUnsavedChanges(isDirty)


  // Store actions
  const setName = useStrategyBuilderStore((s) => s.setName)
  const setDescription = useStrategyBuilderStore((s) => s.setDescription)
  const setChartType = useStrategyBuilderStore((s) => s.setChartType)
  const addIndicator = useStrategyBuilderStore((s) => s.addIndicator)
  const loadStrategy = useStrategyBuilderStore((s) => s.loadStrategy)
  const markSaved = useStrategyBuilderStore((s) => s.markSaved)
  const reset = useStrategyBuilderStore((s) => s.reset)
  const undo = useStrategyBuilderStore((s) => s.undo)
  const redo = useStrategyBuilderStore((s) => s.redo)

  // Helper function to convert user-friendly operators to backend format
  const convertExpressionToBackend = (expression: string): string => {
    if (!expression) return ''
    return expression
      .replace(/\bAND\b/g, '&&')
      .replace(/\bOR\b/g, '||')
      .replace(/\bNOT\b/g, '!')
  }

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  )

  // Load existing strategy
  useEffect(() => {
    if (!id) {
      reset()
      return
    }
    setLoading(true)
    getStrategy(id)
      .then((strategy: Strategy) => {
        // Organize condition groups by type and name
        const entryGroups: Record<string, ConditionGroupInput> = {}
        const exitGroups: Record<string, ConditionGroupInput> = {}
        const shortEntryGroups: Record<string, ConditionGroupInput> = {}
        const shortExitGroups: Record<string, ConditionGroupInput> = {}

        // Legacy single groups (for backward compatibility)
        let entryGroup: ConditionGroupInput | undefined
        let exitGroup: ConditionGroupInput | undefined
        let shortEntryGroup: ConditionGroupInput | undefined
        let shortExitGroup: ConditionGroupInput | undefined

        // Parse condition groups
        strategy.condition_groups.forEach((g) => {
          const group: ConditionGroupInput = {
            logic: g.logic as 'AND' | 'OR',
            conditions: g.conditions.map((c, idx) => ({
              ...c,
              id: `${g.group_type}_${g.group_name || 'main'}_${idx}`,
            })),
          }

          if (g.group_name) {
            // Named group mode
            switch (g.group_type) {
              case 'ENTRY':
                entryGroups[g.group_name] = group
                break
              case 'EXIT':
                exitGroups[g.group_name] = group
                break
              case 'SHORT_ENTRY':
                shortEntryGroups[g.group_name] = group
                break
              case 'SHORT_EXIT':
                shortExitGroups[g.group_name] = group
                break
            }
          } else {
            // Legacy single group mode
            switch (g.group_type) {
              case 'ENTRY':
                entryGroup = group
                break
              case 'EXIT':
                exitGroup = group
                break
              case 'SHORT_ENTRY':
                shortEntryGroup = group
                break
              case 'SHORT_EXIT':
                shortExitGroup = group
                break
            }
          }
        })

        loadStrategy({
          name: strategy.name,
          description: strategy.description || '',
          chartType: strategy.chart_type || 'ohlcv',
          indicators: strategy.indicators.map((ind, idx) => ({
            id: `loaded_${idx}`,
            indicator_type: ind.indicator_type,
            alias: ind.alias,
            params: ind.params || {},
            display_order: ind.display_order ?? idx,
          })) as IndicatorInput[],
          // Named groups and expressions
          entryGroups,
          exitGroups,
          shortEntryGroups,
          shortExitGroups,
          entryExpression: strategy.entry_expression || '',
          exitExpression: strategy.exit_expression || '',
          shortEntryExpression: strategy.short_entry_expression || '',
          shortExitExpression: strategy.short_exit_expression || '',
          // Legacy single groups
          entry: entryGroup || { logic: 'AND', conditions: [] },
          exit: exitGroup || { logic: 'AND', conditions: [] },
          shortEntry: shortEntryGroup || { logic: 'AND', conditions: [] },
          shortExit: shortExitGroup || { logic: 'AND', conditions: [] },
        })
      })
      .catch((err: Error) => setError(err.message || 'Failed to load strategy'))
      .finally(() => setLoading(false))
  }, [id, loadStrategy, reset])

  // Handle drag start
  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event
    setActiveDrag(active.data.current as DragData)
  }

  // Handle drag end
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    setActiveDrag(null)

    if (!over) return

    const dragData = active.data.current as DragData

    // Dropping palette indicator on canvas
    if (dragData.type === 'palette-indicator' && over.id === 'builder-canvas') {
      if (dragData.indicatorType) {
        addIndicator(dragData.indicatorType)
      }
    }
  }

  // Save strategy
  const handleSave = async () => {
    if (!name.trim()) {
      setError('Strategy name is required')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const payload: StrategyCreate = {
        name,
        description,
        chart_type: chartType,
        indicators: indicators.map(({ id: _id, ...rest }) => rest), // Remove client-side IDs
      }

      // Check if using named groups or legacy single groups
      const hasEntryGroups = Object.keys(entryGroups).length > 0
      const hasExitGroups = Object.keys(exitGroups).length > 0
      const hasShortEntryGroups = Object.keys(shortEntryGroups).length > 0
      const hasShortExitGroups = Object.keys(shortExitGroups).length > 0

      if (hasEntryGroups) {
        // Named groups mode
        payload.entry_groups = Object.fromEntries(
          Object.entries(entryGroups).map(([name, group]) => [
            name,
            {
              logic: group.logic,
              conditions: group.conditions.map(({ id: _id, ...rest }) => rest),
            },
          ])
        )
        payload.entry_expression = convertExpressionToBackend(getExpression('entry'))
      } else {
        // Legacy single group mode
        payload.entry = {
          logic: entry.logic,
          conditions: entry.conditions.map(({ id: _id, ...rest }) => rest),
        } as ConditionGroupInput
      }

      if (hasExitGroups) {
        payload.exit_groups = Object.fromEntries(
          Object.entries(exitGroups).map(([name, group]) => [
            name,
            {
              logic: group.logic,
              conditions: group.conditions.map(({ id: _id, ...rest }) => rest),
            },
          ])
        )
        payload.exit_expression = convertExpressionToBackend(getExpression('exit'))
      } else {
        payload.exit = {
          logic: exit.logic,
          conditions: exit.conditions.map(({ id: _id, ...rest }) => rest),
        } as ConditionGroupInput
      }

      // Only include short conditions if they have any conditions defined
      if (hasShortEntryGroups) {
        payload.short_entry_groups = Object.fromEntries(
          Object.entries(shortEntryGroups).map(([name, group]) => [
            name,
            {
              logic: group.logic,
              conditions: group.conditions.map(({ id: _id, ...rest }) => rest),
            },
          ])
        )
        payload.short_entry_expression = convertExpressionToBackend(getExpression('shortEntry'))
      } else if (shortEntry.conditions.length > 0) {
        payload.short_entry = {
          logic: shortEntry.logic,
          conditions: shortEntry.conditions.map(({ id: _id, ...rest }) => rest),
        }
      }

      if (hasShortExitGroups) {
        payload.short_exit_groups = Object.fromEntries(
          Object.entries(shortExitGroups).map(([name, group]) => [
            name,
            {
              logic: group.logic,
              conditions: group.conditions.map(({ id: _id, ...rest }) => rest),
            },
          ])
        )
        payload.short_exit_expression = convertExpressionToBackend(getExpression('shortExit'))
      } else if (shortExit.conditions.length > 0) {
        payload.short_exit = {
          logic: shortExit.logic,
          conditions: shortExit.conditions.map(({ id: _id, ...rest }) => rest),
        }
      }

      const strategy = id ? await updateStrategy(id, payload) : await createStrategy(payload)
      markSaved()
      navigate(`/strategies/${strategy.id}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setLoading(false)
    }
  }

  if (loading && id) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-primary" />
      </div>
    )
  }

  return (
    <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <div className="h-screen flex flex-col bg-background">
        {/* Header */}
        <div className="border-b border-border px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold">
              {id ? 'Edit Strategy' : 'New Strategy'}
            </h1>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Strategy Name"
              className="w-64"
            />
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description (optional)"
              className="w-64"
            />
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-muted-foreground whitespace-nowrap">Chart Type:</label>
              <select
                value={chartType}
                onChange={(e) => setChartType(e.target.value)}
                className="px-3 py-2 rounded-md border border-input bg-background text-sm"
              >
                <option value="ohlcv">Candlestick</option>
                <option value="heikinashi">Heikin Ashi</option>
              </select>
              {chartType !== 'ohlcv' && (
                <HelpTooltip
                  text={
                    <>
                      Indicators computed on {chartType === 'heikinashi' ? 'Heikin Ashi' : chartType} prices.
                      <br />
                      Trade fills use real prices.
                    </>
                  }
                />
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={undo}
              disabled={historyIndex < 0}
            >
              <Undo2 className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={redo}
              disabled={historyIndex >= historyLength - 1}
            >
              <Redo2 className="h-4 w-4" />
            </Button>
            <Button size="sm" onClick={handleSave} disabled={loading}>
              <Save className="h-4 w-4 mr-2" />
              Save
            </Button>
          </div>
        </div>

        {error && (
          <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm">
            {error}
          </div>
        )}

        {/* Main Content - 3 Column Layout */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left: Indicator Palette */}
          <div className="w-64 border-r border-border overflow-y-auto">
            <IndicatorPalette />
          </div>

          {/* Center: Canvas */}
          <div className="flex-1 overflow-y-auto p-4">
            <BuilderCanvas />
          </div>

          {/* Right: Inspector */}
          <div className="w-80 border-l border-border overflow-y-auto">
            <BlockInspector />
          </div>
        </div>

        {/* Drag Overlay */}
        <DragOverlay>
          {activeDrag?.type === 'palette-indicator' && activeDrag.indicatorType && (
            <Card className="w-48 opacity-80 shadow-lg">
              <CardHeader className="py-2 px-3">
                <CardTitle className="text-sm">{activeDrag.indicatorType}</CardTitle>
              </CardHeader>
            </Card>
          )}
        </DragOverlay>
      </div>
    </DndContext>
  )
}

export default StrategyBuilderVisual
