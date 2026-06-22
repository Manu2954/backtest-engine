import { useDroppable } from '@dnd-kit/core'
import { useStrategyBuilderStore } from '@/store/strategyBuilderStore'
import { IndicatorBlock } from './IndicatorBlock'
import { ConditionGroupBlock } from './ConditionGroupBlock'
import { cn } from '@/lib/utils'

export function BuilderCanvas() {
  const indicators = useStrategyBuilderStore((s) => s.indicators)
  const entry = useStrategyBuilderStore((s) => s.entry)
  const exit = useStrategyBuilderStore((s) => s.exit)

  const { setNodeRef, isOver } = useDroppable({
    id: 'builder-canvas',
  })

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'min-h-full rounded-lg border-2 border-dashed transition-colors p-6 space-y-6',
        isOver ? 'border-primary bg-primary/5' : 'border-border'
      )}
    >
      {/* Indicators Section */}
      <section>
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
          Indicators ({indicators.length})
        </h3>
        {indicators.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>Drag indicators from the palette to add them here</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {indicators.map((indicator, index) => (
              <IndicatorBlock
                key={indicator.id || `ind-${index}`}
                indicator={indicator}
              />
            ))}
          </div>
        )}
      </section>

      {/* Entry Conditions Section */}
      <section>
        <ConditionGroupBlock
          type="entry"
          title="Entry Conditions"
          conditions={entry.conditions}
          logic={entry.logic}
        />
      </section>

      {/* Exit Conditions Section */}
      <section>
        <ConditionGroupBlock
          type="exit"
          title="Exit Conditions"
          conditions={exit.conditions}
          logic={exit.logic}
        />
      </section>
    </div>
  )
}
