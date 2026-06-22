import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getBacktest, getBacktestTrades } from "../api/client";
import type { BacktestOut, TradeLog } from "../types";
import HeroSection from "../components/backtest/HeroSection";
import QuickStats from "../components/backtest/QuickStats";
import EquityCurve from "../components/backtest/EquityCurve";
import MonthlyReturns from "../components/backtest/MonthlyReturns";
import ExitReasonChart from "../components/backtest/ExitReasonChart";
import ExportActions from "../components/backtest/ExportActions";

const metricLabels: Record<string, string> = {
  avg_win: "Avg Win",
  avg_loss: "Avg Loss",
  avg_win_loss: "Win/Loss Ratio",
  avg_trade_duration_days: "Avg Duration",
  longest_drawdown_days: "Longest Drawdown",
  largest_win: "Largest Win",
  largest_loss: "Largest Loss",
  benchmark_return_pct: "Benchmark Return",
  benchmark_final_capital: "Benchmark Final Capital",
  benchmark_sharpe_ratio: "Benchmark Sharpe",
  benchmark_max_drawdown_pct: "Benchmark Drawdown",
  alpha: "Alpha",
  beta: "Beta",
};

const tradeMetrics = [
  "avg_win",
  "avg_loss",
  "avg_trade_duration_days",
  "largest_win",
  "largest_loss",
  "longest_drawdown_days",
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
  const [configExpanded, setConfigExpanded] = useState(false);

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
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : "Failed to load backtest";
        setError(errorMsg);
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

  const winningTrades = useMemo(() => trades.filter((t) => t.pnl > 0), [trades]);
  const losingTrades = useMemo(() => trades.filter((t) => t.pnl <= 0), [trades]);

  if (!id) {
    return <div className="container">Missing backtest id.</div>;
  }

  return (
    <div className="container fade-in">
      {/* Header Card with Status */}
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
          {/* Hero Section - Large Return Display with Benchmark Comparison */}
          <HeroSection run={run} />

          {/* Quick Stats - 5 Key Metrics with Visuals */}
          <QuickStats run={run} />

          {/* Equity Curve - Interactive Chart */}
          {loadingTrades && <div className="notice">Loading trade data for equity curve...</div>}
          <EquityCurve run={run} trades={trades} />

          {/* Analysis Charts Section */}
          <div className="grid grid-2">
            {/* Monthly Returns */}
            <MonthlyReturns trades={trades} initialCapital={run.initial_capital} />

            {/* Exit Reason Distribution */}
            <ExitReasonChart trades={trades} />
          </div>

          {/* Trade Statistics - Detailed Metrics */}
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

          {/* Benchmark Comparison */}
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

          {/* Export Actions */}
          <ExportActions run={run} trades={trades} />

          {/* Configuration - Collapsible */}
          <div className="card">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                cursor: "pointer",
              }}
              onClick={() => setConfigExpanded(!configExpanded)}
            >
              <h2 style={{ margin: 0 }}>Configuration</h2>
              <button
                className="btn secondary"
                style={{ padding: "6px 12px", fontSize: "0.85rem" }}
              >
                {configExpanded ? "Hide" : "Show"}
              </button>
            </div>

            {configExpanded && (
              <div style={{ marginTop: "16px" }}>
                <table className="table">
                  <tbody>
                    <tr>
                      <td style={{ fontWeight: 600 }}>Strategy ID</td>
                      <td>{run.strategy_id}</td>
                    </tr>
                    <tr>
                      <td style={{ fontWeight: 600 }}>Ticker</td>
                      <td>{run.ticker}</td>
                    </tr>
                    <tr>
                      <td style={{ fontWeight: 600 }}>Asset Class</td>
                      <td>{run.asset_class}</td>
                    </tr>
                    <tr>
                      <td style={{ fontWeight: 600 }}>Date Range</td>
                      <td>{run.start_date} to {run.end_date}</td>
                    </tr>
                    <tr>
                      <td style={{ fontWeight: 600 }}>Bar Resolution</td>
                      <td>{run.bar_resolution}</td>
                    </tr>
                    <tr>
                      <td style={{ fontWeight: 600 }}>Initial Capital</td>
                      <td>${run.initial_capital.toLocaleString()}</td>
                    </tr>
                    <tr>
                      <td style={{ fontWeight: 600 }}>Position Sizing</td>
                      <td>{run.position_size_type || "full_capital"} ({run.position_size_value || 100}%)</td>
                    </tr>
                    {run.stop_loss_pct && (
                      <tr>
                        <td style={{ fontWeight: 600 }}>Stop Loss</td>
                        <td>{run.stop_loss_pct}%</td>
                      </tr>
                    )}
                    {run.take_profit_pct && (
                      <tr>
                        <td style={{ fontWeight: 600 }}>Take Profit</td>
                        <td>{run.take_profit_pct}%</td>
                      </tr>
                    )}
                    {(run.commission_per_trade || run.commission_pct) && (
                      <tr>
                        <td style={{ fontWeight: 600 }}>Commission</td>
                        <td>
                          {run.commission_per_trade ? `$${run.commission_per_trade}/trade` : ""}
                          {run.commission_per_trade && run.commission_pct ? " + " : ""}
                          {run.commission_pct ? `${run.commission_pct}%` : ""}
                        </td>
                      </tr>
                    )}
                    {run.slippage_pct !== undefined && run.slippage_pct > 0 && (
                      <tr>
                        <td style={{ fontWeight: 600 }}>Slippage</td>
                        <td>{run.slippage_pct}%</td>
                      </tr>
                    )}
                    {run.dynamic_stop_column && (
                      <tr>
                        <td style={{ fontWeight: 600 }}>Dynamic Stop</td>
                        <td>{run.dynamic_stop_column}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* Trade Log Link */}
      <div className="card">
        <h2>Trade Log</h2>
        <p style={{ color: "var(--muted)", marginBottom: "12px" }}>
          View detailed information about each trade including entry/exit dates, prices, P&L, and exit reasons.
        </p>
        <Link className="btn" to={`/backtests/${id}/trades`}>
          View All {trades.length} Trades
        </Link>
      </div>

      {/* Comparison Placeholder */}
      <div className="card" style={{ background: "#faf8f5", border: "2px dashed var(--line)" }}>
        <div style={{ textAlign: "center", padding: "24px", color: "var(--muted)" }}>
          <h3 style={{ margin: "0 0 8px 0", color: "var(--muted)" }}>Compare Strategies</h3>
          <p style={{ fontSize: "0.9rem" }}>
            Strategy comparison feature coming soon. Run multiple backtests and compare them side by side.
          </p>
        </div>
      </div>
    </div>
  );
}
