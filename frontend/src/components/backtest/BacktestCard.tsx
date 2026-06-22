import { Link } from 'react-router-dom'
import { formatDate, formatPercent, cn } from '@/lib/utils'
import type { Backtest } from '@/types'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  MoreHorizontal,
  Trash2,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Loader2,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface BacktestCardProps {
  backtest: Backtest
  onDelete?: (id: string) => void
}

function getStatusBadgeVariant(status: string): 'pending' | 'running' | 'complete' | 'failed' {
  switch (status) {
    case 'PENDING':
      return 'pending'
    case 'RUNNING':
      return 'running'
    case 'COMPLETE':
    case 'COMPLETED':
      return 'complete'
    case 'FAILED':
      return 'failed'
    default:
      return 'pending'
  }
}

export function BacktestCard({ backtest, onDelete }: BacktestCardProps) {
  const results = backtest.results || backtest.report
  const isComplete = backtest.status === 'COMPLETE' || backtest.status === 'COMPLETED'
  const isRunning = backtest.status === 'RUNNING' || backtest.status === 'PENDING'
  const returnPct = results?.total_return_pct

  return (
    <Card className="group hover:border-primary/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base flex items-center gap-2">
              <Link
                to={`/backtests/${backtest.id}`}
                className="hover:text-primary transition-colors"
              >
                {backtest.ticker}
              </Link>
              <Badge variant="outline" className="text-xs font-normal">
                {backtest.asset_class}
              </Badge>
            </CardTitle>
            <div className="text-xs text-muted-foreground">
              {backtest.start_date} → {backtest.end_date}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={getStatusBadgeVariant(backtest.status)}>
              {isRunning && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
              {backtest.status}
            </Badge>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                  <Link to={`/backtests/${backtest.id}`}>
                    <ExternalLink className="mr-2 h-4 w-4" />
                    View Details
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => onDelete?.(backtest.id)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {isComplete && results ? (
          <>
            {/* Return & Key Metrics */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {returnPct !== undefined && returnPct >= 0 ? (
                  <TrendingUp className="h-5 w-5 text-profit" />
                ) : (
                  <TrendingDown className="h-5 w-5 text-loss" />
                )}
                <span
                  className={cn(
                    'text-2xl font-bold numeric',
                    returnPct !== undefined && returnPct >= 0 ? 'text-profit' : 'text-loss'
                  )}
                >
                  {returnPct !== undefined ? formatPercent(returnPct) : '—'}
                </span>
              </div>
              <div className="text-right text-xs text-muted-foreground">
                {results.total_trades} trades
              </div>
            </div>

            {/* Secondary Metrics */}
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <div className="text-muted-foreground">Sharpe</div>
                <div className="font-medium numeric">
                  {results.sharpe_ratio?.toFixed(2) || '—'}
                </div>
              </div>
              <div>
                <div className="text-muted-foreground">Win Rate</div>
                <div className="font-medium numeric">
                  {results.win_rate ? `${(results.win_rate * 100).toFixed(1)}%` : '—'}
                </div>
              </div>
              <div>
                <div className="text-muted-foreground">Max DD</div>
                <div className="font-medium numeric text-loss">
                  {results.max_drawdown_pct ? `${results.max_drawdown_pct.toFixed(1)}%` : '—'}
                </div>
              </div>
            </div>
          </>
        ) : backtest.status === 'FAILED' ? (
          <div className="text-sm text-destructive">
            {backtest.error_message || 'Backtest failed'}
          </div>
        ) : (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-border text-xs text-muted-foreground">
          <span>{backtest.bar_resolution}</span>
          {backtest.created_at && (
            <span>{formatDate(backtest.created_at)}</span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
