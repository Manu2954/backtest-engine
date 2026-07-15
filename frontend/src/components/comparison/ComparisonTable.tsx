import type { BacktestOut } from "../../types";
import { cn } from "@/lib/utils";

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

export function getChartColor(index: number): string {
  return `hsl(var(--chart-${(index % 5) + 1}))`;
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
      <div className="overflow-x-auto">
        <table className="table">
          <thead>
            <tr>
              <th className="min-w-[140px]">Metric</th>
              {backtests.map((bt, index) => (
                <th key={bt.id} className="min-w-[120px]">
                  <div className="flex items-center gap-2">
                    <span
                      className="inline-block h-3 w-3 rounded-full"
                      style={{ background: getChartColor(index) }}
                    />
                    <span>{bt.ticker}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
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
                  <td className="font-semibold">{metric.label}</td>
                  {values.map((value, index) => {
                    const isBest = bestIndex === index;
                    const isWorst = worstIndex === index;

                    return (
                      <td
                        key={backtests[index].id}
                        className={cn(
                          isBest && "font-bold text-profit bg-profit/10",
                          isWorst && "font-bold text-loss bg-loss/10"
                        )}
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

      <div className="mt-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm border border-profit bg-profit/30" />
            <span className="text-sm text-muted-foreground">Best in row</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm border border-loss bg-loss/30" />
            <span className="text-sm text-muted-foreground">Worst in row</span>
          </div>
        </div>
      </div>
    </div>
  );
}
