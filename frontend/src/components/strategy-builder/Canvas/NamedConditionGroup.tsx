import { useState } from 'react'
import { useStrategyBuilderStore, type ConditionTarget } from '@/store/strategyBuilderStore'
import { ConditionBlock } from './ConditionBlock'
import { ConditionGroupFocusModal } from './ConditionGroupFocusModal'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Plus,
  ChevronDown,
  ChevronRight,
  Trash2,
  ArrowRightToLine,
  ArrowLeftFromLine,
  TrendingDown,
  TrendingUp,
  Maximize2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ConditionGroupInput } from '@/types'

interface NamedConditionGroupProps {
  target: ConditionTarget
  groupName: string
  group: ConditionGroupInput
}

export function NamedConditionGroup({ target, groupName, group }: NamedConditionGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [isRenaming, setIsRenaming] = useState(false)
  const [newName, setNewName] = useState(groupName)
  const [focusModalOpen, setFocusModalOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  const setGroupLogic = useStrategyBuilderStore((s) => s.setGroupLogic)
  const addConditionWithId = useStrategyBuilderStore((s) => s.addConditionWithId)
  const renameGroup = useStrategyBuilderStore((s) => s.renameGroup)
  const deleteGroup = useStrategyBuilderStore((s) => s.deleteGroup)
  const selectGroup = useStrategyBuilderStore((s) => s.selectGroup)

  const handleToggleLogic = () => {
    const newLogic = group.logic === 'AND' ? 'OR' : 'AND'
    setGroupLogic(target, groupName, newLogic)
  }

  const handleAddCondition = () => {
    addConditionWithId(target, groupName)
  }

  const handleRename = () => {
    if (newName && newName !== groupName && newName.trim()) {
      renameGroup(target, groupName, newName.trim())
    }
    setIsRenaming(false)
  }

  const handleDelete = () => {
    setDeleteDialogOpen(true)
  }

  const confirmDelete = () => {
    deleteGroup(target, groupName)
    setDeleteDialogOpen(false)
  }

  const handleGroupClick = () => {
    selectGroup(target, groupName)
  }

  // Choose icon based on type
  const getIcon = () => {
    if (target === 'entry') return ArrowRightToLine
    if (target === 'exit') return ArrowLeftFromLine
    if (target === 'shortEntry') return TrendingDown
    return TrendingUp // shortExit
  }
  const Icon = getIcon()

  const getBorderClass = () => {
    if (target === 'entry') return 'border-profit/30 hover:border-profit/50'
    if (target === 'exit') return 'border-loss/30 hover:border-loss/50'
    if (target === 'shortEntry') return 'border-orange-500/30 hover:border-orange-500/50'
    return 'border-purple-500/30 hover:border-purple-500/50' // shortExit
  }

  const getIconClass = () => {
    if (target === 'entry') return 'text-profit'
    if (target === 'exit') return 'text-loss'
    if (target === 'shortEntry') return 'text-orange-500'
    return 'text-purple-500' // shortExit
  }

  return (
    <>
      <Card className={cn('border-2 transition-colors', getBorderClass())}>
        <CardHeader className="py-3 px-4">
          <div className="flex items-center justify-between gap-2 min-w-0">
            <div className="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className="h-6 w-6 p-0 flex-shrink-0"
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </Button>

              <Icon className={cn('h-4 w-4 flex-shrink-0', getIconClass())} />

              {isRenaming ? (
                <Input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onBlur={handleRename}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleRename()
                    if (e.key === 'Escape') {
                      setNewName(groupName)
                      setIsRenaming(false)
                    }
                  }}
                  className="h-7 flex-1 min-w-0"
                  autoFocus
                />
              ) : (
                <button
                  onClick={handleGroupClick}
                  className="text-sm font-semibold hover:underline truncate min-w-0"
                >
                  {groupName}
                </button>
              )}

              <Badge variant="outline" className="text-xs flex-shrink-0">
                {group.conditions.length}
              </Badge>
            </div>

            <div className="flex items-center gap-1 flex-shrink-0">
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
                {group.logic}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDelete}
                className="h-7 w-7 p-0 text-destructive hover:text-destructive"
              >
                <Trash2 className="h-3 w-3" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleAddCondition}
                className="h-7 px-2"
              >
                <Plus className="h-3 w-3" />
                <span className="ml-1 hidden lg:inline">Add</span>
              </Button>
            </div>
          </div>
        </CardHeader>

        {isExpanded && (
          <CardContent className="pt-0 pb-4 px-4">
            {group.conditions.length === 0 ? (
              <div className="text-center py-6 text-muted-foreground text-sm border border-dashed border-border rounded-lg">
                No conditions. Click "Add" to create one.
              </div>
            ) : (
              <div className="space-y-2">
                {group.conditions.map((condition, index) => (
                  <div key={condition.id || `cond-${index}`}>
                    {index > 0 && (
                      <div className="text-center text-xs text-muted-foreground font-mono my-2">
                        {group.logic}
                      </div>
                    )}
                    <ConditionBlock condition={condition} />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        )}
      </Card>

      <ConditionGroupFocusModal
        open={focusModalOpen}
        onOpenChange={setFocusModalOpen}
        target={target}
        groupName={groupName}
        isNamedGroup={true}
      />

      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Group"
        description={`Are you sure you want to delete "${groupName}"? This action cannot be undone.`}
        confirmText="Delete"
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </>
  )
}
