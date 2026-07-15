import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Header } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { StrategyCard } from '@/components/strategy/StrategyCard'
import { useStrategies, useDeleteStrategy, useCreateStrategy } from '@/api/hooks'
import { Plus, Search, FlaskConical } from 'lucide-react'
import type { Strategy } from '@/types'

export function StrategiesPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [strategyToDelete, setStrategyToDelete] = useState<string | null>(null)
  const { data: strategies, isLoading, error } = useStrategies({ limit: 100 })
  const deleteStrategy = useDeleteStrategy()
  const createStrategy = useCreateStrategy()

  const filteredStrategies = strategies?.filter((s) =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleDelete = (id: string) => {
    setStrategyToDelete(id)
    setDeleteDialogOpen(true)
  }

  const confirmDelete = () => {
    if (strategyToDelete) {
      deleteStrategy.mutate(strategyToDelete)
    }
    setDeleteDialogOpen(false)
    setStrategyToDelete(null)
  }

  const handleDuplicate = (strategy: Strategy) => {
    createStrategy.mutate({
      name: `${strategy.name} (Copy)`,
      description: strategy.description,
      indicators: strategy.indicators.map((ind) => ({
        indicator_type: ind.indicator_type,
        alias: ind.alias,
        params: ind.params,
        display_order: ind.display_order,
      })),
      entry_expression: strategy.entry_expression,
      exit_expression: strategy.exit_expression,
    })
  }

  return (
    <>
      <Header title="Strategies">
        <Button asChild>
          <Link to="/strategies/new">
            <Plus className="h-4 w-4" />
            New Strategy
          </Link>
        </Button>
      </Header>

      <div className="p-6 space-y-6">
        {/* Search */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search strategies..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-[180px] rounded-lg" />
            ))}
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-destructive">Failed to load strategies</p>
            <p className="text-sm text-muted-foreground mt-1">
              Please check your connection and try again
            </p>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && filteredStrategies?.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-surface-2 mb-4">
              <FlaskConical className="h-8 w-8 text-muted-foreground" />
            </div>
            {searchQuery ? (
              <>
                <h3 className="text-lg font-semibold">No strategies found</h3>
                <p className="text-muted-foreground mt-1">
                  Try a different search term
                </p>
              </>
            ) : (
              <>
                <h3 className="text-lg font-semibold">No strategies yet</h3>
                <p className="text-muted-foreground mt-1">
                  Create your first trading strategy to get started
                </p>
                <Button asChild className="mt-4">
                  <Link to="/strategies/new">
                    <Plus className="h-4 w-4" />
                    Create Strategy
                  </Link>
                </Button>
              </>
            )}
          </div>
        )}

        {/* Strategy grid */}
        {!isLoading && !error && filteredStrategies && filteredStrategies.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredStrategies.map((strategy) => (
              <StrategyCard
                key={strategy.id}
                strategy={strategy}
                onDelete={handleDelete}
                onDuplicate={handleDuplicate}
              />
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Strategy"
        description="Are you sure you want to delete this strategy? This will also delete all associated backtests. This action cannot be undone."
        confirmText="Delete"
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </>
  )
}
