import type { TradeLog } from "../../types";

interface TradeDetailModalProps {
  trade: TradeLog;
  tradeNumber: number;
  onClose: () => void;
}

const getExitReasonLabel = (reason?: string): string => {
  if (!reason) return "--";
  const labels: Record<string, string> = {
    signal: "Signal",
    stop_loss: "Stop Loss",
    take_profit: "Take Profit",
    trailing_stop: "Trailing Stop",
    force_close: "Force Close",
    last_bar_entry_force_close: "Last Bar Close",
    liquidation: "Liquidation",
  };
  return labels[reason] || reason;
};

export default function TradeDetailModal({
  trade,
  tradeNumber,
  onClose,
}: TradeDetailModalProps) {
  const formatDate = (date: string) => {
    const d = new Date(date);
    return d.toLocaleString();
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal trade-detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Trade #{tradeNumber}</h2>
          <button className="btn secondary" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="trade-detail-content">
          {/* Direction Badge */}
          <div className="detail-section">
            <div
              className="direction-badge-large"
              style={{
                background:
                  trade.direction === "SHORT" ? "var(--danger)" : "var(--accent)",
              }}
            >
              {trade.direction === "SHORT" ? "SHORT" : "LONG"}
            </div>
          </div>

          {/* Entry/Exit Info */}
          <div className="detail-section">
            <h3>Entry</h3>
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">Date</span>
                <span className="detail-value">{formatDate(trade.entry_date)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Price</span>
                <span className="detail-value">${trade.entry_price.toFixed(4)}</span>
              </div>
            </div>
          </div>

          <div className="detail-section">
            <h3>Exit</h3>
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">Date</span>
                <span className="detail-value">{formatDate(trade.exit_date)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Price</span>
                <span className="detail-value">${trade.exit_price.toFixed(4)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Reason</span>
                <span className="detail-value">{getExitReasonLabel(trade.exit_reason)}</span>
              </div>
            </div>
          </div>

          {/* Position Info */}
          <div className="detail-section">
            <h3>Position</h3>
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">Shares</span>
                <span className="detail-value">{trade.shares.toFixed(4)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Duration</span>
                <span className="detail-value">{trade.trade_duration_days} days</span>
              </div>
            </div>
          </div>

          {/* P&L Breakdown */}
          <div className="detail-section pnl-section">
            <h3>P&L Breakdown</h3>
            <div className="pnl-breakdown">
              <div className="pnl-item">
                <span className="pnl-label">Gross P&L</span>
                <span
                  className="pnl-value"
                  style={{ color: trade.pnl >= 0 ? "var(--accent)" : "var(--danger)" }}
                >
                  ${trade.pnl.toFixed(2)}
                </span>
              </div>
              <div className="pnl-item">
                <span className="pnl-label">P&L %</span>
                <span
                  className="pnl-value"
                  style={{
                    color: trade.pnl_pct >= 0 ? "var(--accent)" : "var(--danger)",
                  }}
                >
                  {trade.pnl_pct.toFixed(2)}%
                </span>
              </div>
              {trade.total_commission !== undefined && (
                <>
                  <div className="pnl-item">
                    <span className="pnl-label">Entry Commission</span>
                    <span className="pnl-value">
                      ${(trade.entry_commission || 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="pnl-item">
                    <span className="pnl-label">Exit Commission</span>
                    <span className="pnl-value">
                      ${(trade.exit_commission || 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="pnl-item total">
                    <span className="pnl-label">Total Commission</span>
                    <span className="pnl-value">
                      ${trade.total_commission.toFixed(2)}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Attribution Data */}
          {(trade.entry_conditions_met || trade.exit_conditions_met || trade.alpha !== undefined) && (
            <div className="detail-section">
              <h3>Attribution</h3>
              <div className="attribution-data">
                {trade.entry_conditions_met && trade.entry_conditions_met.length > 0 && (
                  <div className="attribution-item">
                    <span className="attribution-label">Entry Conditions Met</span>
                    <div className="conditions-list">
                      {trade.entry_conditions_met.map((cond, i) => (
                        <span key={i} className="condition-tag">
                          {cond}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {trade.exit_conditions_met && trade.exit_conditions_met.length > 0 && (
                  <div className="attribution-item">
                    <span className="attribution-label">Exit Conditions Met</span>
                    <div className="conditions-list">
                      {trade.exit_conditions_met.map((cond, i) => (
                        <span key={i} className="condition-tag">
                          {cond}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {trade.alpha !== undefined && (
                  <div className="attribution-item">
                    <span className="attribution-label">Alpha</span>
                    <span
                      className="attribution-value"
                      style={{ color: trade.alpha >= 0 ? "var(--accent)" : "var(--danger)" }}
                    >
                      {trade.alpha.toFixed(4)}
                    </span>
                  </div>
                )}
                {trade.market_return_during_trade !== undefined && (
                  <div className="attribution-item">
                    <span className="attribution-label">Market Return</span>
                    <span className="attribution-value">
                      {(trade.market_return_during_trade * 100).toFixed(2)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
