import type { BacktestOut } from "../../types";

interface ComparisonTableProps {
  backtests: BacktestOut[];
}

interface MetricConfig {
  key: string;
  label: string;
  format: (value: number) => string;
  higherIsBetter: boolean;
}

const METRICS: MetricConfig[] = [
  {
    key: "total_return_pct",
    label: "Return %",
    format: (v) => `${v.toFixed(2)}%`,
    higherIsBetter: true,
  },
  {
    key: "sharpe_ratio",
    label: "Sharpe Ratio",
    format: (v) => v.toFixed(2),
    higherIsBetter: true,
  },
  {
    key: "max_drawdown_pct",
    label: "Max Drawdown",
    format: (v) => `${v.toFixed(2)}%`,
    higherIsBetter: false,
  },
  {
    key: "win_rate",
    label: "Win Rate",
    format: (v) => `${v.toFixed(2)}%`,
    higherIsBetter: true,
  },
  {
    key: "total_trades",
    label: "Total Trades",
    format: (v) => v.toString(),
    higherIsBetter: true,
  },
  {
    key: "profit_factor",
    label: "Profit Factor",
    format: (v) => v.toFixed(2),
    higherIsBetter: true,
  },
  {
    key: "cagr",
    label: "CAGR",
    format: (v) => `${v.toFixed(2)}%`,
    higherIsBetter: true,
  },
  {
    key: "alpha",
    label: "Alpha",
    format: (v) => v.toFixed(2),
    higherIsBetter: true,
  },
];

const CHART_COLORS = [
  "#1f6feb", // blue
  "#8957e5", // purple
  "#d29922", // amber
  "#2ea043", // green
  "#00b4d8", // cyan
];

export function getChartColor(index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length];
}

export default function ComparisonTable({ backtests }: ComparisonTableProps) {
  if (backtests.length === 0) {
    return (
      <div className="card">
        <div className="notice">No backtests selected for comparison.</div>
      </div>
    );
  }

  const getMetricValues = (metricKey: string): (number | null)[] => {
    return backtests.map((bt) => {
      const value = bt.report?.[metricKey];
      return typeof value === "number" ? value : null;
    });
  };

  const findBestWorst = (
    values: (number | null)[],
    higherIsBetter: boolean
  ): { bestIndex: number | null; worstIndex: number | null } => {
    const validValues = values
      .map((v, i) => ({ value: v, index: i }))
      .filter((item) => item.value !== null) as { value: number; index: number }[];

    if (validValues.length < 2) {
      return { bestIndex: null, worstIndex: null };
    }

    const sorted = [...validValues].sort((a, b) =>
      higherIsBetter ? b.value - a.value : a.value - b.value
    );

    return {
      bestIndex: sorted[0].index,
      worstIndex: sorted[sorted.length - 1].index,
    };
  };

  return (
    <div className="card">
      <h2>Performance Comparison</h2>
      <div style={{ overflowX: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th style={{ minWidth: "140px" }}>Metric</th>
              {backtests.map((bt, index) => (
                <th key={bt.id} style={{ minWidth: "120px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span
                      style={{
                        width: "12px",
                        height: "12px",
                        borderRadius: "50%",
                        background: getChartColor(index),
                        display: "inline-block",
                      }}
                    />
                    <span>{bt.ticker}</span>
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
                    {bt.start_date.slice(0, 7)} - {bt.end_date.slice(0, 7)}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRICS.map((metric) => {
              const values = getMetricValues(metric.key);
              const { bestIndex, worstIndex } = findBestWorst(
                values,
                metric.higherIsBetter
              );

              return (
                <tr key={metric.key}>
                  <td style={{ fontWeight: 600 }}>{metric.label}</td>
                  {values.map((value, index) => {
                    const isBest = bestIndex === index;
                    const isWorst = worstIndex === index;

                    return (
                      <td
                        key={backtests[index].id}
                        style={{
                          fontWeight: isBest || isWorst ? 700 : 400,
                          color: isBest
                            ? "var(--accent)"
                            : isWorst
                            ? "var(--danger)"
                            : "inherit",
                          background: isBest
                            ? "rgba(27, 127, 107, 0.1)"
                            : isWorst
                            ? "rgba(180, 35, 24, 0.1)"
                            : undefined,
                        }}
                      >
                        {value !== null ? metric.format(value) : "N/A"}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: "16px" }}>
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span
              style={{
                width: "12px",
                height: "12px",
                background: "rgba(27, 127, 107, 0.3)",
                border: "1px solid var(--accent)",
                borderRadius: "2px",
              }}
            />
            <span style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
              Best in row
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span
              style={{
                width: "12px",
                height: "12px",
                background: "rgba(180, 35, 24, 0.3)",
                border: "1px solid var(--danger)",
                borderRadius: "2px",
              }}
            />
            <span style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
              Worst in row
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
