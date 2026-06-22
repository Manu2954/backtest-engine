import { useParams, Link, useNavigate } from 'react-router-dom'
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
import { useStrategy, useDeleteStrategy, useBacktests } from '@/api/hooks'
import { INDICATOR_CONFIGS, OPERATORS } from '@/lib/constants'
import {
  ArrowLeft,
  Edit,
  Trash2,
  Play,
  FlaskConical,
} from 'lucide-react'

export function StrategyDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: strategy, isLoading, error } = useStrategy(id!)
  const deleteStrategy = useDeleteStrategy()
  const { data: backtests } = useBacktests({ strategy_id: id, limit: 5 })

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this strategy?')) {
      deleteStrategy.mutate(id!, {
        onSuccess: () => navigate('/strategies'),
      })
    }
  }

  if (isLoading) {
    return (
      <>
        <Header title="Strategy" />
        <div className="p-6 space-y-6">
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[300px]" />
        </div>
      </>
    )
  }

  if (error || !strategy) {
    return (
      <>
        <Header title="Strategy" />
        <div className="p-6">
          <div className="flex flex-col items-center justify-center py-16">
            <p className="text-destructive">Failed to load strategy</p>
            <Button asChild variant="outline" className="mt-4">
              <Link to="/strategies">
                <ArrowLeft className="h-4 w-4" />
                Back to Strategies
              </Link>
            </Button>
          </div>
        </div>
      </>
    )
  }

  const entryGroups = strategy.condition_groups.filter((g) => g.group_type === 'ENTRY')
  const exitGroups = strategy.condition_groups.filter((g) => g.group_type === 'EXIT')
  const shortEntryGroups = strategy.condition_groups.filter((g) => g.group_type === 'SHORT_ENTRY')
  const shortExitGroups = strategy.condition_groups.filter((g) => g.group_type === 'SHORT_EXIT')

  const getOperatorLabel = (op: string) => {
    const found = OPERATORS.find((o) => o.value === op)
    return found?.label || op
  }

  return (
    <>
      <Header title="Strategy">
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link to="/strategies">
              <ArrowLeft className="h-4 w-4" />
              Back
            </Link>
          </Button>
        </div>
      </Header>

      <div className="p-6 space-y-6">
        {/* Header Card */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-2xl">{strategy.name}</CardTitle>
                {strategy.description && (
                  <CardDescription className="mt-1">
                    {strategy.description}
                  </CardDescription>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button asChild variant="outline" size="sm">
                  <Link to={`/strategies/${id}/edit`}>
                    <Edit className="h-4 w-4" />
                    Edit
                  </Link>
                </Button>
                <Button asChild size="sm">
                  <Link to={`/backtests?strategy=${id}`}>
                    <Play className="h-4 w-4" />
                    Run Backtest
                  </Link>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={handleDelete}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Indicators */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Indicators</CardTitle>
              <CardDescription>
                {strategy.indicators.length} indicator{strategy.indicators.length !== 1 ? 's' : ''} configured
              </CardDescription>
            </CardHeader>
            <CardContent>
              {strategy.indicators.length > 0 ? (
                <div className="space-y-3">
                  {strategy.indicators.map((ind) => {
                    const config = INDICATOR_CONFIGS[ind.indicator_type as keyof typeof INDICATOR_CONFIGS]
                    return (
                      <div
                        key={ind.id || ind.alias}
                        className="flex items-start justify-between p-3 rounded-lg bg-surface-2"
                      >
                        <div>
                          <div className="font-medium">
                            {config?.name || ind.indicator_type}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            Alias: <code className="text-xs">{ind.alias}</code>
                          </div>
                        </div>
                        <div className="text-right text-sm">
                          {Object.entries(ind.params).map(([key, value]) => (
                            <div key={key} className="text-muted-foreground">
                              {key}: <span className="text-foreground">{String(value)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No indicators configured
                </p>
              )}
            </CardContent>
          </Card>

          {/* Conditions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Conditions</CardTitle>
              <CardDescription>Entry and exit rules</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Entry Expression */}
              {strategy.entry_expression && (
                <div>
                  <div className="text-sm font-medium mb-1 text-profit">Entry Expression</div>
                  <code className="block p-2 rounded bg-surface-2 text-xs overflow-x-auto">
                    {strategy.entry_expression}
                  </code>
                </div>
              )}

              {/* Entry Groups */}
              {entryGroups.length > 0 && (
                <div>
                  <div className="text-sm font-medium mb-2 text-profit">Entry Conditions</div>
                  {entryGroups.map((group, gi) => (
                    <div key={group.id || gi} className="mb-2 p-2 rounded bg-surface-2">
                      <div className="text-xs text-muted-foreground mb-1">
                        Logic: {group.logic}
                      </div>
                      {group.conditions.map((cond, ci) => (
                        <div key={cond.id || ci} className="text-sm py-0.5">
                          <code className="text-xs">
                            {cond.left_operand_value} {getOperatorLabel(cond.operator)} {cond.right_operand_value}
                          </code>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}

              <Separator />

              {/* Exit Expression */}
              {strategy.exit_expression && (
                <div>
                  <div className="text-sm font-medium mb-1 text-loss">Exit Expression</div>
                  <code className="block p-2 rounded bg-surface-2 text-xs overflow-x-auto">
                    {strategy.exit_expression}
                  </code>
                </div>
              )}

              {/* Exit Groups */}
              {exitGroups.length > 0 && (
                <div>
                  <div className="text-sm font-medium mb-2 text-loss">Exit Conditions</div>
                  {exitGroups.map((group, gi) => (
                    <div key={group.id || gi} className="mb-2 p-2 rounded bg-surface-2">
                      <div className="text-xs text-muted-foreground mb-1">
                        Logic: {group.logic}
                      </div>
                      {group.conditions.map((cond, ci) => (
                        <div key={cond.id || ci} className="text-sm py-0.5">
                          <code className="text-xs">
                            {cond.left_operand_value} {getOperatorLabel(cond.operator)} {cond.right_operand_value}
                          </code>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}

              {/* Short conditions if any */}
              {(shortEntryGroups.length > 0 || shortExitGroups.length > 0) && (
                <>
                  <Separator />
                  <div className="text-xs text-muted-foreground">
                    + {shortEntryGroups.length + shortExitGroups.length} short condition group(s)
                  </div>
                </>
              )}

              {!strategy.entry_expression &&
                !strategy.exit_expression &&
                entryGroups.length === 0 &&
                exitGroups.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No conditions configured
                  </p>
                )}
            </CardContent>
          </Card>
        </div>

        {/* Recent Backtests */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base">Recent Backtests</CardTitle>
              <CardDescription>Backtests using this strategy</CardDescription>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link to={`/backtests?strategy=${id}`}>View All</Link>
            </Button>
          </CardHeader>
          <CardContent>
            {backtests && backtests.length > 0 ? (
              <div className="space-y-2">
                {backtests.map((bt) => {
                  const results = bt.results || bt.report
                  const returnPct = results?.total_return_pct
                  return (
                    <Link
                      key={bt.id}
                      to={`/backtests/${bt.id}`}
                      className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-surface-2 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-medium">{bt.ticker}</span>
                        <Badge variant="outline" className="text-xs">
                          {bt.bar_resolution}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2">
                        {bt.status === 'COMPLETE' || bt.status === 'COMPLETED' ? (
                          <span
                            className={`numeric font-medium ${
                              returnPct && returnPct >= 0 ? 'text-profit' : 'text-loss'
                            }`}
                          >
                            {returnPct !== undefined ? `${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%` : '—'}
                          </span>
                        ) : (
                          <Badge
                            variant={bt.status === 'FAILED' ? 'failed' : 'running'}
                          >
                            {bt.status}
                          </Badge>
                        )}
                      </div>
                    </Link>
                  )
                })}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <FlaskConical className="h-8 w-8 text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground">
                  No backtests yet for this strategy
                </p>
                <Button asChild variant="link" size="sm" className="mt-2">
                  <Link to={`/backtests?strategy=${id}`}>Run your first backtest</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  )
}
