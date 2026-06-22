import { Link } from 'react-router-dom'
import {
  Plus,
  LineChart,
  FlaskConical,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Activity,
} from 'lucide-react'
import { Header } from '@/components/layout'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useStrategies } from '@/api/hooks'
import { useBacktests } from '@/api/hooks'
import { formatPercent, formatDate, cn } from '@/lib/utils'

export function Dashboard() {
  const { data: strategies, isLoading: strategiesLoading } = useStrategies({
    limit: 5,
  })
  const { data: backtests, isLoading: backtestsLoading } = useBacktests({
    limit: 5,
  })

  const recentBacktests = backtests?.slice(0, 5) || []
  const completedBacktests =
    recentBacktests.filter((b) => b.status === 'COMPLETE' || b.status === 'COMPLETED') || []
  const avgReturn =
    completedBacktests.length > 0
      ? completedBacktests.reduce(
          (acc, b) => acc + (b.results?.total_return_pct || b.report?.total_return_pct || 0),
          0
        ) / completedBacktests.length
      : 0

  return (
    <>
      <Header title="Dashboard" />

      <div className="p-6 space-y-6">
        {/* Quick Stats */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Strategies
              </CardTitle>
              <FlaskConical className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold numeric">
                {strategiesLoading ? '—' : strategies?.length || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Backtests
              </CardTitle>
              <LineChart className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold numeric">
                {backtestsLoading ? '—' : backtests?.length || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Avg Return
              </CardTitle>
              {avgReturn >= 0 ? (
                <TrendingUp className="h-4 w-4 text-profit" />
              ) : (
                <TrendingDown className="h-4 w-4 text-loss" />
              )}
            </CardHeader>
            <CardContent>
              <div
                className={cn(
                  'text-2xl font-bold numeric',
                  avgReturn >= 0 ? 'text-profit' : 'text-loss'
                )}
              >
                {completedBacktests.length > 0 ? formatPercent(avgReturn) : '—'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Running
              </CardTitle>
              <Activity className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold numeric">
                {backtestsLoading
                  ? '—'
                  : backtests?.filter(
                      (b) => b.status === 'PENDING' || b.status === 'RUNNING'
                    ).length || 0}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer">
            <Link to="/strategies/new">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <Plus className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-base">New Strategy</CardTitle>
                    <CardDescription>
                      Create a trading strategy
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
            </Link>
          </Card>

          <Card className="hover:border-primary/50 transition-colors cursor-pointer">
            <Link to="/backtests">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-chart-3/10">
                    <LineChart className="h-5 w-5 text-chart-3" />
                  </div>
                  <div>
                    <CardTitle className="text-base">Run Backtest</CardTitle>
                    <CardDescription>
                      Test strategy on historical data
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
            </Link>
          </Card>

          <Card className="hover:border-primary/50 transition-colors cursor-pointer">
            <Link to="/chart">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-chart-4/10">
                    <Activity className="h-5 w-5 text-chart-4" />
                  </div>
                  <div>
                    <CardTitle className="text-base">Live Chart</CardTitle>
                    <CardDescription>
                      View market data with indicators
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
            </Link>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Recent Strategies */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Recent Strategies</CardTitle>
                <CardDescription>Your latest trading strategies</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/strategies">
                  View all <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </CardHeader>
            <CardContent>
              {strategiesLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-12 animate-pulse rounded-lg bg-surface-2"
                    />
                  ))}
                </div>
              ) : strategies && strategies.length > 0 ? (
                <div className="space-y-2">
                  {strategies.slice(0, 5).map((strategy) => (
                    <Link
                      key={strategy.id}
                      to={`/strategies/${strategy.id}`}
                      className="flex items-center justify-between rounded-lg p-3 hover:bg-surface-2 transition-colors"
                    >
                      <div>
                        <div className="font-medium">{strategy.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {strategy.indicators.length} indicators
                        </div>
                      </div>
                      <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <FlaskConical className="h-10 w-10 text-muted-foreground mb-3" />
                  <p className="text-muted-foreground">No strategies yet</p>
                  <Button variant="link" asChild className="mt-2">
                    <Link to="/strategies/new">Create your first strategy</Link>
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Backtests */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Recent Backtests</CardTitle>
                <CardDescription>Latest backtest runs</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/backtests">
                  View all <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </CardHeader>
            <CardContent>
              {backtestsLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-12 animate-pulse rounded-lg bg-surface-2"
                    />
                  ))}
                </div>
              ) : backtests && backtests.length > 0 ? (
                <div className="space-y-2">
                  {backtests.slice(0, 5).map((backtest) => {
                    const returnPct =
                      backtest.results?.total_return_pct ||
                      backtest.report?.total_return_pct
                    return (
                      <Link
                        key={backtest.id}
                        to={`/backtests/${backtest.id}`}
                        className="flex items-center justify-between rounded-lg p-3 hover:bg-surface-2 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div>
                            <div className="font-medium">{backtest.ticker}</div>
                            <div className="text-sm text-muted-foreground">
                              {backtest.created_at
                                ? formatDate(backtest.created_at)
                                : '—'}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {backtest.status === 'COMPLETE' ||
                          backtest.status === 'COMPLETED' ? (
                            <span
                              className={cn(
                                'numeric font-medium',
                                returnPct && returnPct >= 0
                                  ? 'text-profit'
                                  : 'text-loss'
                              )}
                            >
                              {returnPct !== undefined
                                ? formatPercent(returnPct)
                                : '—'}
                            </span>
                          ) : (
                            <Badge
                              variant={
                                backtest.status === 'FAILED'
                                  ? 'failed'
                                  : backtest.status === 'RUNNING'
                                  ? 'running'
                                  : 'pending'
                              }
                            >
                              {backtest.status}
                            </Badge>
                          )}
                        </div>
                      </Link>
                    )
                  })}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <LineChart className="h-10 w-10 text-muted-foreground mb-3" />
                  <p className="text-muted-foreground">No backtests yet</p>
                  <Button variant="link" asChild className="mt-2">
                    <Link to="/backtests">Run your first backtest</Link>
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  )
}
