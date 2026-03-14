import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";
import { getBacktest, getBacktestTrades } from "../api/client";
import type { BacktestOut, TradeLog } from "../types";

const metricLabels: Record<string, string> = {
  total_return_pct: "Total Return",
  cagr: "CAGR",
  total_trades: "Total Trades",
  win_rate: "Win Rate",
  avg_win: "Avg Win",
  avg_loss: "Avg Loss",
  avg_win_loss: "Win/Loss Ratio",
  max_drawdown_pct: "Max Drawdown",
  sharpe_ratio: "Sharpe Ratio",
  profit_factor: "Profit Factor",
  avg_trade_duration_days: "Avg Duration",
  longest_drawdown_days: "Longest Drawdown",
  final_capital: "Final Capital",
  largest_win: "Largest Win",
  largest_loss: "Largest Loss",
  benchmark_return_pct: "Benchmark Return",
  benchmark_final_capital: "Benchmark Final Capital",
  benchmark_sharpe_ratio: "Benchmark Sharpe",
  benchmark_max_drawdown_pct: "Benchmark Drawdown",
  alpha: "Alpha",
  beta: "Beta",
};

const primaryMetrics = [
  "total_return_pct",
  "cagr",
  "sharpe_ratio",
  "max_drawdown_pct",
  "final_capital",
];

const tradeMetrics = [
  "total_trades",
  "win_rate",
  "avg_win",
  "avg_loss",
  "profit_factor",
  "avg_trade_duration_days",
  "largest_win",
  "largest_loss",
];

const benchmarkMetrics = [
  "benchmark_return_pct",
  "benchmark_final_capital",
  "benchmark_sharpe_ratio",
  "benchmark_max_drawdown_pct",
  "alpha",
  "beta",
];

