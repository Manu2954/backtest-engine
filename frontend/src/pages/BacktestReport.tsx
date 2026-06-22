import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Loader2, FileSpreadsheet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricsGrid } from "@/components/backtest/MetricsGrid";
import { EquityCurve } from "@/components/backtest/EquityCurve";
import { useBacktest, useStrategy } from "@/api/hooks";
import { formatDate } from "@/lib/utils";

export default function BacktestReport() {
  const { id } = useParams<{ id: string }>();
  const { data: backtest, isLoading: isLoadingBacktest, error } = useBacktest(id);
  const { data: strategy } = useStrategy(backtest?.strategy_id);

  if (isLoadingBacktest) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !backtest) {
    return (
      <div className="space-y-4">
        <Link to="/backtests">
          <Button variant="ghost">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Backtests
          </Button>
        </Link>
        <div className="text-center py-8 text-destructive">
          {error?.message || "Backtest not found"}
        </div>
      </div>
    );
  }

  const results = backtest.results;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/backtests">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Backtest Report</h1>
            <p className="text-muted-foreground">
              {strategy?.name || "Strategy"} • {backtest.ticker} • {formatDate(backtest.start_date)} - {formatDate(backtest.end_date)}
            </p>
          </div>
        </div>
        <Link to={`/backtests/${backtest.id}/trades`}>
          <Button variant="outline">
            <FileSpreadsheet className="h-4 w-4 mr-2" />
            View Trade Log
          </Button>
        </Link>
      </div>

      {backtest.status !== "COMPLETED" ? (
        <Card>
          <CardContent className="py-8 text-center">
            {backtest.status === "RUNNING" || backtest.status === "PENDING" ? (
              <div className="flex flex-col items-center gap-4">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-muted-foreground">
                  Backtest is {backtest.status.toLowerCase()}...
                </p>
              </div>
            ) : (
              <p className="text-destructive">
                Backtest failed: {backtest.error_message || "Unknown error"}
              </p>
            )}
          </CardContent>
        </Card>
      ) : results ? (
        <>
          <MetricsGrid results={results} />

          <Card>
            <CardHeader>
              <CardTitle>Equity Curve</CardTitle>
            </CardHeader>
            <CardContent>
              <EquityCurve
                equityCurve={results.equity_curve || []}
                benchmarkCurve={results.benchmark_curve}
              />
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Trade Statistics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Trades</span>
                  <span className="font-medium">{results.total_trades}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Winning Trades</span>
                  <span className="font-medium text-green-500">{results.winning_trades}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Losing Trades</span>
                  <span className="font-medium text-red-500">{results.losing_trades}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Avg Win</span>
                  <span className="font-medium text-green-500">
                    {results.avg_win?.toFixed(2)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Avg Loss</span>
                  <span className="font-medium text-red-500">
                    {results.avg_loss?.toFixed(2)}%
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Backtest Configuration</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Initial Capital</span>
                  <span className="font-medium">${backtest.initial_capital?.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Asset Class</span>
                  <span className="font-medium">{backtest.asset_class}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Bar Resolution</span>
                  <span className="font-medium">{backtest.bar_resolution}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Position Sizing</span>
                  <span className="font-medium">{backtest.position_size_type}</span>
                </div>
                {backtest.stop_loss_pct && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Stop Loss</span>
                    <span className="font-medium">{backtest.stop_loss_pct}%</span>
                  </div>
                )}
                {backtest.take_profit_pct && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Take Profit</span>
                    <span className="font-medium">{backtest.take_profit_pct}%</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      ) : (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No results available
          </CardContent>
        </Card>
      )}
    </div>
  );
}
