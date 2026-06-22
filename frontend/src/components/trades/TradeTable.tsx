import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import type { TradeLog, SortField, SortDirection } from "../../types";

interface TradeTableProps {
  trades: TradeLog[];
  sortField: SortField;
  sortDirection: SortDirection;
  onSort: (field: SortField) => void;
  onRowClick: (trade: TradeLog) => void;
}

const ROW_HEIGHT = 48;

const getExitReasonColor = (reason?: string): string => {
  if (!reason) return "var(--muted)";
  if (reason === "take_profit" || reason === "trailing_stop") return "var(--accent)";
  if (reason === "stop_loss" || reason === "liquidation") return "var(--danger)";
  if (reason === "signal") return "var(--ink)";
  return "var(--muted)";
};

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

const formatDate = (date: string): string => {
  return date.split("T")[0];
};

export default function TradeTable({
  trades,
  sortField,
  sortDirection,
  onSort,
  onRowClick,
}: TradeTableProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: trades.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 10,
  });

  const virtualItems = virtualizer.getVirtualItems();

  const columns: { key: SortField | "entry_price" | "exit_price" | "pnl_pct" | "exit_reason" | "direction"; label: string; sortable: boolean }[] = [
    { key: "direction", label: "Dir", sortable: false },
    { key: "entry_date", label: "Entry Date", sortable: true },
    { key: "entry_price", label: "Entry Price", sortable: false },
    { key: "exit_date", label: "Exit Date", sortable: true },
    { key: "exit_price", label: "Exit Price", sortable: false },
    { key: "shares", label: "Shares", sortable: true },
    { key: "pnl", label: "P&L", sortable: true },
    { key: "pnl_pct", label: "P&L %", sortable: false },
    { key: "trade_duration_days", label: "Duration", sortable: true },
    { key: "exit_reason", label: "Exit Reason", sortable: false },
  ];

  const getSortIndicator = (key: string) => {
    if (key !== sortField) return null;
    return sortDirection === "asc" ? " ↑" : " ↓";
  };

  const handleHeaderClick = (key: string, sortable: boolean) => {
    if (sortable) {
      onSort(key as SortField);
    }
  };

  return (
    <div className="trade-table-container">
      <div className="trade-table-header">
        {columns.map((col) => (
          <div
            key={col.key}
            className={`trade-table-cell header-cell ${col.sortable ? "sortable" : ""}`}
            onClick={() => handleHeaderClick(col.key, col.sortable)}
          >
            {col.label}
            {getSortIndicator(col.key)}
          </div>
        ))}
      </div>
      <div
        ref={parentRef}
        className="trade-table-body"
        style={{ height: "500px", overflow: "auto" }}
      >
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            width: "100%",
            position: "relative",
          }}
        >
          {virtualItems.map((virtualRow) => {
            const trade = trades[virtualRow.index];
            return (
              <div
                key={trade.id}
                className="trade-table-row"
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: `${ROW_HEIGHT}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
                onClick={() => onRowClick(trade)}
              >
                <div className="trade-table-cell">
                  <span
                    className="direction-badge"
                    style={{
                      background:
                        trade.direction === "SHORT"
                          ? "var(--danger)"
                          : "var(--accent)",
                    }}
                  >
                    {trade.direction === "SHORT" ? "S" : "L"}
                  </span>
                </div>
                <div className="trade-table-cell">{formatDate(trade.entry_date)}</div>
                <div className="trade-table-cell">${trade.entry_price.toFixed(4)}</div>
                <div className="trade-table-cell">{formatDate(trade.exit_date)}</div>
                <div className="trade-table-cell">${trade.exit_price.toFixed(4)}</div>
                <div className="trade-table-cell">{trade.shares.toFixed(4)}</div>
                <div
                  className="trade-table-cell"
                  style={{ color: trade.pnl >= 0 ? "var(--accent)" : "var(--danger)" }}
                >
                  ${trade.pnl.toFixed(2)}
                </div>
                <div
                  className="trade-table-cell"
                  style={{ color: trade.pnl_pct >= 0 ? "var(--accent)" : "var(--danger)" }}
                >
                  {trade.pnl_pct.toFixed(2)}%
                </div>
                <div className="trade-table-cell">{trade.trade_duration_days}d</div>
                <div className="trade-table-cell">
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
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