function formatMetricValue(key: string, value: number): string {
  if (key.includes("pct") || key === "cagr" || key === "win_rate") {
    return `${value.toFixed(2)}%`;
  }
  if (key.includes("capital") || key.includes("win") || key.includes("loss")) {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  if (key.includes("days")) {
    return `${Math.round(value)} days`;
  }
  if (key.includes("ratio") || key.includes("factor")) {
    return value.toFixed(2);
  }
  return value.toFixed(2);
}

function getMetricColor(key: string, value: number): string {
  if (key === "max_drawdown_pct" || key === "benchmark_max_drawdown_pct" || key === "longest_drawdown_days" || key === "avg_loss" || key === "largest_loss") {
    return value < 0 ? "var(--danger)" : "var(--muted)";
  }
  if (key.includes("return") || key === "cagr" || key === "alpha") {
    return value > 0 ? "var(--accent)" : value < 0 ? "var(--danger)" : "var(--muted)";
  }
  if (key === "sharpe_ratio" || key === "benchmark_sharpe_ratio") {
    return value > 1 ? "var(--accent)" : value > 0 ? "var(--accent-2)" : "var(--danger)";
  }
  if (key === "profit_factor") {
    return value > 1.5 ? "var(--accent)" : value > 1 ? "var(--accent-2)" : "var(--danger)";
  }
  if (key === "beta") {
    return value > 1 ? "var(--accent-2)" : "var(--muted)";
  }
  return "var(--ink)";
}

export default function BacktestReport() {
  const { id } = useParams();
  const [run, setRun] = useState<BacktestOut | null>(null);
  const [trades, setTrades] = useState<TradeLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingTrades, setLoadingTrades] = useState(false);

  useEffect(() => {
    if (!id) return;
    let interval: number | undefined;
    const fetchRun = async () => {
      try {
        const data = await getBacktest(id);
        setRun(data);
        if (data.status === "PENDING" || data.status === "RUNNING") {
          return;
        }
        if (interval) window.clearInterval(interval);
      } catch (err: any) {
        setError(err.message || "Failed to load backtest");
      }
    };

    fetchRun();
    interval = window.setInterval(fetchRun, 2000);
    return () => {
      if (interval) window.clearInterval(interval);
    };
  }, [id]);

  useEffect(() => {
    if (!id || !run || run.status !== "COMPLETE") return;
    if (trades.length > 0) return;
    setLoadingTrades(true);
    getBacktestTrades(id, 1000, 0)
      .then((data) => setTrades(data))
      .catch((err) => setError(err.message || "Failed to load trades"))
      .finally(() => setLoadingTrades(false));
  }, [id, run, trades.length]);

  const equitySeries = useMemo(() => {
    if (!run) return [];
    const initial = run.initial_capital || 0;
    let capital = initial;
    const points = [
      {
        date: run.start_date,
        equity: Number(capital.toFixed(2)),
        benchmark: Number(initial.toFixed(2)),
      },
    ];

    const sorted = [...trades].sort((a, b) => a.exit_date.localeCompare(b.exit_date));

    // Calculate benchmark if available
    const benchmarkReturn = run.report?.benchmark_return_pct || 0;
    const benchmarkMultiplier = 1 + (benchmarkReturn / 100);

    for (const trade of sorted) {
      capital += trade.pnl;
      const daysSinceStart = Math.max(0,
        (new Date(trade.exit_date).getTime() - new Date(run.start_date).getTime()) / (1000 * 60 * 60 * 24)
      );
      const totalDays = Math.max(1,
        (new Date(run.end_date).getTime() - new Date(run.start_date).getTime()) / (1000 * 60 * 60 * 24)
      );
      const benchmarkProgress = Math.pow(benchmarkMultiplier, daysSinceStart / totalDays);

      points.push({
        date: trade.exit_date,
        equity: Number(capital.toFixed(2)),
        benchmark: Number((initial * benchmarkProgress).toFixed(2)),
      });
    }
    return points;
  }, [run, trades]);

  const winningTrades = useMemo(() => trades.filter((t) => t.pnl > 0), [trades]);
  const losingTrades = useMemo(() => trades.filter((t) => t.pnl <= 0), [trades]);

  if (!id) {
    return <div className="container">Missing backtest id.</div>;
  }

  return (
    <div className="container fade-in">
      <div className="card">
        <h1>Backtest Report</h1>
        {error && <div className="notice">{error}</div>}
        <div className="row" style={{ alignItems: "center", marginTop: "12px" }}>
          <span className="tag">Run ID: {id.slice(0, 8)}</span>
          <span className="tag" style={{
            background: run?.status === "COMPLETE" ? "#e8f5f3" : run?.status === "FAILED" ? "#ffe8e6" : "#fff6e8",
            color: run?.status === "COMPLETE" ? "var(--accent)" : run?.status === "FAILED" ? "var(--danger)" : "var(--accent-2)"
          }}>
            {run?.status || "Loading"}
          </span>
          {run?.ticker && <span className="tag">{run.ticker} ({run.asset_class})</span>}
          {run?.bar_resolution && <span className="tag">{run.bar_resolution}</span>}
        </div>
        {run?.status === "FAILED" && run.error_message && (
          <div className="notice" style={{ marginTop: "12px", background: "#ffe8e6", borderColor: "#ffcccc", color: "var(--danger)" }}>
            {run.error_message}
          </div>
        )}
        {(run?.status === "RUNNING" || run?.status === "PENDING") && (
          <div style={{ marginTop: "16px" }} className="row">
            <div className="spinner" />
            <span>Backtest running...</span>
          </div>
        )}
      </div>

      {run?.report && (
        <>
          <div className="card">
            <h2>Performance Overview</h2>
            <div className="metrics">
              {primaryMetrics.map((key) => {
                const value = run.report?.[key];
                if (value === undefined || value === null) return null;
                return (
                  <div key={key} className="metric" style={{
                    borderLeft: `4px solid ${getMetricColor(key, value as number)}`
                  }}>
                    <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginBottom: "4px" }}>
                      {metricLabels[key] || key}
                    </div>
                    <div style={{
                      fontWeight: 700,
                      fontSize: "1.3rem",
                      color: getMetricColor(key, value as number)
                    }}>
                      {formatMetricValue(key, value as number)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="card">
            <h2>Trade Statistics</h2>
            <div className="metrics">
              {tradeMetrics.map((key) => {
                const value = run.report?.[key];
                if (value === undefined || value === null) return null;
                return (
                  <div key={key} className="metric">
                    <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginBottom: "4px" }}>
                      {metricLabels[key] || key}
                    </div>
                    <div style={{
                      fontWeight: 700,
                      fontSize: "1.1rem",
                      color: getMetricColor(key, value as number)
                    }}>
                      {formatMetricValue(key, value as number)}
                    </div>
                  </div>
                );
              })}
            </div>

            {(winningTrades.length > 0 || losingTrades.length > 0) && (
              <div className="grid grid-2" style={{ marginTop: "16px" }}>
                <div className="card" style={{ background: "#e8f5f3", border: "1px solid var(--accent)" }}>
                  <h4 style={{ color: "var(--accent)", margin: "0 0 8px 0" }}>
                    Winning Trades ({winningTrades.length})
                  </h4>
                  <div style={{ fontSize: "0.9rem", color: "var(--muted)" }}>
                    Total Profit: <strong style={{ color: "var(--accent)" }}>
                      ${winningTrades.reduce((sum, t) => sum + t.pnl, 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </strong>
                  </div>
                </div>
                <div className="card" style={{ background: "#ffe8e6", border: "1px solid var(--danger)" }}>
                  <h4 style={{ color: "var(--danger)", margin: "0 0 8px 0" }}>
                    Losing Trades ({losingTrades.length})
                  </h4>
                  <div style={{ fontSize: "0.9rem", color: "var(--muted)" }}>
                    Total Loss: <strong style={{ color: "var(--danger)" }}>
                      ${losingTrades.reduce((sum, t) => sum + t.pnl, 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </strong>
                  </div>
                </div>
              </div>
            )}
          </div>

          {run.report.benchmark_return_pct !== undefined && (
            <div className="card">
              <h2>Benchmark Comparison</h2>
              <div className="metrics">
                {benchmarkMetrics.map((key) => {
                  const value = run.report?.[key];
                  if (value === undefined || value === null) return null;
                  return (
                    <div key={key} className="metric">
                      <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginBottom: "4px" }}>
                        {metricLabels[key] || key}
                      </div>
                      <div style={{
                        fontWeight: 700,
                        fontSize: "1.1rem",
                        color: getMetricColor(key, value as number)
                      }}>
                        {formatMetricValue(key, value as number)}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="notice" style={{ marginTop: "12px" }}>
                Alpha represents excess return over buy-and-hold benchmark.
                {run.report.alpha && run.report.alpha > 0
                  ? " Your strategy outperformed!"
                  : " Consider optimizing your strategy parameters."}
              </div>
            </div>
          )}
        </>
      )}

      <div className="card">
        <h2>Equity Curve</h2>
        {loadingTrades && <div className="notice">Loading trade data for equity curve...</div>}
        {equitySeries.length === 0 ? (
          <p className="notice">No equity data yet.</p>
        ) : (
          <div style={{ width: "100%", height: 400 }}>
            <ResponsiveContainer>
              <LineChart data={equitySeries} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e0d7cc" />
                <XAxis
                  dataKey="date"
                  stroke="#6a6157"
                  style={{ fontSize: "0.85rem" }}
                />
                <YAxis
                  stroke="#6a6157"
                  style={{ fontSize: "0.85rem" }}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  contentStyle={{
                    background: "white",
                    border: "1px solid #e0d7cc",
                    borderRadius: "8px",
                    padding: "8px"
                  }}
                  formatter={(value: number) => `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="equity"
                  stroke="var(--accent)"
                  strokeWidth={2.5}
                  dot={false}
                  name="Strategy"
                />
                {run?.report?.benchmark_return_pct !== undefined && (
                  <Line
                    type="monotone"
                    dataKey="benchmark"
                    stroke="var(--accent-2)"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                    name="Buy & Hold"
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="card">
        <h2>Trade Log</h2>
        <p style={{ color: "var(--muted)", marginBottom: "12px" }}>
          View detailed information about each trade including entry/exit dates, prices, P&L, and exit reasons.
        </p>
        <Link className="btn" to={`/backtests/${id}/trades`}>
          View All {trades.length} Trades
        </Link>
      </div>
    </div>
  );
}
