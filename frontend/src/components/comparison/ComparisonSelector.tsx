import { useBacktests } from '@/api/hooks'
import { useComparisonStore } from '@/store/comparisonStore'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { formatPercent, cn } from '@/lib/utils'
import { Check } from 'lucide-react'

interface ComparisonSelectorProps {
  onCompare: () => void
}

export function ComparisonSelector({ onCompare }: ComparisonSelectorProps) {
  const { data: backtests, isLoading, error } = useBacktests({ limit: 100 })
  const {
    selectedIds,
    addToComparison,
    removeFromComparison,
    clearComparison,
    isSelected,
    canAddMore,
    maxSelected,
  } = useComparisonStore()

  const completedBacktests = backtests?.filter(
    (bt) => bt.status === 'COMPLETE' || bt.status === 'COMPLETED'
  ) || []

  const handleToggle = (id: string) => {
    if (isSelected(id)) {
      removeFromComparison(id)
    } else if (canAddMore()) {
      addToComparison(id)
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Select Backtests</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8">
          <p className="text-destructive text-center">Failed to load backtests</p>
        </CardContent>
      </Card>
    )
  }

  if (completedBacktests.length === 0) {
    return (
      <Card>
        <CardContent className="py-8">
          <p className="text-muted-foreground text-center">
            No completed backtests available. Run some backtests first.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Select Backtests</CardTitle>
            <CardDescription>
              Choose 2-{maxSelected} backtests to compare
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">
              {selectedIds.length} / {maxSelected} selected
            </Badge>
            {selectedIds.length > 0 && (
              <Button variant="outline" size="sm" onClick={clearComparison}>
                Clear
              </Button>
            )}
            <Button
              size="sm"
              onClick={onCompare}
              disabled={selectedIds.length < 2}
            >
              Compare
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {completedBacktests.map((bt) => {
            const selected = isSelected(bt.id)
            const disabled = !selected && !canAddMore()
            const results = bt.results || bt.report
            const returnPct = results?.total_return_pct

            return (
              <div
                key={bt.id}
                onClick={() => !disabled && handleToggle(bt.id)}
                className={cn(
                  'flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors',
                  selected
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:bg-surface-2',
                  disabled && 'opacity-50 cursor-not-allowed'
                )}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      'w-5 h-5 rounded border flex items-center justify-center',
                      selected
                        ? 'bg-primary border-primary'
                        : 'border-border'
                    )}
                  >
                    {selected && <Check className="h-3 w-3 text-primary-foreground" />}
                  </div>
                  <div>
                    <div className="font-medium">{bt.ticker}</div>
                    <div className="text-xs text-muted-foreground">
                      {bt.start_date} → {bt.end_date}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Badge variant="outline">{bt.asset_class}</Badge>
                  <span
                    className={cn(
                      'numeric font-medium',
                      returnPct !== undefined && returnPct >= 0
                        ? 'text-profit'
                        : 'text-loss'
                    )}
                  >
                    {returnPct !== undefined ? formatPercent(returnPct) : '—'}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
