import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Header } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useBacktest, useBacktestTrades } from '@/api/hooks'
import { formatPercent, formatDateTimeFull, formatDurationFromTimestamps, cn } from '@/lib/utils'
import { ArrowLeft, Search, Download } from 'lucide-react'

export function BacktestTradesPage() {
  const { id } = useParams<{ id: string }>()
  const { data: backtest, isLoading: loadingBacktest } = useBacktest(id!)
  const { data: trades, isLoading: loadingTrades } = useBacktestTrades(id!, { limit: 1000 })

  const [searchQuery, setSearchQuery] = useState('')
  const [filterDirection, setFilterDirection] = useState<'ALL' | 'LONG' | 'SHORT'>('ALL')
  const [filterResult, setFilterResult] = useState<'ALL' | 'WIN' | 'LOSS'>('ALL')

  const isLoading = loadingBacktest || loadingTrades

  const filteredTrades = trades?.filter((trade) => {
    // Direction filter
    if (filterDirection !== 'ALL' && trade.direction !== filterDirection) {
      return false
    }
    // Result filter
    if (filterResult === 'WIN' && trade.pnl_pct < 0) return false
    if (filterResult === 'LOSS' && trade.pnl_pct >= 0) return false
    // Search filter (by exit reason)
    if (searchQuery && !trade.exit_reason?.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }
    return true
  })

  const handleExportCSV = () => {
    if (!trades || trades.length === 0) return

    const headers = ['Entry Date', 'Exit Date', 'Direction', 'Entry Price', 'Exit Price', 'Shares', 'PnL', 'PnL %', 'Duration (days)', 'Exit Reason']
    const rows = trades.map((t) => [
      t.entry_date,
      t.exit_date,
      t.direction,
      t.entry_price,
      t.exit_price,
      t.shares,
      t.pnl,
      t.pnl_pct,
      t.trade_duration_days,
      t.exit_reason || '',
    ])

    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `trades-${backtest?.ticker || id}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return (
      <>
        <Header title="Trade Log" />
        <div className="p-6 space-y-6">
          <Skeleton className="h-[100px]" />
          <Skeleton className="h-[400px]" />
        </div>
      </>
    )
  }

  return (
    <>
      <Header title="Trade Log">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExportCSV} disabled={!trades?.length}>
            <Download className="h-4 w-4" />
            Export CSV
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link to={`/backtests/${id}`}>
              <ArrowLeft className="h-4 w-4" />
              Back to Report
            </Link>
          </Button>
        </div>
      </Header>

      <div className="p-6 space-y-6">
        {/* Summary Card */}
        {backtest && (
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    {backtest.ticker}
                    <Badge variant="outline">{backtest.asset_class}</Badge>
                  </CardTitle>
                  <CardDescription>
                    {backtest.start_date} → {backtest.end_date}
                  </CardDescription>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold numeric">
                    {trades?.length || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">Total Trades</div>
                </div>
              </div>
            </CardHeader>
          </Card>
        )}

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by exit reason..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="flex gap-1">
            {(['ALL', 'LONG', 'SHORT'] as const).map((dir) => (
              <Button
                key={dir}
                variant={filterDirection === dir ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setFilterDirection(dir)}
              >
                {dir}
              </Button>
            ))}
          </div>
          <div className="flex gap-1">
            {(['ALL', 'WIN', 'LOSS'] as const).map((result) => (
              <Button
                key={result}
                variant={filterResult === result ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setFilterResult(result)}
                className={cn(
                  result === 'WIN' && filterResult === result && 'text-profit',
                  result === 'LOSS' && filterResult === result && 'text-loss'
                )}
              >
                {result}
              </Button>
            ))}
          </div>
        </div>

        {/* Trades Table */}
        <Card>
          <CardContent className="p-0">
            {filteredTrades && filteredTrades.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-surface-1">
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">#</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">Direction</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">Entry</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">Exit</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">Entry Price</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">Exit Price</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">Shares</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">PnL</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">PnL %</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">Duration</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">Exit Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTrades.map((trade, index) => (
                      <tr key={trade.id} className="border-b border-border/50 hover:bg-surface-1/50">
                        <td className="px-4 py-3 text-muted-foreground">{index + 1}</td>
                        <td className="px-4 py-3">
                          <Badge variant={trade.direction === 'LONG' ? 'profit' : 'loss'} className="text-xs">
                            {trade.direction}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">{formatDateTimeFull(trade.entry_date)}</td>
                        <td className="px-4 py-3">{formatDateTimeFull(trade.exit_date)}</td>
                        <td className="px-4 py-3 text-right numeric">${trade.entry_price.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right numeric">${trade.exit_price.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right numeric">{trade.shares.toFixed(4)}</td>
                        <td className={cn(
                          'px-4 py-3 text-right numeric font-medium',
                          trade.pnl >= 0 ? 'text-profit' : 'text-loss'
                        )}>
                          ${trade.pnl.toFixed(2)}
                        </td>
                        <td className={cn(
                          'px-4 py-3 text-right numeric font-medium',
                          trade.pnl_pct >= 0 ? 'text-profit' : 'text-loss'
                        )}>
                          {formatPercent(trade.pnl_pct)}
                        </td>
                        <td className="px-4 py-3 text-right numeric">{formatDurationFromTimestamps(trade.entry_date, trade.exit_date)}</td>
                        <td className="px-4 py-3">
                          {trade.exit_reason && (
                            <Badge variant="outline" className="text-xs">
                              {trade.exit_reason}
                            </Badge>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="flex items-center justify-center py-12">
                <p className="text-muted-foreground">
                  {trades?.length === 0 ? 'No trades recorded' : 'No trades match your filters'}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Summary Stats */}
        {filteredTrades && filteredTrades.length > 0 && (
          <div className="text-sm text-muted-foreground">
            Showing {filteredTrades.length} of {trades?.length} trades
          </div>
        )}
      </div>
    </>
  )
}
