import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getBacktestTrades } from "../api/client";
import type { TradeLog } from "../types";

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

  return (
    <div className="container fade-in">
      <div className="card">
        <h1>Trade Log</h1>
        {error && <div className="notice">{error}</div>}
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
              <th>Duration (days)</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade) => (
              <tr key={trade.id}>
                <td>{trade.entry_date}</td>
                <td>{trade.entry_price.toFixed(4)}</td>
                <td>{trade.exit_date}</td>
                <td>{trade.exit_price.toFixed(4)}</td>
                <td>{trade.shares.toFixed(4)}</td>
                <td>{trade.pnl.toFixed(4)}</td>
                <td>{trade.pnl_pct.toFixed(4)}</td>
                <td>{trade.trade_duration_days}</td>
              </tr>
            ))}
          </tbody>
        </table>
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
