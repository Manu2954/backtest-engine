import { useState, type CSSProperties } from "react";
import { Link } from "react-router-dom";
import type { StrategyOut, BacktestOut, IndicatorType } from "../../types";

interface StrategyCardProps {
  strategy: StrategyOut;
  backtests: BacktestOut[];
  onRunBacktest: (strategy: StrategyOut) => void;
  onDelete: (strategy: StrategyOut) => void;
  isDeleting?: boolean;
}

const cardStyle: CSSProperties = {
  background: "var(--card)",
  borderRadius: "var(--radius)",
  boxShadow: "var(--shadow)",
  padding: "20px",
  border: "1px solid var(--line)",
  display: "flex",
  flexDirection: "column",
  gap: "14px",
  transition: "transform 0.2s, box-shadow 0.2s",
};

const cardHoverStyle: CSSProperties = {
  transform: "translateY(-2px)",
  boxShadow: "0 16px 40px rgba(20, 20, 20, 0.16)",
};

const headerStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  gap: "12px",
};

const titleStyle: CSSProperties = {
  fontFamily: "'Fraunces', 'Space Grotesk', serif",
  fontSize: "1.1rem",
  fontWeight: 600,
  margin: 0,
  lineHeight: 1.3,
};

const descriptionStyle: CSSProperties = {
  fontSize: "0.9rem",
  color: "var(--muted)",
  margin: 0,
  lineHeight: 1.5,
  overflow: "hidden",
  display: "-webkit-box",
  WebkitLineClamp: 2,
  WebkitBoxOrient: "vertical",
  minHeight: "2.7em",
};

const badgeContainerStyle: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "6px",
};

const badgeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  padding: "4px 10px",
  borderRadius: "999px",
  fontSize: "0.75rem",
  fontWeight: 600,
};

const indicatorChipStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  padding: "3px 8px",
  borderRadius: "6px",
  fontSize: "0.75rem",
  fontWeight: 500,
  background: "#f3efe9",
  color: "var(--muted)",
};

const metricsContainerStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(3, 1fr)",
  gap: "8px",
  padding: "12px",
  borderRadius: "10px",
  background: "#faf8f5",
  border: "1px solid var(--line)",
};

const metricStyle: CSSProperties = {
  textAlign: "center",
};

const metricLabelStyle: CSSProperties = {
  fontSize: "0.7rem",
  color: "var(--muted)",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
};

const metricValueStyle: CSSProperties = {
  fontSize: "0.9rem",
  fontWeight: 600,
  marginTop: "2px",
};

const actionsStyle: CSSProperties = {
  display: "flex",
  gap: "8px",
  marginTop: "auto",
  paddingTop: "4px",
};

const actionButtonStyle: CSSProperties = {
  flex: 1,
  padding: "8px 12px",
  borderRadius: "8px",
  border: "none",
  fontSize: "0.85rem",
  fontWeight: 600,
  cursor: "pointer",
  transition: "transform 0.15s, background 0.15s",
};

