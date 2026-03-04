import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getBacktest, getBacktestTrades } from "../api/client";
import type { BacktestOut, TradeLog } from "../types";

const metricLabels: Record<string, string> = {
  total_return_pct: "Total Return %",
  cagr: "CAGR",
  total_trades: "Total Trades",
  win_rate: "Win Rate %",
  avg_win_loss: "Avg Win / Avg Loss",
  max_drawdown_pct: "Max Drawdown %",
  sharpe_ratio: "Sharpe Ratio",
  profit_factor: "Profit Factor",
  avg_trade_duration: "Avg Trade Duration",
  longest_drawdown_days: "Longest Drawdown (days)",
};

const metricOrder = [
  "total_return_pct",
  "cagr",
  "total_trades",
  "win_rate",
  "avg_win_loss",
  "max_drawdown_pct",
  "sharpe_ratio",
  "profit_factor",
  "avg_trade_duration",
  "longest_drawdown_days",
];

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
        equity: Number(capital.toFixed(4)),
      },
    ];
    const sorted = [...trades].sort((a, b) => a.exit_date.localeCompare(b.exit_date));
    for (const trade of sorted) {
      capital += trade.pnl;
      points.push({
        date: trade.exit_date,
        equity: Number(capital.toFixed(4)),
      });
    }
    return points;
  }, [run, trades]);

  if (!id) {
    return <div className="container">Missing backtest id.</div>;
  }

  return (
    <div className="container fade-in">
      <div className="card">
        <h1>Backtest Report</h1>
        {error && <div className="notice">{error}</div>}
        <div className="row" style={{ alignItems: "center" }}>
          <span className="tag">Run ID: {id}</span>
          <span className="tag">Status: {run?.status || "Loading"}</span>
          {run?.status === "FAILED" && run.error_message && (
            <span className="tag" style={{ color: "var(--danger)" }}>
              {run.error_message}
            </span>
          )}
        </div>
        {(run?.status === "RUNNING" || run?.status === "PENDING") && (
          <div style={{ marginTop: "16px" }} className="row">
            <div className="spinner" />
            <span>Backtest running...</span>
          </div>
        )}
      </div>

      {run?.report && (
        <div className="card">
          <h2>Metrics</h2>
          <div className="metrics">
            {metricOrder.map((key) => (
              <div key={key} className="metric">
                <div style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
                  {metricLabels[key] || key}
                </div>
                <div style={{ fontWeight: 700, fontSize: "1.1rem" }}>
                  {typeof run.report?.[key] === "number"
                    ? Number(run.report?.[key]).toFixed(4)
                    : run.report?.[key] ?? "n/a"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h2>Equity Curve</h2>
        {loadingTrades && <div className="notice">Loading trade data for equity curve...</div>}
        {equitySeries.length === 0 ? (
          <p className="notice">No equity data yet.</p>
        ) : (
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <LineChart data={equitySeries}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="equity" stroke="#1b7f6b" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="card">
        <h2>Trades</h2>
        <p>View full trade log for this run.</p>
        <Link className="btn" to={`/backtests/${id}/trades`}>
          View Trade Log
        </Link>
      </div>
    </div>
  );
}
