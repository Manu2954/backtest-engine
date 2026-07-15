import { useState } from 'react'
import { useStrategyBuilderStore, type ConditionTarget } from '@/store/strategyBuilderStore'
import { ConditionBlock } from './ConditionBlock'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Plus, ArrowRightToLine, ArrowLeftFromLine, TrendingDown, TrendingUp, X, Pencil, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ConditionGroupInput } from '@/types'

interface ConditionGroupFocusModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  target: ConditionTarget
  groupName?: string // For named groups
  isNamedGroup: boolean
}

export function ConditionGroupFocusModal({
  open,
  onOpenChange,
  target,
  groupName,
  isNamedGroup,
}: ConditionGroupFocusModalProps) {
  const addConditionWithId = useStrategyBuilderStore((s) => s.addConditionWithId)
  const setConditionLogic = useStrategyBuilderStore((s) => s.setConditionLogic)
  const setGroupLogic = useStrategyBuilderStore((s) => s.setGroupLogic)
  const renameGroup = useStrategyBuilderStore((s) => s.renameGroup)

  const [isRenaming, setIsRenaming] = useState(false)
  const [newName, setNewName] = useState(groupName || '')

  // Get the appropriate group data
  let group: ConditionGroupInput
  if (isNamedGroup && groupName) {
    const groups = useStrategyBuilderStore((s) => {
      if (target === 'entry') return s.entryGroups
      if (target === 'exit') return s.exitGroups
      if (target === 'shortEntry') return s.shortEntryGroups
      return s.shortExitGroups
    })
    group = groups[groupName]
  } else {
    group = useStrategyBuilderStore((s) => {
      if (target === 'entry') return s.entry
      if (target === 'exit') return s.exit
      if (target === 'shortEntry') return s.shortEntry
      return s.shortExit
    })
  }

  if (!group) return null

  const handleToggleLogic = () => {
    const newLogic = group.logic === 'AND' ? 'OR' : 'AND'
    if (isNamedGroup && groupName) {
      setGroupLogic(target, groupName, newLogic)
    } else {
      setConditionLogic(target, newLogic)
    }
  }

  const handleAddCondition = () => {
    addConditionWithId(target, groupName)
  }

  const handleRename = () => {
    if (isNamedGroup && groupName && newName && newName !== groupName && newName.trim()) {
      renameGroup(target, groupName, newName.trim())
    }
    setIsRenaming(false)
  }

  // Icon and styling based on type
  const getIcon = () => {
    if (target === 'entry') return ArrowRightToLine
    if (target === 'exit') return ArrowLeftFromLine
    if (target === 'shortEntry') return TrendingDown
    return TrendingUp
  }
  const Icon = getIcon()

  const getIconClass = () => {
    if (target === 'entry') return 'text-profit'
    if (target === 'exit') return 'text-loss'
    if (target === 'shortEntry') return 'text-orange-500'
    return 'text-purple-500'
  }

  const getBgClass = () => {
    if (target === 'entry') return 'bg-profit/5'
    if (target === 'exit') return 'bg-loss/5'
    if (target === 'shortEntry') return 'bg-orange-500/5'
    return 'bg-purple-500/5'
  }

  const getTitle = () => {
    if (isNamedGroup && groupName) return groupName
    if (target === 'entry') return 'Entry Conditions'
    if (target === 'exit') return 'Exit Conditions'
    if (target === 'shortEntry') return 'Short Entry Conditions'
    return 'Short Exit Conditions'
  }

  const getSubtitle = () => {
    if (target === 'entry') return 'Long Entry'
    if (target === 'exit') return 'Long Exit'
    if (target === 'shortEntry') return 'Short Entry'
    return 'Short Exit'
  }

  return (
    <>
      {/* Backdrop overlay - excludes inspector panel on the right */}
      <div
        className={cn(
          'fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity duration-200',
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        style={{
          right: '320px', // Width of inspector panel (w-80)
          pointerEvents: open ? 'auto' : 'none',
        }}
        onClick={() => onOpenChange(false)}
      />

      {/* Centered modal */}
      <div
        className={cn(
          'fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] max-h-[85vh] bg-background rounded-lg shadow-2xl z-50 transition-all duration-200 flex flex-col',
          open ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'
        )}
        style={{
          marginRight: '160px', // Half of inspector width to center in remaining space
        }}
      >
        {/* Header */}
        <div className={cn('border-b px-6 py-4', getBgClass())}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <Icon className={cn('h-5 w-5 flex-shrink-0', getIconClass())} />
              <div className="min-w-0 flex-1">
                {isNamedGroup && isRenaming ? (
                  <div className="flex items-center gap-2">
                    <Input
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRename()
                        if (e.key === 'Escape') {
                          setNewName(groupName || '')
                          setIsRenaming(false)
                        }
                      }}
                      className="h-8 max-w-xs"
                      autoFocus
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={handleRename}
                      className="h-8 w-8"
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <>
                    <h2 className="text-lg font-semibold truncate">{getTitle()}</h2>
                    <p className="text-sm text-muted-foreground">{getSubtitle()}</p>
                  </>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {isNamedGroup && !isRenaming && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsRenaming(true)}
                  className="h-8 w-8"
                  title="Rename group"
                >
                  <Pencil className="h-4 w-4" />
                </Button>
              )}
              <Badge variant="outline" className="text-sm">
                {group.conditions.length}
              </Badge>
              <Button
                variant="outline"
                size="sm"
                onClick={handleToggleLogic}
                className="h-8 px-3 text-sm font-mono"
              >
                {group.logic}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onOpenChange(false)}
                className="h-8 w-8"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Content - scrollable */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {group.conditions.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground border border-dashed border-border rounded-lg">
              <p className="text-sm">No conditions yet.</p>
              <p className="text-xs mt-1">Click "Add Condition" to create one.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {group.conditions.map((condition, index) => (
                <div key={condition.id || `cond-${index}`}>
                  {index > 0 && (
                    <div className="text-center text-sm text-muted-foreground font-mono my-3 py-1.5 bg-muted/30 rounded">
                      {group.logic}
                    </div>
                  )}
                  <ConditionBlock condition={condition} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer - sticky */}
        <div className="border-t px-6 py-4 flex items-center gap-2">
          <Button
            onClick={handleAddCondition}
            variant="outline"
            className="flex-1"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Condition
          </Button>
          <Button onClick={() => onOpenChange(false)} variant="default" className="px-8">
            Done
          </Button>
        </div>
      </div>
    </>
  )
}
