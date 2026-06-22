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
import { IndicatorPalette } from './IndicatorPalette'
import { BuilderCanvas } from './Canvas/BuilderCanvas'
import { BlockInspector } from './Inspector/BlockInspector'
import { getStrategy, createStrategy, updateStrategy } from '@/api'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Undo2, Redo2, Save } from 'lucide-react'
import type { Strategy, IndicatorInput, ConditionGroupInput } from '@/types'

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
  const indicators = useStrategyBuilderStore((s) => s.indicators)
  const entry = useStrategyBuilderStore((s) => s.entry)
  const exit = useStrategyBuilderStore((s) => s.exit)
  const historyIndex = useStrategyBuilderStore((s) => s.historyIndex)
  const historyLength = useStrategyBuilderStore((s) => s.history.length)

  // Store actions
  const setName = useStrategyBuilderStore((s) => s.setName)
  const setDescription = useStrategyBuilderStore((s) => s.setDescription)
  const addIndicator = useStrategyBuilderStore((s) => s.addIndicator)
  const loadStrategy = useStrategyBuilderStore((s) => s.loadStrategy)
  const reset = useStrategyBuilderStore((s) => s.reset)
  const undo = useStrategyBuilderStore((s) => s.undo)
  const redo = useStrategyBuilderStore((s) => s.redo)

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
        const entryGroup = strategy.condition_groups.find((g) => g.group_type === 'ENTRY')
        const exitGroup = strategy.condition_groups.find((g) => g.group_type === 'EXIT')
        loadStrategy({
          name: strategy.name,
          description: strategy.description || '',
          indicators: strategy.indicators.map((ind, idx) => ({
            id: `loaded_${idx}`,
            indicator_type: ind.indicator_type,
            alias: ind.alias,
            params: ind.params || {},
            display_order: ind.display_order ?? idx,
          })) as IndicatorInput[],
          entry: entryGroup
            ? {
                logic: entryGroup.logic as 'AND' | 'OR',
                conditions: entryGroup.conditions.map((c, idx) => ({
                  ...c,
                  id: `entry_${idx}`,
                })),
              }
            : { logic: 'AND', conditions: [] },
          exit: exitGroup
            ? {
                logic: exitGroup.logic as 'AND' | 'OR',
                conditions: exitGroup.conditions.map((c, idx) => ({
                  ...c,
                  id: `exit_${idx}`,
                })),
              }
            : { logic: 'AND', conditions: [] },
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
      const payload = {
        name,
        description,
        indicators: indicators.map(({ id: _id, ...rest }) => rest), // Remove client-side IDs
        entry: {
          logic: entry.logic,
          conditions: entry.conditions.map(({ id: _id, ...rest }) => rest),
        } as ConditionGroupInput,
        exit: {
          logic: exit.logic,
          conditions: exit.conditions.map(({ id: _id, ...rest }) => rest),
        } as ConditionGroupInput,
      }

      const strategy = id ? await updateStrategy(id, payload) : await createStrategy(payload)
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
