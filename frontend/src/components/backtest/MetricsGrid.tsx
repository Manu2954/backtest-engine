import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, formatCurrency, formatPercent, formatNumber } from "@/lib/utils";
import type { BacktestReport } from "@/types";

interface MetricsGridProps {
  report: BacktestReport;
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

export function MetricsGrid({ report, className }: MetricsGridProps) {
  const totalReturnVariant =
    report.total_return_pct >= 0 ? "success" : "danger";
  const sharpeVariant =
    report.sharpe_ratio >= 1.0
      ? "success"
      : report.sharpe_ratio >= 0.5
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
            value={formatPercent(report.total_return_pct)}
            variant={totalReturnVariant}
          />
          <MetricCard
            label="CAGR"
            value={formatPercent(report.cagr * 100)}
            variant={report.cagr >= 0 ? "success" : "danger"}
          />
          <MetricCard
            label="Max Drawdown"
            value={formatPercent(-report.max_drawdown_pct)}
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
            value={formatNumber(report.sharpe_ratio)}
            variant={sharpeVariant}
          />
          {report.sortino_ratio !== undefined && (
            <MetricCard
              label="Sortino Ratio"
              value={formatNumber(report.sortino_ratio)}
              variant={report.sortino_ratio >= 1.0 ? "success" : "warning"}
            />
          )}
          <MetricCard
            label="Profit Factor"
            value={formatNumber(report.profit_factor)}
            variant={report.profit_factor >= 1.5 ? "success" : "warning"}
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
            value={report.total_trades.toString()}
          />
          <MetricCard
            label="Win Rate"
            value={formatPercent(report.win_rate * 100)}
            variant={report.win_rate >= 0.5 ? "success" : "warning"}
          />
          <MetricCard
            label="Avg Duration"
            value={`${formatNumber(report.avg_trade_duration_days, 1)} days`}
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
            value={report.winning_trades.toString()}
            variant="success"
          />
          <MetricCard
            label="Losing Trades"
            value={report.losing_trades.toString()}
            variant="danger"
          />
          <div className="flex gap-4">
            <MetricCard
              label="Avg Win"
              value={formatCurrency(report.avg_win)}
              variant="success"
            />
            <MetricCard
              label="Avg Loss"
              value={formatCurrency(report.avg_loss)}
              variant="danger"
            />
          </div>
        </CardContent>
      </Card>

      {/* Benchmark Comparison */}
      {report.benchmark_return_pct !== undefined && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Benchmark Comparison
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <MetricCard
              label="Benchmark Return"
              value={formatPercent(report.benchmark_return_pct)}
              variant={report.benchmark_return_pct >= 0 ? "success" : "danger"}
            />
            {report.alpha !== undefined && (
              <MetricCard
                label="Alpha"
                value={formatPercent(report.alpha * 100)}
                variant={report.alpha >= 0 ? "success" : "danger"}
              />
            )}
            {report.beta !== undefined && (
              <MetricCard label="Beta" value={formatNumber(report.beta)} />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
