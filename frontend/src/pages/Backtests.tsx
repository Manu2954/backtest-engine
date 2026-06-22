import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { Header } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { BacktestCard, NewBacktestModal } from '@/components/backtest'
import { useBacktests, useDeleteBacktest } from '@/api/hooks'
import { createBacktest } from '@/api'
import type { Backtest } from '@/types'
import { Plus, Search, LineChart, AlertTriangle } from 'lucide-react'

const STATUS_FILTERS = ['ALL', 'PENDING', 'RUNNING', 'COMPLETE', 'FAILED'] as const
type StatusFilter = (typeof STATUS_FILTERS)[number]

export function BacktestsPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const strategyId = searchParams.get('strategy') || undefined

  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')
  const [deleteTarget, setDeleteTarget] = useState<Backtest | null>(null)
  const [_rerunning, setRerunning] = useState<string | null>(null)
  const [newBacktestOpen, setNewBacktestOpen] = useState(false)

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

  const handleDeleteClick = (backtest: Backtest) => {
    setDeleteTarget(backtest)
  }

  const handleDeleteConfirm = () => {
    if (deleteTarget) {
      deleteBacktest.mutate(deleteTarget.id)
      setDeleteTarget(null)
    }
  }

  const handleRerun = async (backtest: Backtest) => {
    setRerunning(backtest.id)
    try {
      const newBacktest = await createBacktest({
        strategy_id: backtest.strategy_id,
        ticker: backtest.ticker,
        asset_class: backtest.asset_class,
        start_date: backtest.start_date,
        end_date: backtest.end_date,
        bar_resolution: backtest.bar_resolution,
        initial_capital: backtest.initial_capital,
      })
      navigate(`/backtests/${newBacktest.id}`)
    } catch (err) {
      console.error('Failed to rerun backtest:', err)
    } finally {
      setRerunning(null)
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
        <Button onClick={() => setNewBacktestOpen(true)}>
          <Plus className="h-4 w-4" />
          New Backtest
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
                onDelete={() => handleDeleteClick(backtest)}
                onRerun={() => handleRerun(backtest)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Delete Backtest
            </AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this backtest?
              {deleteTarget && (
                <div className="mt-3 p-3 bg-surface-1 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{deleteTarget.ticker}</Badge>
                    <Badge variant="secondary">{deleteTarget.asset_class}</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    {deleteTarget.start_date} → {deleteTarget.end_date}
                  </p>
                </div>
              )}
              <p className="mt-3 text-destructive font-medium">
                This action cannot be undone.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* New Backtest Modal */}
      <NewBacktestModal
        open={newBacktestOpen}
        onOpenChange={setNewBacktestOpen}
        defaultStrategyId={strategyId}
      />
    </>
  )
}
