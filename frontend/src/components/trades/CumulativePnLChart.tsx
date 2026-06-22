import { useMemo } from "react";
import type { TradeLog } from "../../types";

interface CumulativePnLChartProps {
  trades: TradeLog[];
}

export default function CumulativePnLChart({ trades }: CumulativePnLChartProps) {
  const chartData = useMemo(() => {
    if (trades.length === 0) return { points: [], minPnl: 0, maxPnl: 0 };

    // Sort trades by exit date
    const sortedTrades = [...trades].sort(
      (a, b) => new Date(a.exit_date).getTime() - new Date(b.exit_date).getTime()
    );

    let cumulative = 0;
    const points = sortedTrades.map((trade) => {
      cumulative += trade.pnl;
      return {
        date: trade.exit_date,
        cumPnl: cumulative,
      };
    });

    const cumulatives = points.map((p) => p.cumPnl);
    const minPnl = Math.min(0, ...cumulatives);
    const maxPnl = Math.max(0, ...cumulatives);

    return { points, minPnl, maxPnl };
  }, [trades]);

  const { points, minPnl, maxPnl } = chartData;

  if (trades.length === 0) {
    return (
      <div className="chart-card">
        <h3>Cumulative P&L</h3>
        <div className="chart-empty">No trades to display</div>
      </div>
    );
  }

  // Calculate SVG path for area chart
  const width = 400;
  const height = 150;
  const padding = { top: 10, right: 10, bottom: 20, left: 50 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const range = maxPnl - minPnl || 1;
  const xScale = (i: number) => padding.left + (i / (points.length - 1 || 1)) * chartWidth;
  const yScale = (value: number) =>
    padding.top + chartHeight - ((value - minPnl) / range) * chartHeight;

  const zeroY = yScale(0);

  // Build path
  let linePath = `M ${xScale(0)} ${yScale(points[0]?.cumPnl || 0)}`;
  for (let i = 1; i < points.length; i++) {
    linePath += ` L ${xScale(i)} ${yScale(points[i].cumPnl)}`;
  }

  // Area path (fill to zero line)
  let areaPath = linePath;
  areaPath += ` L ${xScale(points.length - 1)} ${zeroY}`;
  areaPath += ` L ${xScale(0)} ${zeroY}`;
  areaPath += " Z";

  const finalPnl = points[points.length - 1]?.cumPnl || 0;
  const isPositive = finalPnl >= 0;

  return (
    <div className="chart-card">
      <h3>Cumulative P&L</h3>
      <div className="cumulative-chart-container">
        <svg viewBox={`0 0 ${width} ${height}`} className="cumulative-chart-svg">
          {/* Zero line */}
          <line
            x1={padding.left}
            y1={zeroY}
            x2={width - padding.right}
            y2={zeroY}
            stroke="var(--line)"
            strokeDasharray="4,4"
          />

          {/* Area fill */}
          <path
            d={areaPath}
            fill={isPositive ? "rgba(27, 127, 107, 0.2)" : "rgba(180, 35, 24, 0.2)"}
          />

          {/* Line */}
          <path
            d={linePath}
            fill="none"
            stroke={isPositive ? "var(--accent)" : "var(--danger)"}
            strokeWidth="2"
          />

          {/* Y-axis labels */}
          <text
            x={padding.left - 5}
            y={padding.top + 5}
            textAnchor="end"
            className="chart-label"
          >
            ${maxPnl.toFixed(0)}
          </text>
          <text
            x={padding.left - 5}
            y={height - padding.bottom}
            textAnchor="end"
            className="chart-label"
          >
            ${minPnl.toFixed(0)}
          </text>
          {minPnl < 0 && maxPnl > 0 && (
            <text
              x={padding.left - 5}
              y={zeroY + 4}
              textAnchor="end"
              className="chart-label"
            >
              $0
            </text>
          )}
        </svg>
        <div className="cumulative-chart-summary">
          <span
            className="cumulative-total"
            style={{ color: isPositive ? "var(--accent)" : "var(--danger)" }}
          >
            Total: ${finalPnl.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}
