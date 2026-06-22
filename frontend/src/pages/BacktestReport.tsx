import { useParams, Link } from 'react-router-dom'
import { Header } from '@/components/layout'
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
import { Separator } from '@/components/ui/separator'
import { useBacktest, useBacktestTrades } from '@/api/hooks'
import { formatPercent, formatDate, cn } from '@/lib/utils'
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  DollarSign,
  BarChart3,
  Loader2,
} from 'lucide-react'

function MetricCard({
  label,
  value,
  subValue,
  icon: Icon,
  trend,
}: {
  label: string
  value: string
  subValue?: string
  icon?: React.ComponentType<{ className?: string }>
  trend?: 'up' | 'down' | 'neutral'
}) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p
              className={cn(
                'text-2xl font-bold numeric mt-1',
                trend === 'up' && 'text-profit',
                trend === 'down' && 'text-loss'
              )}
            >
              {value}
            </p>
            {subValue && (
              <p className="text-xs text-muted-foreground mt-0.5">{subValue}</p>
            )}
          </div>
          {Icon && (
            <div
              className={cn(
                'p-2 rounded-lg',
                trend === 'up' && 'bg-profit/10',
                trend === 'down' && 'bg-loss/10',
                trend === 'neutral' && 'bg-surface-2'
              )}
            >
              <Icon
                className={cn(
                  'h-5 w-5',
                  trend === 'up' && 'text-profit',
                  trend === 'down' && 'text-loss',
                  trend === 'neutral' && 'text-muted-foreground'
                )}
              />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function BacktestReportPage() {
  const { id } = useParams<{ id: string }>()
  const { data: backtest, isLoading, error } = useBacktest(id!)
  const { data: trades } = useBacktestTrades(id!, { limit: 10 })

  if (isLoading) {
    return (
      <>
        <Header title="Backtest Report" />
        <div className="p-6 space-y-6">
          <Skeleton className="h-[200px]" />
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <Skeleton key={i} className="h-[100px]" />
            ))}
          </div>
        </div>
      </>
    )
  }

  if (error || !backtest) {
    return (
      <>
        <Header title="Backtest Report" />
        <div className="p-6">
          <div className="flex flex-col items-center justify-center py-16">
            <p className="text-destructive">Failed to load backtest</p>
            <Button asChild variant="outline" className="mt-4">
              <Link to="/backtests">
                <ArrowLeft className="h-4 w-4" />
                Back to Backtests
              </Link>
            </Button>
          </div>
        </div>
      </>
    )
  }

  const results = backtest.results || backtest.report
  const isComplete = backtest.status === 'COMPLETE' || backtest.status === 'COMPLETED'
  const isRunning = backtest.status === 'RUNNING' || backtest.status === 'PENDING'
  const returnPct = results?.total_return_pct

  return (
    <>
      <Header title="Backtest Report">
        <Button asChild variant="ghost" size="sm">
          <Link to="/backtests">
            <ArrowLeft className="h-4 w-4" />
            Back
          </Link>
        </Button>
      </Header>

      <div className="p-6 space-y-6">
        {/* Hero Section */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-3">
                  <CardTitle className="text-2xl">{backtest.ticker}</CardTitle>
                  <Badge variant="outline">{backtest.asset_class}</Badge>
                  <Badge
                    variant={
                      isComplete
                        ? 'complete'
                        : backtest.status === 'FAILED'
                        ? 'failed'
                        : 'running'
                    }
                  >
                    {isRunning && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                    {backtest.status}
                  </Badge>
                </div>
                <CardDescription className="mt-1">
                  {backtest.start_date} → {backtest.end_date} · {backtest.bar_resolution}
                </CardDescription>
              </div>
              {isComplete && returnPct !== undefined && (
                <div className="text-right">
                  <div
                    className={cn(
                      'text-4xl font-bold numeric',
                      returnPct >= 0 ? 'text-profit' : 'text-loss'
                    )}
                  >
                    {formatPercent(returnPct)}
                  </div>
                  <div className="text-sm text-muted-foreground">Total Return</div>
                </div>
              )}
            </div>
          </CardHeader>
        </Card>

        {/* Running state */}
        {isRunning && (
          <Card>
            <CardContent className="flex items-center justify-center py-12">
              <div className="text-center">
                <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
                <p className="mt-4 text-lg font-medium">Running backtest...</p>
                <p className="text-sm text-muted-foreground">
                  This may take a few moments
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Failed state */}
        {backtest.status === 'FAILED' && (
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-lg font-medium text-destructive">Backtest Failed</p>
                <p className="text-sm text-muted-foreground mt-2">
                  {backtest.error_message || 'An unknown error occurred'}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Results */}
        {isComplete && results && (
          <>
            {/* Primary Metrics */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                label="Total Return"
                value={formatPercent(results.total_return_pct || 0)}
                icon={returnPct && returnPct >= 0 ? TrendingUp : TrendingDown}
                trend={returnPct && returnPct >= 0 ? 'up' : 'down'}
              />
              <MetricCard
                label="Sharpe Ratio"
                value={results.sharpe_ratio?.toFixed(2) || '—'}
                subValue="Risk-adjusted return"
                icon={BarChart3}
                trend="neutral"
              />
              <MetricCard
                label="Max Drawdown"
                value={`${results.max_drawdown_pct?.toFixed(1) || 0}%`}
                icon={TrendingDown}
                trend="down"
              />
              <MetricCard
                label="Win Rate"
                value={results.win_rate ? `${(results.win_rate * 100).toFixed(1)}%` : '—'}
                icon={Target}
                trend={results.win_rate && results.win_rate >= 0.5 ? 'up' : 'down'}
              />
            </div>

            {/* Secondary Metrics */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                label="Total Trades"
                value={results.total_trades?.toString() || '0'}
                subValue={`${results.winning_trades || 0}W / ${results.losing_trades || 0}L`}
                icon={Activity}
                trend="neutral"
              />
              <MetricCard
                label="Profit Factor"
                value={results.profit_factor?.toFixed(2) || '—'}
                icon={DollarSign}
                trend={results.profit_factor && results.profit_factor > 1 ? 'up' : 'down'}
              />
              <MetricCard
                label="Avg Win"
                value={results.avg_win ? formatPercent(results.avg_win) : '—'}
                icon={TrendingUp}
                trend="up"
              />
              <MetricCard
                label="Avg Loss"
                value={results.avg_loss ? formatPercent(Math.abs(results.avg_loss)) : '—'}
                icon={TrendingDown}
                trend="down"
              />
            </div>

            {/* Additional Info */}
            <div className="grid gap-4 md:grid-cols-2">
              {/* Trade Statistics */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Trade Statistics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Avg Trade Duration</span>
                    <span className="numeric">{results.avg_trade_duration_days?.toFixed(1) || '—'} days</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Largest Win</span>
                    <span className="numeric text-profit">
                      {results.largest_win ? formatPercent(results.largest_win) : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Largest Loss</span>
                    <span className="numeric text-loss">
                      {results.largest_loss ? formatPercent(Math.abs(results.largest_loss)) : '—'}
                    </span>
                  </div>
                  <Separator />
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">CAGR</span>
                    <span className="numeric">{results.cagr ? formatPercent(results.cagr) : '—'}</span>
                  </div>
                </CardContent>
              </Card>

              {/* Benchmark Comparison */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">vs Buy & Hold</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Benchmark Return</span>
                    <span className="numeric">
                      {results.benchmark_return_pct !== undefined
                        ? formatPercent(results.benchmark_return_pct)
                        : '—'}
                    </span>
                  </div>
                  <Separator />
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Alpha</span>
                    <span
                      className={cn(
                        'numeric',
                        results.alpha && results.alpha >= 0 ? 'text-profit' : 'text-loss'
                      )}
                    >
                      {results.alpha !== undefined ? formatPercent(results.alpha) : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Beta</span>
                    <span className="numeric">{results.beta?.toFixed(2) || '—'}</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Sortino Ratio</span>
                    <span className="numeric">{results.sortino_ratio?.toFixed(2) || '—'}</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Equity Curve Placeholder */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Equity Curve</CardTitle>
                <CardDescription>Strategy performance over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-center h-[300px] border border-dashed border-border rounded-lg">
                  <p className="text-muted-foreground">Chart coming in Phase 3...</p>
                </div>
              </CardContent>
            </Card>

            {/* Recent Trades */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-base">Recent Trades</CardTitle>
                  <CardDescription>Last 10 trades from this backtest</CardDescription>
                </div>
                <Button asChild variant="outline" size="sm">
                  <Link to={`/backtests/${id}/trades`}>View All</Link>
                </Button>
              </CardHeader>
              <CardContent>
                {trades && trades.length > 0 ? (
                  <div className="space-y-2">
                    {trades.map((trade) => (
                      <div
                        key={trade.id}
                        className="flex items-center justify-between py-2 border-b border-border last:border-0"
                      >
                        <div className="flex items-center gap-3">
                          <Badge
                            variant={trade.direction === 'LONG' ? 'profit' : 'loss'}
                            className="text-xs"
                          >
                            {trade.direction}
                          </Badge>
                          <div className="text-sm">
                            <span className="text-muted-foreground">
                              {formatDate(trade.entry_date)}
                            </span>
                            <span className="mx-2">→</span>
                            <span className="text-muted-foreground">
                              {formatDate(trade.exit_date)}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          {trade.exit_reason && (
                            <Badge variant="outline" className="text-xs">
                              {trade.exit_reason}
                            </Badge>
                          )}
                          <span
                            className={cn(
                              'numeric font-medium',
                              trade.pnl_pct >= 0 ? 'text-profit' : 'text-loss'
                            )}
                          >
                            {formatPercent(trade.pnl_pct)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No trades recorded
                  </p>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </>
  )
}
