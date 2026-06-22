import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, formatCurrency, formatPercent, formatNumber } from "@/lib/utils";
import type { BacktestResults } from "@/types";

interface MetricsGridProps {
  results: BacktestResults;
  className?: string;
}

interface MetricCardProps {
  label: string;
  value: string;
  variant?: "default" | "success" | "danger" | "warning";
}

function MetricCard({ label, value, variant = "default" }: MetricCardProps) {
  const valueColors = {
    default: "text-foreground",
    success: "text-green-500",
    danger: "text-red-500",
    warning: "text-yellow-500",
  };

  return (
    <div className="flex flex-col">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={cn("text-xl font-semibold", valueColors[variant])}>
        {value}
      </span>
    </div>
  );
}

export function MetricsGrid({ results, className }: MetricsGridProps) {
  const totalReturn = results.total_return ?? results.total_return_pct ?? 0;
  const totalReturnVariant = totalReturn >= 0 ? "success" : "danger";
  const sharpeVariant =
    results.sharpe_ratio >= 1.0
      ? "success"
      : results.sharpe_ratio >= 0.5
        ? "warning"
        : "danger";

  return (
    <div className={cn("grid gap-4 md:grid-cols-2 lg:grid-cols-3", className)}>
      {/* Primary Metrics */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Performance
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <MetricCard
            label="Total Return"
            value={formatPercent(totalReturn)}
            variant={totalReturnVariant}
          />
          <MetricCard
            label="CAGR"
            value={formatPercent(results.cagr * 100)}
            variant={results.cagr >= 0 ? "success" : "danger"}
          />
          <MetricCard
            label="Max Drawdown"
            value={formatPercent(-results.max_drawdown_pct)}
            variant="danger"
          />
        </CardContent>
      </Card>

      {/* Risk Metrics */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Risk Metrics
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <MetricCard
            label="Sharpe Ratio"
            value={formatNumber(results.sharpe_ratio)}
            variant={sharpeVariant}
          />
          {results.sortino_ratio !== undefined && (
            <MetricCard
              label="Sortino Ratio"
              value={formatNumber(results.sortino_ratio)}
              variant={results.sortino_ratio >= 1.0 ? "success" : "warning"}
            />
          )}
          <MetricCard
            label="Profit Factor"
            value={formatNumber(results.profit_factor)}
            variant={results.profit_factor >= 1.5 ? "success" : "warning"}
          />
        </CardContent>
      </Card>

      {/* Trade Statistics */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Trade Statistics
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <MetricCard
            label="Total Trades"
            value={results.total_trades.toString()}
          />
          <MetricCard
            label="Win Rate"
            value={formatPercent(results.win_rate * 100)}
            variant={results.win_rate >= 0.5 ? "success" : "warning"}
          />
          <MetricCard
            label="Avg Duration"
            value={`${formatNumber(results.avg_trade_duration_days, 1)} days`}
          />
        </CardContent>
      </Card>

      {/* Win/Loss Stats */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Win/Loss
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <MetricCard
            label="Winning Trades"
            value={results.winning_trades.toString()}
            variant="success"
          />
          <MetricCard
            label="Losing Trades"
            value={results.losing_trades.toString()}
            variant="danger"
          />
          <div className="flex gap-4">
            <MetricCard
              label="Avg Win"
              value={formatCurrency(results.avg_win)}
              variant="success"
            />
            <MetricCard
              label="Avg Loss"
              value={formatCurrency(results.avg_loss)}
              variant="danger"
            />
          </div>
        </CardContent>
      </Card>

      {/* Benchmark Comparison */}
      {results.benchmark_return_pct !== undefined && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Benchmark Comparison
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <MetricCard
              label="Benchmark Return"
              value={formatPercent(results.benchmark_return_pct)}
              variant={results.benchmark_return_pct >= 0 ? "success" : "danger"}
            />
            {results.alpha !== undefined && (
              <MetricCard
                label="Alpha"
                value={formatPercent(results.alpha * 100)}
                variant={results.alpha >= 0 ? "success" : "danger"}
              />
            )}
            {results.beta !== undefined && (
              <MetricCard label="Beta" value={formatNumber(results.beta)} />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
