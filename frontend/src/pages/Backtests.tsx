import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Header } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { BacktestCard } from '@/components/backtest/BacktestCard'
import { useBacktests, useDeleteBacktest } from '@/api/hooks'
import { Plus, Search, LineChart } from 'lucide-react'

const STATUS_FILTERS = ['ALL', 'PENDING', 'RUNNING', 'COMPLETE', 'FAILED'] as const
type StatusFilter = (typeof STATUS_FILTERS)[number]

export function BacktestsPage() {
  const [searchParams] = useSearchParams()
  const strategyId = searchParams.get('strategy') || undefined

  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')

  const { data: backtests, isLoading, error } = useBacktests({
    strategy_id: strategyId,
    limit: 100,
  })
  const deleteBacktest = useDeleteBacktest()

  const filteredBacktests = backtests?.filter((b) => {
    // Search filter
    const matchesSearch =
      b.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.asset_class.toLowerCase().includes(searchQuery.toLowerCase())

    // Status filter
    const matchesStatus =
      statusFilter === 'ALL' ||
      b.status === statusFilter ||
      (statusFilter === 'COMPLETE' && b.status === 'COMPLETED')

    return matchesSearch && matchesStatus
  })

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this backtest?')) {
      deleteBacktest.mutate(id)
    }
  }

  // Count by status
  const statusCounts = {
    ALL: backtests?.length || 0,
    PENDING: backtests?.filter((b) => b.status === 'PENDING').length || 0,
    RUNNING: backtests?.filter((b) => b.status === 'RUNNING').length || 0,
    COMPLETE: backtests?.filter((b) => b.status === 'COMPLETE' || b.status === 'COMPLETED').length || 0,
    FAILED: backtests?.filter((b) => b.status === 'FAILED').length || 0,
  }

  return (
    <>
      <Header title="Backtests">
        <Button asChild>
          <Link to="/strategies">
            <Plus className="h-4 w-4" />
            New Backtest
          </Link>
        </Button>
      </Header>

      <div className="p-6 space-y-6">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by ticker..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Status filter */}
          <div className="flex gap-1">
            {STATUS_FILTERS.map((status) => (
              <Button
                key={status}
                variant={statusFilter === status ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setStatusFilter(status)}
                className="text-xs"
              >
                {status === 'ALL' ? 'All' : status.charAt(0) + status.slice(1).toLowerCase()}
                {statusCounts[status] > 0 && (
                  <Badge
                    variant="outline"
                    className="ml-1.5 h-5 px-1.5 text-[10px]"
                  >
                    {statusCounts[status]}
                  </Badge>
                )}
              </Button>
            ))}
          </div>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-[200px] rounded-lg" />
            ))}
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-destructive">Failed to load backtests</p>
            <p className="text-sm text-muted-foreground mt-1">
              Please check your connection and try again
            </p>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && filteredBacktests?.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-surface-2 mb-4">
              <LineChart className="h-8 w-8 text-muted-foreground" />
            </div>
            {searchQuery || statusFilter !== 'ALL' ? (
              <>
                <h3 className="text-lg font-semibold">No backtests found</h3>
                <p className="text-muted-foreground mt-1">
                  Try adjusting your filters
                </p>
                <Button
                  variant="outline"
                  className="mt-4"
                  onClick={() => {
                    setSearchQuery('')
                    setStatusFilter('ALL')
                  }}
                >
                  Clear Filters
                </Button>
              </>
            ) : (
              <>
                <h3 className="text-lg font-semibold">No backtests yet</h3>
                <p className="text-muted-foreground mt-1">
                  Run your first backtest to see results here
                </p>
                <Button asChild className="mt-4">
                  <Link to="/strategies">
                    <Plus className="h-4 w-4" />
                    Run Backtest
                  </Link>
                </Button>
              </>
            )}
          </div>
        )}

        {/* Backtest grid */}
        {!isLoading && !error && filteredBacktests && filteredBacktests.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredBacktests.map((backtest) => (
              <BacktestCard
                key={backtest.id}
                backtest={backtest}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </div>
    </>
  )
}
