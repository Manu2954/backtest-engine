import { useEffect, useState, useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { getBacktestTrades } from "../../api";
import type { BacktestOut, TradeLog } from "../../types";
import { getChartColor } from "./ComparisonTable";

interface OverlaidEquityCurveProps {
  backtests: BacktestOut[];
}

interface EquityDataPoint {
  date: string;
  [key: string]: number | string;
}

export default function OverlaidEquityCurve({ backtests }: OverlaidEquityCurveProps) {
  const [tradesMap, setTradesMap] = useState<Record<string, TradeLog[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (backtests.length === 0) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    Promise.all(
      backtests.map((bt) =>
        getBacktestTrades(bt.id, { limit: 1000, offset: 0 }).then((trades) => ({
          id: bt.id,
          trades,
        }))
      )
    )
      .then((results) => {
        const map: Record<string, TradeLog[]> = {};
        results.forEach((result) => {
          map[result.id] = result.trades;
        });
        setTradesMap(map);
      })
      .catch((err) => setError(err.message || "Failed to load trades"))
      .finally(() => setLoading(false));
  }, [backtests]);

  const chartData = useMemo(() => {
    if (backtests.length === 0) return [];

    // Collect all unique dates across all backtests
    const allDates = new Set<string>();

    backtests.forEach((bt) => {
      allDates.add(bt.start_date);
      allDates.add(bt.end_date);
      const trades = tradesMap[bt.id] || [];
      trades.forEach((t) => allDates.add(t.exit_date));
    });

    const sortedDates = Array.from(allDates).sort();

    // Build equity curves for each backtest
    const equityCurves: Record<string, Map<string, number>> = {};

    backtests.forEach((bt) => {
      const trades = tradesMap[bt.id] || [];
      const sorted = [...trades].sort((a, b) =>
        a.exit_date.localeCompare(b.exit_date)
      );

      const curve = new Map<string, number>();
      let capital = bt.initial_capital;

      // Start date
      curve.set(bt.start_date, capital);

      // After each trade
      for (const trade of sorted) {
        capital += trade.pnl;
        curve.set(trade.exit_date, capital);
      }

      // Ensure end date has the final value
      if (!curve.has(bt.end_date)) {
        curve.set(bt.end_date, capital);
      }

      equityCurves[bt.id] = curve;
    });

    // Build chart data with all backtests normalized to percentage return
    const data: EquityDataPoint[] = [];

    sortedDates.forEach((date) => {
      const point: EquityDataPoint = { date };

      backtests.forEach((bt, index) => {
        const curve = equityCurves[bt.id];
        if (!curve) return;

        // Find the most recent value at or before this date
        let value: number | null = null;
        const curveEntries = Array.from(curve.entries()).sort((a, b) =>
          a[0].localeCompare(b[0])
        );

        for (const [entryDate, entryValue] of curveEntries) {
          if (entryDate <= date) {
            value = entryValue;
          } else {
            break;
          }
        }

        if (value !== null) {
          // Calculate percentage return from initial capital
          const returnPct = ((value - bt.initial_capital) / bt.initial_capital) * 100;
          point[`equity_${index}`] = Number(returnPct.toFixed(2));
        }
      });

      // Only add point if at least one backtest has data
      const hasData = backtests.some(
        (_, index) => point[`equity_${index}`] !== undefined
      );
      if (hasData) {
        data.push(point);
      }
    });

    return data;
  }, [backtests, tradesMap]);

  if (loading) {
    return (
      <div className="card">
        <h2>Overlaid Equity Curves</h2>
        <div className="row" style={{ alignItems: "center", padding: "20px 0" }}>
          <div className="spinner" />
          <span>Loading equity data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h2>Overlaid Equity Curves</h2>
        <div className="notice">{error}</div>
      </div>
    );
  }

  if (chartData.length === 0) {
    return (
      <div className="card">
        <h2>Overlaid Equity Curves</h2>
        <div className="notice">No equity data available.</div>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Overlaid Equity Curves</h2>
      <p style={{ color: "var(--muted)", marginBottom: "16px" }}>
        Normalized percentage return comparison. Each curve shows cumulative return
        from initial capital.
      </p>
      <div style={{ width: "100%", height: 400 }}>
        <ResponsiveContainer>
          <LineChart
            data={chartData}
            margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e0d7cc" />
            <XAxis
              dataKey="date"
              stroke="#6a6157"
              style={{ fontSize: "0.85rem" }}
              tickFormatter={(value: string) =>
                value.length >= 7 ? value.slice(0, 7) : value
              }
            />
            <YAxis
              stroke="#6a6157"
              style={{ fontSize: "0.85rem" }}
              tickFormatter={(value: number) => `${value.toFixed(0)}%`}
            />
            <Tooltip
              contentStyle={{
                background: "white",
                border: "1px solid #e0d7cc",
                borderRadius: "8px",
                padding: "8px",
              }}
              formatter={(value: unknown, name: unknown) => {
                const numValue = typeof value === "number" ? value : 0;
                const strName = String(name || "");
                const index = parseInt(strName.replace("equity_", ""), 10);
                const bt = backtests[index];
                return [
                  `${numValue.toFixed(2)}%`,
                  bt ? bt.ticker : strName,
                ];
              }}
              labelFormatter={(label: unknown) => `Date: ${String(label)}`}
            />
            <Legend
              formatter={(value: string) => {
                const index = parseInt(value.replace("equity_", ""), 10);
                const bt = backtests[index];
                return bt ? bt.ticker : value;
              }}
            />
            {backtests.map((bt, index) => (
              <Line
                key={bt.id}
                type="monotone"
                dataKey={`equity_${index}`}
                stroke={getChartColor(index)}
                strokeWidth={2.5}
                dot={false}
                name={`equity_${index}`}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div style={{ marginTop: "16px" }}>
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
          {backtests.map((bt, index) => (
            <div
              key={bt.id}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <span
                style={{
                  width: "20px",
                  height: "3px",
                  background: getChartColor(index),
                  display: "inline-block",
                  borderRadius: "2px",
                }}
              />
              <span style={{ fontSize: "0.85rem" }}>
                {bt.ticker} ({bt.asset_class})
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
