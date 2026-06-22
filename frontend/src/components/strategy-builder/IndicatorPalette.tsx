import { useState, useMemo } from 'react'
import { useDraggable } from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import { getIndicatorConfigsArray } from '@/lib/constants'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Search } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PaletteItemProps {
  type: string
  name: string
  description: string
}

function PaletteItem({ type, name, description }: PaletteItemProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `palette-${type}`,
    data: {
      type: 'palette-indicator',
      indicatorType: type,
    },
  })

  const style = {
    transform: CSS.Translate.toString(transform),
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={cn(
        'p-3 rounded-lg border border-border bg-card cursor-grab active:cursor-grabbing',
        'hover:border-primary/50 hover:bg-surface-2 transition-colors',
        isDragging && 'opacity-50'
      )}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium text-sm">{name}</span>
        <Badge variant="secondary" className="text-xs">
          {type}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground line-clamp-2">{description}</p>
    </div>
  )
}

export function IndicatorPalette() {
  const [search, setSearch] = useState('')
  const allConfigs = getIndicatorConfigsArray()

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    if (!q) return allConfigs
    return allConfigs.filter(
      (c) =>
        c.type.toLowerCase().includes(q) ||
        c.name.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q)
    )
  }, [search, allConfigs])

  return (
    <div className="p-4 space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Indicators
        </h3>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search indicators..."
            className="pl-9"
          />
        </div>
      </div>

      <div className="space-y-2">
        {filtered.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No indicators found
          </p>
        ) : (
          filtered.map((config) => (
            <PaletteItem
              key={config.type}
              type={config.type}
              name={config.name}
              description={config.description}
            />
          ))
        )}
      </div>

      <div className="pt-4 border-t border-border">
        <p className="text-xs text-muted-foreground text-center">
          Drag indicators to the canvas to add them
        </p>
      </div>
    </div>
  )
}
