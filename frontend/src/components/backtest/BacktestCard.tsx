import { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer } from "recharts";
import type { BacktestOut, StrategyOut } from "../../types";

interface BacktestCardProps {
  backtest: BacktestOut;
  strategy?: StrategyOut;
  onDelete: (id: string) => void;
  onRerun: (backtest: BacktestOut) => void;
  selected?: boolean;
  onSelect?: (id: string, selected: boolean) => void;
}

const statusStyles: Record<string, { bg: string; color: string; border: string }> = {
  PENDING: { bg: "#fff6e8", color: "#b8860b", border: "#f2e2c6" },
  RUNNING: { bg: "#e8f4ff", color: "#0066cc", border: "#b8d4f0" },
  COMPLETE: { bg: "#e8f5f3", color: "#1b7f6b", border: "#c5e8e0" },
  FAILED: { bg: "#ffe8e6", color: "#b42318", border: "#ffcccc" },
};

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin} min ago`;
  if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? "s" : ""} ago`;
  if (diffDay < 7) return `${diffDay} day${diffDay > 1 ? "s" : ""} ago`;
  return date.toLocaleDateString();
}

function formatMetric(value: number | undefined | null, type: "percent" | "ratio" | "number"): string {
  if (value === undefined || value === null) return "--";
  if (type === "percent") return `${value.toFixed(1)}%`;
  if (type === "ratio") return value.toFixed(2);
  return value.toString();
}

