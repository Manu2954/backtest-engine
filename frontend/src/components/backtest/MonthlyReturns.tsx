import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TradeLog } from "../../types";

interface MonthlyReturnsProps {
  trades: TradeLog[];
  initialCapital: number;
}

interface MonthlyData {
  month: string;
  return_pct: number;
  pnl: number;
  tradeCount: number;
}

export default function MonthlyReturns({ trades, initialCapital }: MonthlyReturnsProps) {
  const monthlyData = useMemo((): MonthlyData[] => {
    if (!trades.length) return [];

    // Group trades by month (using exit_date)
    const byMonth: Record<string, { pnl: number; count: number }> = {};

    for (const trade of trades) {
      const date = new Date(trade.exit_date);
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;

      if (!byMonth[monthKey]) {
        byMonth[monthKey] = { pnl: 0, count: 0 };
      }
      byMonth[monthKey].pnl += trade.pnl;
      byMonth[monthKey].count += 1;
    }

    // Sort by month and calculate return percentages
    const sortedMonths = Object.keys(byMonth).sort();
    let runningCapital = initialCapital;

    return sortedMonths.map((month) => {
      const { pnl, count } = byMonth[month];
      const returnPct = runningCapital > 0 ? (pnl / runningCapital) * 100 : 0;
      runningCapital += pnl;

      // Format month for display (e.g., "Jan 24")
      const [year, m] = month.split("-");
      const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const displayMonth = `${monthNames[parseInt(m) - 1]} ${year.slice(2)}`;

      return {
        month: displayMonth,
        return_pct: Number(returnPct.toFixed(2)),
        pnl: Number(pnl.toFixed(2)),
        tradeCount: count,
      };
    });
  }, [trades, initialCapital]);

  if (monthlyData.length === 0) {
    return (
      <div className="card">
        <h2>Monthly Returns</h2>
        <p className="notice">No monthly data available.</p>
      </div>
    );
  }

  const positiveMonths = monthlyData.filter((d) => d.return_pct > 0).length;
  const negativeMonths = monthlyData.filter((d) => d.return_pct < 0).length;
  const avgReturn =
    monthlyData.reduce((sum, d) => sum + d.return_pct, 0) / monthlyData.length;

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
        <h2 style={{ margin: 0 }}>Monthly Returns</h2>
        <div style={{ display: "flex", gap: "16px", fontSize: "0.85rem" }}>
          <span style={{ color: "var(--accent)" }}>+{positiveMonths} months</span>
          <span style={{ color: "var(--danger)" }}>-{negativeMonths} months</span>
          <span style={{ color: "var(--muted)" }}>
            Avg: {avgReturn >= 0 ? "+" : ""}
            {avgReturn.toFixed(2)}%
          </span>
        </div>
      </div>

      <div style={{ width: "100%", height: 250 }}>
        <ResponsiveContainer>
          <BarChart data={monthlyData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0d7cc" vertical={false} />
            <XAxis
              dataKey="month"
              stroke="#6a6157"
              style={{ fontSize: "0.75rem" }}
              interval={Math.floor(monthlyData.length / 12)}
            />
            <YAxis
              stroke="#6a6157"
              style={{ fontSize: "0.85rem" }}
              tickFormatter={(value) => `${value}%`}
            />
            <Tooltip
              contentStyle={{
                background: "white",
                border: "1px solid #e0d7cc",
                borderRadius: "8px",
                padding: "12px",
              }}
              content={({ active, payload }) => {
                if (!active || !payload || !payload.length) return null;
                const data = payload[0]?.payload as MonthlyData;
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
                    <div style={{ fontWeight: 600, marginBottom: "8px" }}>{data.month}</div>
                    <div
                      style={{
                        color: data.return_pct >= 0 ? "var(--accent)" : "var(--danger)",
                      }}
                    >
                      Return: {data.return_pct >= 0 ? "+" : ""}
                      {data.return_pct}%
                    </div>
                    <div style={{ color: "var(--muted)" }}>
                      P&L: $
                      {data.pnl.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </div>
                    <div style={{ color: "var(--muted)" }}>Trades: {data.tradeCount}</div>
                  </div>
                );
              }}
            />
            <Bar dataKey="return_pct" radius={[4, 4, 0, 0]}>
              {monthlyData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.return_pct >= 0 ? "var(--accent)" : "var(--danger)"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
