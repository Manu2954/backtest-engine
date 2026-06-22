import { useMemo, useState } from "react";
import {
  Area,
  Brush,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BacktestOut, TradeLog } from "../../types";

interface EquityCurveProps {
  run: BacktestOut;
  trades: TradeLog[];
}

interface EquityPoint {
  date: string;
  equity: number;
  benchmark: number;
  drawdown: number;
  dailyReturn: number;
  isEntry?: boolean;
  isExit?: boolean;
}

export default function EquityCurve({ run, trades }: EquityCurveProps) {
  const [showDrawdown, setShowDrawdown] = useState(false);
  const [showTradeMarkers, setShowTradeMarkers] = useState(false);

  const equitySeries = useMemo((): EquityPoint[] => {
    if (!run) return [];
    const initial = run.initial_capital || 0;
    let capital = initial;
    let peak = initial;
    let prevCapital = initial;

    const benchmarkReturn = run.report?.benchmark_return_pct || 0;
    const benchmarkMultiplier = 1 + benchmarkReturn / 100;
    const totalDays = Math.max(
      1,
      (new Date(run.end_date).getTime() - new Date(run.start_date).getTime()) / (1000 * 60 * 60 * 24)
    );

    // Create a map of entry/exit dates
    const entryDates = new Set(trades.map((t) => t.entry_date));
    const exitDates = new Set(trades.map((t) => t.exit_date));

    const points: EquityPoint[] = [
      {
        date: run.start_date,
        equity: Number(capital.toFixed(2)),
        benchmark: Number(initial.toFixed(2)),
        drawdown: 0,
        dailyReturn: 0,
        isEntry: entryDates.has(run.start_date),
        isExit: exitDates.has(run.start_date),
      },
    ];

    const sorted = [...trades].sort((a, b) => a.exit_date.localeCompare(b.exit_date));

    for (const trade of sorted) {
      prevCapital = capital;
      capital += trade.pnl;
      peak = Math.max(peak, capital);

      const daysSinceStart = Math.max(
        0,
        (new Date(trade.exit_date).getTime() - new Date(run.start_date).getTime()) /
          (1000 * 60 * 60 * 24)
      );
      const benchmarkProgress = Math.pow(benchmarkMultiplier, daysSinceStart / totalDays);
      const drawdown = peak > 0 ? ((capital - peak) / peak) * 100 : 0;
      const dailyReturn = prevCapital > 0 ? ((capital - prevCapital) / prevCapital) * 100 : 0;

      points.push({
        date: trade.exit_date,
        equity: Number(capital.toFixed(2)),
        benchmark: Number((initial * benchmarkProgress).toFixed(2)),
        drawdown: Number(drawdown.toFixed(2)),
        dailyReturn: Number(dailyReturn.toFixed(2)),
        isEntry: entryDates.has(trade.exit_date),
        isExit: true,
      });
    }
    return points;
  }, [run, trades]);

  const entryPoints = useMemo(() => {
    if (!showTradeMarkers) return [];
    return equitySeries.filter((p) => p.isEntry);
  }, [equitySeries, showTradeMarkers]);

  const exitPoints = useMemo(() => {
    if (!showTradeMarkers) return [];
    return equitySeries.filter((p) => p.isExit);
  }, [equitySeries, showTradeMarkers]);

  if (equitySeries.length === 0) {
    return (
      <div className="card">
        <h2>Equity Curve</h2>
        <p className="notice">No equity data yet.</p>
      </div>
    );
  }

  const hasBenchmark = run?.report?.benchmark_return_pct !== undefined;

  return (
    <div className="card">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
        }}
      >
        <h2 style={{ margin: 0 }}>Equity Curve</h2>
        <div style={{ display: "flex", gap: "12px" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={showDrawdown}
              onChange={(e) => setShowDrawdown(e.target.checked)}
            />
            <span style={{ fontSize: "0.85rem" }}>Show Drawdown</span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={showTradeMarkers}
              onChange={(e) => setShowTradeMarkers(e.target.checked)}
            />
            <span style={{ fontSize: "0.85rem" }}>Trade Markers</span>
          </label>
        </div>
      </div>

      <div style={{ width: "100%", height: 400 }}>
        <ResponsiveContainer>
          <ComposedChart data={equitySeries} margin={{ top: 5, right: 20, left: 20, bottom: 30 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0d7cc" />
            <XAxis dataKey="date" stroke="#6a6157" style={{ fontSize: "0.85rem" }} />
            <YAxis
              yAxisId="equity"
              stroke="#6a6157"
              style={{ fontSize: "0.85rem" }}
              tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
            />
            {showDrawdown && (
              <YAxis
                yAxisId="drawdown"
                orientation="right"
                stroke="var(--danger)"
                style={{ fontSize: "0.85rem" }}
                tickFormatter={(value) => `${value}%`}
                domain={["auto", 0]}
              />
            )}
            <Tooltip
              contentStyle={{
                background: "white",
                border: "1px solid #e0d7cc",
                borderRadius: "8px",
                padding: "12px",
              }}
              content={({ active, payload, label }) => {
                if (!active || !payload || !payload.length) return null;
                const data = payload[0]?.payload as EquityPoint;
                return (
                  <div
                    style={{
                      background: "white",
                      border: "1px solid #e0d7cc",
                      borderRadius: "8px",
                      padding: "12px",
                      fontSize: "0.85rem",
                    }}
                  >
                    <div style={{ fontWeight: 600, marginBottom: "8px" }}>{label}</div>
                    <div style={{ color: "var(--accent)" }}>
                      Equity: $
                      {data.equity.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </div>
                    {hasBenchmark && (
                      <div style={{ color: "var(--accent-2)" }}>
                        Benchmark: $
                        {data.benchmark.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </div>
                    )}
                    {showDrawdown && (
                      <div style={{ color: "var(--danger)" }}>Drawdown: {data.drawdown}%</div>
                    )}
                    <div style={{ color: data.dailyReturn >= 0 ? "var(--accent)" : "var(--danger)" }}>
                      Daily Return: {data.dailyReturn >= 0 ? "+" : ""}
                      {data.dailyReturn}%
                    </div>
                  </div>
                );
              }}
            />
            <Legend />

            {/* Drawdown area */}
            {showDrawdown && (
              <>
                <ReferenceLine yAxisId="drawdown" y={0} stroke="#ccc" />
                <Area
                  yAxisId="drawdown"
                  type="monotone"
                  dataKey="drawdown"
                  fill="rgba(180, 35, 24, 0.2)"
                  stroke="var(--danger)"
                  strokeWidth={1}
                  name="Drawdown"
                />
              </>
            )}

            {/* Equity line */}
            <Line
              yAxisId="equity"
              type="monotone"
              dataKey="equity"
              stroke="var(--accent)"
              strokeWidth={2.5}
              dot={false}
              name="Strategy"
            />

            {/* Benchmark line */}
            {hasBenchmark && (
              <Line
                yAxisId="equity"
                type="monotone"
                dataKey="benchmark"
                stroke="var(--accent-2)"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                name="Buy & Hold"
              />
            )}

            {/* Trade markers */}
            {showTradeMarkers && entryPoints.length > 0 && (
              <Scatter
                yAxisId="equity"
                data={entryPoints}
                fill="var(--accent)"
                name="Entry"
                shape="triangle"
              />
            )}
            {showTradeMarkers && exitPoints.length > 0 && (
              <Scatter
                yAxisId="equity"
                data={exitPoints}
                fill="var(--danger)"
                name="Exit"
                shape="circle"
              />
            )}

            {/* Brush for zoom/pan */}
            <Brush
              dataKey="date"
              height={30}
              stroke="var(--accent)"
              fill="#faf8f5"
              travellerWidth={10}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
