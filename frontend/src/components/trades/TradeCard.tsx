import type { TradeLog } from "../../types";

interface TradeCardProps {
  trade: TradeLog;
  tradeNumber: number;
  onClick: () => void;
}

const getExitReasonLabel = (reason?: string): string => {
  if (!reason) return "--";
  const labels: Record<string, string> = {
    signal: "Signal",
    stop_loss: "SL",
    take_profit: "TP",
    trailing_stop: "Trail",
    force_close: "Force",
    last_bar_entry_force_close: "Last Bar",
    liquidation: "Liq",
  };
  return labels[reason] || reason;
};

const formatDate = (date: string): string => {
  return date.split("T")[0];
};

export default function TradeCard({ trade, tradeNumber, onClick }: TradeCardProps) {
  return (
    <div className="trade-card" onClick={onClick}>
      <div className="trade-card-header">
        <span className="trade-number">#{tradeNumber}</span>
        <span
          className="direction-badge"
          style={{
            background: trade.direction === "SHORT" ? "var(--danger)" : "var(--accent)",
          }}
        >
          {trade.direction === "SHORT" ? "SHORT" : "LONG"}
        </span>
      </div>

      <div className="trade-card-pnl">
        <span
          className="pnl-amount"
          style={{ color: trade.pnl >= 0 ? "var(--accent)" : "var(--danger)" }}
        >
          ${trade.pnl.toFixed(2)}
        </span>
        <span
          className="pnl-percent"
          style={{ color: trade.pnl_pct >= 0 ? "var(--accent)" : "var(--danger)" }}
        >
          ({trade.pnl_pct.toFixed(2)}%)
        </span>
      </div>

      <div className="trade-card-dates">
        <div className="date-row">
          <span className="date-label">Entry:</span>
          <span className="date-value">{formatDate(trade.entry_date)}</span>
        </div>
        <div className="date-row">
          <span className="date-label">Exit:</span>
          <span className="date-value">{formatDate(trade.exit_date)}</span>
        </div>
      </div>

      <div className="trade-card-footer">
        <span className="shares">{trade.shares.toFixed(2)} shares</span>
        <span className="exit-reason tag">{getExitReasonLabel(trade.exit_reason)}</span>
      </div>
    </div>
  );
}
