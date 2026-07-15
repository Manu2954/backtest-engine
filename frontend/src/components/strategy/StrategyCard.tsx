import { Link } from 'react-router-dom'
import { INDICATOR_CONFIGS } from '@/lib/constants'
import type { Strategy } from '@/types'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  MoreHorizontal,
  Edit,
  Trash2,
  Play,
  Copy,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface StrategyCardProps {
  strategy: Strategy
  onDelete?: (id: string) => void
  onDuplicate?: (strategy: Strategy) => void
}

export function StrategyCard({ strategy, onDelete, onDuplicate }: StrategyCardProps) {
  const entryConditions = strategy.condition_groups.filter(
    (g) => g.group_type === 'ENTRY'
  )
  const exitConditions = strategy.condition_groups.filter(
    (g) => g.group_type === 'EXIT'
  )

  return (
    <Card className="group hover:border-primary/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base">
              <Link
                to={`/strategies/${strategy.id}`}
                className="hover:text-primary transition-colors"
              >
                {strategy.name}
              </Link>
            </CardTitle>
            {strategy.description && (
              <CardDescription className="line-clamp-2">
                {strategy.description}
              </CardDescription>
            )}
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
                aria-label={`Actions for ${strategy.name}`}
              >
                <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={`/strategies/${strategy.id}/edit`}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onDuplicate?.(strategy)}>
                <Copy className="mr-2 h-4 w-4" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to={`/backtests?strategy=${strategy.id}`}>
                  <Play className="mr-2 h-4 w-4" />
                  Run Backtest
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={() => onDelete?.(strategy.id)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Indicators */}
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-1.5">
            Indicators
          </div>
          <div className="flex flex-wrap gap-1.5">
            {strategy.indicators.length > 0 ? (
              strategy.indicators.slice(0, 5).map((ind) => {
                const config = INDICATOR_CONFIGS[ind.indicator_type as keyof typeof INDICATOR_CONFIGS]
                return (
                  <Badge key={ind.id || ind.alias} variant="secondary" className="text-xs">
                    {config?.name || ind.indicator_type}
                  </Badge>
                )
              })
            ) : (
              <span className="text-xs text-muted-foreground">No indicators</span>
            )}
            {strategy.indicators.length > 5 && (
              <Badge variant="outline" className="text-xs">
                +{strategy.indicators.length - 5}
              </Badge>
            )}
          </div>
        </div>

        {/* Conditions Summary */}
        <div className="flex gap-4 text-xs">
          <div>
            <span className="text-muted-foreground">Entry: </span>
            <span className="font-medium">
              {entryConditions.reduce((acc, g) => acc + g.conditions.length, 0)} conditions
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Exit: </span>
            <span className="font-medium">
              {exitConditions.reduce((acc, g) => acc + g.conditions.length, 0)} conditions
            </span>
          </div>
        </div>

        {/* Expression preview if using expressions */}
        {strategy.entry_expression && (
          <div className="text-xs">
            <span className="text-muted-foreground">Entry: </span>
            <code className="text-[10px] bg-surface-2 px-1.5 py-0.5 rounded">
              {strategy.entry_expression.length > 40
                ? strategy.entry_expression.slice(0, 40) + '...'
                : strategy.entry_expression}
            </code>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
