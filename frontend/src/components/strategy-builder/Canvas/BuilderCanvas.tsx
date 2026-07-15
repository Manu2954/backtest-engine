import { useDroppable } from '@dnd-kit/core'
import { useStrategyBuilderStore } from '@/store/strategyBuilderStore'
import { IndicatorBlock } from './IndicatorBlock'
import { ConditionGroupBlock } from './ConditionGroupBlock'
import { NamedConditionGroup } from './NamedConditionGroup'
import { ExpressionEditor } from './ExpressionEditor'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Plus, FolderTree } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useState } from 'react'

export function BuilderCanvas() {
  const indicators = useStrategyBuilderStore((s) => s.indicators)
  const entry = useStrategyBuilderStore((s) => s.entry)
  const exit = useStrategyBuilderStore((s) => s.exit)
  const shortEntry = useStrategyBuilderStore((s) => s.shortEntry)
  const shortExit = useStrategyBuilderStore((s) => s.shortExit)

  const entryGroups = useStrategyBuilderStore((s) => s.entryGroups)
  const exitGroups = useStrategyBuilderStore((s) => s.exitGroups)
  const shortEntryGroups = useStrategyBuilderStore((s) => s.shortEntryGroups)
  const shortExitGroups = useStrategyBuilderStore((s) => s.shortExitGroups)

  const createGroup = useStrategyBuilderStore((s) => s.createGroup)

  const [newGroupNames, setNewGroupNames] = useState({
    entry: '',
    exit: '',
    shortEntry: '',
    shortExit: '',
  })

  const [groupErrors, setGroupErrors] = useState({
    entry: '',
    exit: '',
    shortEntry: '',
    shortExit: '',
  })

  const [switchDialog, setSwitchDialog] = useState<{
    open: boolean
    target: 'entry' | 'exit' | 'shortEntry' | 'shortExit' | null
    groupName: string
    error: string
  }>({
    open: false,
    target: null,
    groupName: '',
    error: '',
  })

  const { setNodeRef, isOver } = useDroppable({
    id: 'builder-canvas',
  })

  const handleCreateGroup = (target: 'entry' | 'exit' | 'shortEntry' | 'shortExit') => {
    const name = newGroupNames[target].trim()
    if (!name) {
      setGroupErrors((prev) => ({ ...prev, [target]: 'Please enter a group name' }))
      return
    }
    if (/\s/.test(name)) {
      setGroupErrors((prev) => ({ ...prev, [target]: 'No spaces allowed. Use underscores or camelCase.' }))
      return
    }
    setGroupErrors((prev) => ({ ...prev, [target]: '' }))
    createGroup(target, name)
    setNewGroupNames((prev) => ({ ...prev, [target]: '' }))
  }

  const handleSwitchToNamedGroups = () => {
    if (!switchDialog.target) return
    const name = switchDialog.groupName.trim()
    if (!name) {
      setSwitchDialog((prev) => ({ ...prev, error: 'Please enter a group name' }))
      return
    }
    if (/\s/.test(name)) {
      setSwitchDialog((prev) => ({ ...prev, error: 'Group names cannot contain spaces. Use underscores or camelCase.' }))
      return
    }
    createGroup(switchDialog.target, name)
    setSwitchDialog({ open: false, target: null, groupName: '', error: '' })
  }

  const openSwitchDialog = (target: 'entry' | 'exit' | 'shortEntry' | 'shortExit') => {
    setSwitchDialog({ open: true, target, groupName: '', error: '' })
  }

  // Check if we're using named groups or legacy single groups
  const hasEntryGroups = Object.keys(entryGroups).length > 0
  const hasExitGroups = Object.keys(exitGroups).length > 0
  const hasShortEntryGroups = Object.keys(shortEntryGroups).length > 0
  const hasShortExitGroups = Object.keys(shortExitGroups).length > 0

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

      {/* Long Conditions */}
      <section>
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
          Long Positions
        </h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Entry Conditions */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <h4 className="text-xs font-medium text-muted-foreground">Entry Conditions</h4>
            </div>

            {hasEntryGroups ? (
              <>
                <ExpressionEditor
                  target="entry"
                  groupNames={Object.keys(entryGroups)}
                />
                {Object.entries(entryGroups).map(([groupName, group]) => (
                  <NamedConditionGroup
                    key={groupName}
                    target="entry"
                    groupName={groupName}
                    group={group}
                  />
                ))}
                <div className="space-y-1">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Group name..."
                      value={newGroupNames.entry}
                      onChange={(e) => {
                        setNewGroupNames((prev) => ({ ...prev, entry: e.target.value }))
                        setGroupErrors((prev) => ({ ...prev, entry: '' }))
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleCreateGroup('entry')
                      }}
                      className={cn(
                        "flex-1 px-3 py-2 text-sm rounded-md border bg-background",
                        groupErrors.entry ? 'border-destructive' : 'border-input'
                      )}
                    />
                    <Button onClick={() => handleCreateGroup('entry')} size="sm">
                      <Plus className="h-4 w-4 mr-1" />
                      Create Group
                    </Button>
                  </div>
                  {groupErrors.entry && (
                    <p className="text-xs text-destructive">{groupErrors.entry}</p>
                  )}
                </div>
              </>
            ) : (
              <>
                <ConditionGroupBlock
                  type="entry"
                  conditions={entry.conditions}
                  logic={entry.logic}
                />
                <Button
                  onClick={() => openSwitchDialog('entry')}
                  variant="outline"
                  size="sm"
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Switch to Named Groups
                </Button>
              </>
            )}
          </div>

          {/* Exit Conditions */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <h4 className="text-xs font-medium text-muted-foreground">Exit Conditions</h4>
            </div>

            {hasExitGroups ? (
              <>
                <ExpressionEditor
                  target="exit"
                  groupNames={Object.keys(exitGroups)}
                />
                {Object.entries(exitGroups).map(([groupName, group]) => (
                  <NamedConditionGroup
                    key={groupName}
                    target="exit"
                    groupName={groupName}
                    group={group}
                  />
                ))}
                <div className="space-y-1">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Group name..."
                      value={newGroupNames.exit}
                      onChange={(e) => {
                        setNewGroupNames((prev) => ({ ...prev, exit: e.target.value }))
                        setGroupErrors((prev) => ({ ...prev, exit: '' }))
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleCreateGroup('exit')
                      }}
                      className={cn(
                        "flex-1 px-3 py-2 text-sm rounded-md border bg-background",
                        groupErrors.exit ? 'border-destructive' : 'border-input'
                      )}
                    />
                    <Button onClick={() => handleCreateGroup('exit')} size="sm">
                      <Plus className="h-4 w-4 mr-1" />
                      Create Group
                    </Button>
                  </div>
                  {groupErrors.exit && (
                    <p className="text-xs text-destructive">{groupErrors.exit}</p>
                  )}
                </div>
              </>
            ) : (
              <>
                <ConditionGroupBlock
                  type="exit"
                  conditions={exit.conditions}
                  logic={exit.logic}
                />
                <Button
                  onClick={() => openSwitchDialog('exit')}
                  variant="outline"
                  size="sm"
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Switch to Named Groups
                </Button>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Short Conditions */}
      <section>
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
          Short Positions
        </h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Short Entry Conditions */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <h4 className="text-xs font-medium text-muted-foreground">Short Entry Conditions</h4>
            </div>

            {hasShortEntryGroups ? (
              <>
                <ExpressionEditor
                  target="shortEntry"
                  groupNames={Object.keys(shortEntryGroups)}
                />
                {Object.entries(shortEntryGroups).map(([groupName, group]) => (
                  <NamedConditionGroup
                    key={groupName}
                    target="shortEntry"
                    groupName={groupName}
                    group={group}
                  />
                ))}
                <div className="space-y-1">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Group name..."
                      value={newGroupNames.shortEntry}
                      onChange={(e) => {
                        setNewGroupNames((prev) => ({ ...prev, shortEntry: e.target.value }))
                        setGroupErrors((prev) => ({ ...prev, shortEntry: '' }))
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleCreateGroup('shortEntry')
                      }}
                      className={cn(
                        "flex-1 px-3 py-2 text-sm rounded-md border bg-background",
                        groupErrors.shortEntry ? 'border-destructive' : 'border-input'
                      )}
                    />
                    <Button onClick={() => handleCreateGroup('shortEntry')} size="sm">
                      <Plus className="h-4 w-4 mr-1" />
                      Create Group
                    </Button>
                  </div>
                  {groupErrors.shortEntry && (
                    <p className="text-xs text-destructive">{groupErrors.shortEntry}</p>
                  )}
                </div>
              </>
            ) : (
              <>
                <ConditionGroupBlock
                  type="shortEntry"
                  conditions={shortEntry.conditions}
                  logic={shortEntry.logic}
                />
                <Button
                  onClick={() => openSwitchDialog('shortEntry')}
                  variant="outline"
                  size="sm"
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Switch to Named Groups
                </Button>
              </>
            )}
          </div>

          {/* Short Exit Conditions */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <h4 className="text-xs font-medium text-muted-foreground">Short Exit Conditions</h4>
            </div>

            {hasShortExitGroups ? (
              <>
                <ExpressionEditor
                  target="shortExit"
                  groupNames={Object.keys(shortExitGroups)}
                />
                {Object.entries(shortExitGroups).map(([groupName, group]) => (
                  <NamedConditionGroup
                    key={groupName}
                    target="shortExit"
                    groupName={groupName}
                    group={group}
                  />
                ))}
                <div className="space-y-1">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Group name..."
                      value={newGroupNames.shortExit}
                      onChange={(e) => {
                        setNewGroupNames((prev) => ({ ...prev, shortExit: e.target.value }))
                        setGroupErrors((prev) => ({ ...prev, shortExit: '' }))
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleCreateGroup('shortExit')
                      }}
                      className={cn(
                        "flex-1 px-3 py-2 text-sm rounded-md border bg-background",
                        groupErrors.shortExit ? 'border-destructive' : 'border-input'
                      )}
                    />
                    <Button onClick={() => handleCreateGroup('shortExit')} size="sm">
                      <Plus className="h-4 w-4 mr-1" />
                      Create Group
                    </Button>
                  </div>
                  {groupErrors.shortExit && (
                    <p className="text-xs text-destructive">{groupErrors.shortExit}</p>
                  )}
                </div>
              </>
            ) : (
              <>
                <ConditionGroupBlock
                  type="shortExit"
                  conditions={shortExit.conditions}
                  logic={shortExit.logic}
                />
                <Button
                  onClick={() => openSwitchDialog('shortExit')}
                  variant="outline"
                  size="sm"
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Switch to Named Groups
                </Button>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Switch to Named Groups Dialog */}
      <Dialog open={switchDialog.open} onOpenChange={(open) => !open && setSwitchDialog({ open: false, target: null, groupName: '', error: '' })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FolderTree className="h-5 w-5 text-primary" />
              Switch to Named Groups
            </DialogTitle>
            <DialogDescription>
              Create your first named condition group. Named groups allow you to build complex strategies using boolean expressions (AND, OR, NOT).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label htmlFor="group-name" className="text-sm font-medium">
              Group Name
            </label>
            <Input
              id="group-name"
              placeholder="e.g., oversold, trend_up, breakout"
              value={switchDialog.groupName}
              onChange={(e) =>
                setSwitchDialog((prev) => ({ ...prev, groupName: e.target.value, error: '' }))
              }
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSwitchToNamedGroups()
              }}
              className={cn(switchDialog.error && 'border-red-500')}
              autoFocus
            />
            {switchDialog.error && (
              <p className="text-sm text-red-600">{switchDialog.error}</p>
            )}
            <p className="text-xs text-muted-foreground">
              No spaces allowed. Use underscores (e.g., "trend_up") or camelCase (e.g., "trendUp").
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSwitchDialog({ open: false, target: null, groupName: '', error: '' })}>
              Cancel
            </Button>
            <Button onClick={handleSwitchToNamedGroups} disabled={!switchDialog.groupName.trim()}>
              Create Group
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
