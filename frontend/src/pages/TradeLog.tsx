import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getBacktestTrades } from "../api/client";
import type { TradeLog } from "../types";

const getExitReasonColor = (reason?: string): string => {
  if (!reason) return "var(--muted)";
  if (reason === "take_profit" || reason === "trailing_stop") return "var(--accent)";
  if (reason === "stop_loss") return "var(--danger)";
  if (reason === "signal") return "var(--ink)";
  return "var(--muted)";
};

const getExitReasonLabel = (reason?: string): string => {
  if (!reason) return "—";
  const labels: Record<string, string> = {
    signal: "Signal",
    stop_loss: "Stop Loss",
    take_profit: "Take Profit",
    trailing_stop: "Trailing Stop",
    force_close: "Force Close",
    last_bar_entry_force_close: "Last Bar Close",
  };
  return labels[reason] || reason;
};

export default function TradeLogPage() {
  const { id } = useParams();
  const [trades, setTrades] = useState<TradeLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = 50;

  useEffect(() => {
    if (!id) return;
    getBacktestTrades(id, limit, offset)
      .then(setTrades)
      .catch((err) => setError(err.message || "Failed to load trades"));
  }, [id, offset]);

  if (!id) {
    return <div className="container">Missing backtest id.</div>;
  }

  const winningTrades = trades.filter((t) => t.pnl > 0);
  const losingTrades = trades.filter((t) => t.pnl <= 0);

  return (
    <div className="container fade-in">
      <div className="card">
        <h1>Trade Log</h1>
        {error && <div className="notice">{error}</div>}

        {trades.length > 0 && (
          <div className="grid grid-2" style={{ marginBottom: "16px" }}>
            <div className="metric" style={{ borderLeft: `4px solid var(--accent)` }}>
              <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginBottom: "4px" }}>
                Winning Trades
              </div>
              <div style={{ fontWeight: 700, fontSize: "1.3rem", color: "var(--accent)" }}>
                {winningTrades.length} / {trades.length}
              </div>
            </div>
            <div className="metric" style={{ borderLeft: `4px solid var(--danger)` }}>
              <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginBottom: "4px" }}>
                Losing Trades
              </div>
              <div style={{ fontWeight: 700, fontSize: "1.3rem", color: "var(--danger)" }}>
                {losingTrades.length} / {trades.length}
              </div>
            </div>
          </div>
        )}

        <div style={{ overflowX: "auto" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Entry Date</th>
                <th>Entry Price</th>
                <th>Exit Date</th>
                <th>Exit Price</th>
                <th>Shares</th>
                <th>PnL</th>
                <th>PnL %</th>
                <th>Duration</th>
                <th>Exit Reason</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.id}>
                  <td>{trade.entry_date}</td>
                  <td>${trade.entry_price.toFixed(4)}</td>
                  <td>{trade.exit_date}</td>
                  <td>${trade.exit_price.toFixed(4)}</td>
                  <td>{trade.shares.toFixed(4)}</td>
                  <td style={{ color: trade.pnl >= 0 ? "var(--accent)" : "var(--danger)" }}>
                    ${trade.pnl.toFixed(2)}
                  </td>
                  <td style={{ color: trade.pnl_pct >= 0 ? "var(--accent)" : "var(--danger)" }}>
                    {trade.pnl_pct.toFixed(2)}%
                  </td>
                  <td>{trade.trade_duration_days}d</td>
                  <td>
                    <span
                      className="tag"
                      style={{
                        background: getExitReasonColor(trade.exit_reason) + "20",
                        color: getExitReasonColor(trade.exit_reason),
                        border: `1px solid ${getExitReasonColor(trade.exit_reason)}40`,
                      }}
                    >
                      {getExitReasonLabel(trade.exit_reason)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="row" style={{ marginTop: "12px" }}>
          <button className="btn secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
            Previous
          </button>
          <button className="btn" disabled={trades.length < limit} onClick={() => setOffset(offset + limit)}>
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