const menuButtonStyle: CSSProperties = {
  padding: "8px",
  borderRadius: "8px",
  border: "none",
  background: "#f0ede8",
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const dropdownStyle: CSSProperties = {
  position: "absolute",
  top: "100%",
  right: 0,
  marginTop: "4px",
  background: "#fff",
  border: "1px solid var(--line)",
  borderRadius: "10px",
  boxShadow: "var(--shadow)",
  padding: "6px",
  zIndex: 10,
  minWidth: "120px",
};

const dropdownItemStyle: CSSProperties = {
  display: "block",
  width: "100%",
  padding: "8px 12px",
  borderRadius: "6px",
  border: "none",
  background: "transparent",
  fontSize: "0.85rem",
  fontWeight: 500,
  cursor: "pointer",
  textAlign: "left",
  transition: "background 0.15s",
};

function getIndicatorBadgeColor(count: number): CSSProperties {
  if (count <= 2) {
    return { background: "#e8e5e0", color: "#6a6157" }; // Gray
  } else if (count <= 5) {
    return { background: "#dceffe", color: "#1565c0" }; // Blue
  } else {
    return { background: "#ede7f6", color: "#7b1fa2" }; // Purple
  }
}

function getIndicatorTypes(strategy: StrategyOut): IndicatorType[] {
  const types = new Set<IndicatorType>();
  strategy.indicators.forEach((ind) => types.add(ind.indicator_type));
  return Array.from(types);
}

function getConditionCounts(strategy: StrategyOut): { entry: number; exit: number } {
  let entry = 0;
  let exit = 0;
  strategy.condition_groups.forEach((group) => {
    if (group.group_type === "ENTRY") {
      entry += group.conditions.length;
    } else {
      exit += group.conditions.length;
    }
  });
  return { entry, exit };
}

function getBestBacktest(backtests: BacktestOut[]): BacktestOut | null {
  const completed = backtests.filter((b) => b.status === "COMPLETED" && b.report);
  if (completed.length === 0) return null;
  // Return the one with highest total return
  return completed.reduce((best, current) => {
    const bestReturn = best.report?.total_return_pct ?? -Infinity;
    const currentReturn = current.report?.total_return_pct ?? -Infinity;
    return currentReturn > bestReturn ? current : best;
  });
}

export default function StrategyCard({
  strategy,
  backtests,
  onRunBacktest,
  onDelete,
  isDeleting,
}: StrategyCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const indicatorCount = strategy.indicators.length;
  const indicatorTypes = getIndicatorTypes(strategy);
  const conditionCounts = getConditionCounts(strategy);
  const bestBacktest = getBestBacktest(backtests);

  const handleMouseLeave = () => {
    setIsHovered(false);
    setMenuOpen(false);
  };

  return (
    <div
      style={{ ...cardStyle, ...(isHovered ? cardHoverStyle : {}) }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={handleMouseLeave}
    >
      {/* Header */}
      <div style={headerStyle}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h3 style={titleStyle}>{strategy.name}</h3>
        </div>
        {/* Overflow Menu */}
        <div style={{ position: "relative" }}>
          <button
            type="button"
            style={menuButtonStyle}
            onClick={() => setMenuOpen(!menuOpen)}
            title="More actions"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="5" r="2" />
              <circle cx="12" cy="12" r="2" />
              <circle cx="12" cy="19" r="2" />
            </svg>
          </button>
          {menuOpen && (
            <div style={dropdownStyle}>
              <Link
                to={`/strategies/${strategy.id}`}
                style={{ ...dropdownItemStyle, color: "var(--ink)", textDecoration: "none" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "#f0ede8")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                Edit
              </Link>
              <button
                type="button"
                style={{ ...dropdownItemStyle, color: "var(--danger)" }}
                onClick={() => {
                  setMenuOpen(false);
                  onDelete(strategy);
                }}
                disabled={isDeleting}
                onMouseEnter={(e) => (e.currentTarget.style.background = "#fff6f5")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                {isDeleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Description */}
      <p style={descriptionStyle}>{strategy.description || "No description provided."}</p>

      {/* Complexity Badges */}
      <div style={badgeContainerStyle}>
        <span style={{ ...badgeStyle, ...getIndicatorBadgeColor(indicatorCount) }}>
          {indicatorCount} Indicator{indicatorCount !== 1 ? "s" : ""}
        </span>
        <span style={{ ...badgeStyle, background: "#e8f5e9", color: "#2e7d32" }}>
          {conditionCounts.entry} Entry / {conditionCounts.exit} Exit
        </span>
      </div>

      {/* Indicator Chips */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
        {indicatorTypes.slice(0, 4).map((type) => (
          <span key={type} style={indicatorChipStyle}>
            {type}
          </span>
        ))}
        {indicatorTypes.length > 4 && (
          <span style={indicatorChipStyle}>+{indicatorTypes.length - 4}</span>
        )}
      </div>

      {/* Performance Preview */}
      {bestBacktest && bestBacktest.report && (
        <div style={metricsContainerStyle}>
          <div style={metricStyle}>
            <div style={metricLabelStyle}>Return</div>
            <div
              style={{
                ...metricValueStyle,
                color:
                  (bestBacktest.report.total_return_pct ?? 0) >= 0 ? "#2e7d32" : "var(--danger)",
              }}
            >
              {(bestBacktest.report.total_return_pct ?? 0).toFixed(1)}%
            </div>
          </div>
          <div style={metricStyle}>
            <div style={metricLabelStyle}>Win Rate</div>
            <div style={metricValueStyle}>{(bestBacktest.report.win_rate ?? 0).toFixed(0)}%</div>
          </div>
          <div style={metricStyle}>
            <div style={metricLabelStyle}>Sharpe</div>
            <div style={metricValueStyle}>{(bestBacktest.report.sharpe_ratio ?? 0).toFixed(2)}</div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div style={actionsStyle}>
        <Link
          to={`/strategies/${strategy.id}`}
          style={{
            ...actionButtonStyle,
            background: "#f0ede8",
            color: "var(--ink)",
            textAlign: "center",
            textDecoration: "none",
          }}
        >
          Edit
        </Link>
        <button
          type="button"
          style={{
            ...actionButtonStyle,
            background: "var(--accent)",
            color: "white",
            boxShadow: "0 6px 16px rgba(27, 127, 107, 0.2)",
          }}
          onClick={() => onRunBacktest(strategy)}
        >
          Run Backtest
        </button>
      </div>
    </div>
  );
}