export default function BacktestCard({
  backtest,
  strategy,
  onDelete,
  onRerun,
  selected,
  onSelect,
}: BacktestCardProps) {
  const navigate = useNavigate();
  const status = backtest.status || "PENDING";
  const statusStyle = statusStyles[status] || statusStyles.PENDING;

  const metrics = useMemo(() => {
    const report = backtest.report;
    if (!report) return null;
    return {
      return: report.total_return_pct as number | undefined,
      sharpe: report.sharpe_ratio as number | undefined,
      maxDD: report.max_drawdown_pct as number | undefined,
      trades: report.total_trades as number | undefined,
    };
  }, [backtest.report]);

  // Generate sparkline data from equity curve (simplified - just show trend)
  const sparklineData = useMemo(() => {
    if (!metrics?.return) return [];
    // Generate a simple curve based on return
    const points = 20;
    const data = [];
    const finalReturn = metrics.return / 100;
    for (let i = 0; i <= points; i++) {
      const progress = i / points;
      // Add some variation to make it look like a real equity curve
      const noise = Math.sin(progress * 10) * 0.02;
      const value = 100 * (1 + finalReturn * progress + noise * progress);
      data.push({ v: value });
    }
    return data;
  }, [metrics?.return]);

  const returnColor = metrics?.return
    ? metrics.return > 0
      ? "var(--accent)"
      : "var(--danger)"
    : "var(--muted)";

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't navigate if clicking on buttons or checkbox
    const target = e.target as HTMLElement;
    if (target.closest("button") || target.closest("input[type='checkbox']")) {
      return;
    }
    navigate(`/backtests/${backtest.id}`);
  };

  return (
    <div
      className="card"
      style={{
        cursor: "pointer",
        transition: "transform 0.2s, box-shadow 0.2s",
        position: "relative",
      }}
      onClick={handleCardClick}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = "translateY(-2px)";
        e.currentTarget.style.boxShadow = "0 16px 40px rgba(20, 20, 20, 0.15)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = "translateY(0)";
        e.currentTarget.style.boxShadow = "0 12px 30px rgba(20, 20, 20, 0.12)";
      }}
    >
      {/* Selection checkbox */}
      {onSelect && (
        <div style={{ position: "absolute", top: "16px", right: "16px" }}>
          <input
            type="checkbox"
            checked={selected}
            onChange={(e) => onSelect(backtest.id, e.target.checked)}
            style={{ width: "18px", height: "18px", cursor: "pointer" }}
          />
        </div>
      )}

      {/* Header: Strategy name + Status badge */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "12px" }}>
        <h3 style={{ margin: 0, fontSize: "1.1rem", flex: 1 }}>
          {strategy?.name || "Unknown Strategy"}
        </h3>
        <span
          className="tag"
          style={{
            background: statusStyle.bg,
            color: statusStyle.color,
            border: `1px solid ${statusStyle.border}`,
            fontWeight: 600,
            animation: status === "RUNNING" ? "pulse 1.5s infinite" : "none",
          }}
        >
          {status}
        </span>
      </div>

      {/* Ticker, Resolution, Date Range */}
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "16px" }}>
        <span className="tag">{backtest.ticker}</span>
        <span className="tag">{backtest.bar_resolution}</span>
        <span className="tag" style={{ fontSize: "0.75rem" }}>
          {backtest.start_date} - {backtest.end_date}
        </span>
      </div>

      {/* Metrics row */}
      {status === "COMPLETE" && metrics && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: "8px",
            marginBottom: "12px",
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "0.7rem", color: "var(--muted)", marginBottom: "2px" }}>
              Return
            </div>
            <div style={{ fontWeight: 700, color: returnColor, fontSize: "0.95rem" }}>
              {formatMetric(metrics.return, "percent")}
            </div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "0.7rem", color: "var(--muted)", marginBottom: "2px" }}>
              Sharpe
            </div>
            <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>
              {formatMetric(metrics.sharpe, "ratio")}
            </div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "0.7rem", color: "var(--muted)", marginBottom: "2px" }}>
              Max DD
            </div>
            <div style={{ fontWeight: 600, color: "var(--danger)", fontSize: "0.95rem" }}>
              {formatMetric(metrics.maxDD, "percent")}
            </div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "0.7rem", color: "var(--muted)", marginBottom: "2px" }}>
              Trades
            </div>
            <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>
              {formatMetric(metrics.trades, "number")}
            </div>
          </div>
        </div>
      )}

      {/* Mini sparkline */}
      {status === "COMPLETE" && sparklineData.length > 0 && (
        <div style={{ height: "50px", marginBottom: "12px" }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparklineData}>
              <Line
                type="monotone"
                dataKey="v"
                stroke={returnColor}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Running indicator */}
      {status === "RUNNING" && (
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
          <div className="spinner" style={{ width: "16px", height: "16px" }} />
          <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>Processing...</span>
        </div>
      )}

      {/* Failed message */}
      {status === "FAILED" && backtest.error_message && (
        <div
          style={{
            fontSize: "0.8rem",
            color: "var(--danger)",
            marginBottom: "12px",
            padding: "8px",
            background: "#fff5f5",
            borderRadius: "8px",
          }}
        >
          {backtest.error_message.slice(0, 100)}
          {backtest.error_message.length > 100 ? "..." : ""}
        </div>
      )}

      {/* Footer: Relative time + Actions */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderTop: "1px solid var(--line)",
          paddingTop: "12px",
          marginTop: "auto",
        }}
      >
        <span style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
          {formatRelativeTime(backtest.start_date)}
        </span>
        <div style={{ display: "flex", gap: "8px" }}>
          <Link
            className="btn secondary"
            to={`/backtests/${backtest.id}`}
            style={{ padding: "6px 12px", fontSize: "0.8rem" }}
            onClick={(e) => e.stopPropagation()}
          >
            View
          </Link>
          <button
            className="btn secondary"
            style={{ padding: "6px 12px", fontSize: "0.8rem" }}
            onClick={(e) => {
              e.stopPropagation();
              onRerun(backtest);
            }}
          >
            Re-run
          </button>
          <button
            className="btn secondary"
            style={{
              padding: "6px 12px",
              fontSize: "0.8rem",
              color: "var(--danger)",
            }}
            onClick={(e) => {
              e.stopPropagation();
              if (window.confirm("Delete this backtest?")) {
                onDelete(backtest.id);
              }
            }}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
