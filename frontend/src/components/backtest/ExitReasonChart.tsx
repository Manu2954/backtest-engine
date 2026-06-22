import { useMemo } from "react";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { TradeLog } from "../../types";

interface ExitReasonChartProps {
  trades: TradeLog[];
}

interface ExitReasonData {
  name: string;
  value: number;
  pnl: number;
  color: string;
}

const EXIT_REASON_COLORS: Record<string, string> = {
  take_profit: "#1b7f6b", // green - accent
  signal: "#3182ce", // blue
  stop_loss: "#b42318", // red - danger
  dynamic_stop: "#e67e22", // orange
  liquidation: "#8e44ad", // purple
  force_close: "#6a6157", // muted
  exit_rule: "#2ecc71", // light green
  unknown: "#999999", // gray
};

const EXIT_REASON_LABELS: Record<string, string> = {
  take_profit: "Take Profit",
  signal: "Exit Signal",
  stop_loss: "Stop Loss",
  dynamic_stop: "Dynamic Stop",
  liquidation: "Liquidation",
  force_close: "Force Close",
  exit_rule: "Exit Rule",
  unknown: "Unknown",
};

function normalizeExitReason(reason: string | undefined): string {
  if (!reason) return "unknown";
  const lower = reason.toLowerCase();
  if (lower.includes("take_profit") || lower.includes("tp")) return "take_profit";
  if (lower.includes("stop_loss") || lower.includes("sl")) return "stop_loss";
  if (lower.includes("dynamic_stop") || lower.includes("trailing")) return "dynamic_stop";
  if (lower.includes("liquidation")) return "liquidation";
  if (lower.includes("force") || lower.includes("close")) return "force_close";
  if (lower.includes("signal") || lower.includes("exit")) return "signal";
  // Check for custom exit rules (e.g., "atr_exit", "rsi_exit")
  if (lower.includes("_exit") || lower.includes("rule")) return "exit_rule";
  return "unknown";
}

export default function ExitReasonChart({ trades }: ExitReasonChartProps) {
  const exitReasonData = useMemo((): ExitReasonData[] => {
    if (!trades.length) return [];

    // Group trades by exit reason
    const byReason: Record<string, { count: number; pnl: number }> = {};

    for (const trade of trades) {
      const normalizedReason = normalizeExitReason(trade.exit_reason);

      if (!byReason[normalizedReason]) {
        byReason[normalizedReason] = { count: 0, pnl: 0 };
      }
      byReason[normalizedReason].count += 1;
      byReason[normalizedReason].pnl += trade.pnl;
    }

    return Object.entries(byReason)
      .map(([reason, data]) => ({
        name: EXIT_REASON_LABELS[reason] || reason,
        value: data.count,
        pnl: Number(data.pnl.toFixed(2)),
        color: EXIT_REASON_COLORS[reason] || EXIT_REASON_COLORS.unknown,
      }))
      .sort((a, b) => b.value - a.value);
  }, [trades]);

  if (exitReasonData.length === 0) {
    return (
      <div className="card">
        <h2>Exit Reasons</h2>
        <p className="notice">No exit data available.</p>
      </div>
    );
  }

  const totalTrades = exitReasonData.reduce((sum, d) => sum + d.value, 0);

  return (
    <div className="card">
      <h2>Exit Reasons</h2>

      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "24px" }}>
        {/* Pie Chart */}
        <div style={{ flex: "1", minWidth: "200px", height: 220 }}>
          <ResponsiveContainer>
            <PieChart>
              <Pie
                data={exitReasonData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                dataKey="value"
                paddingAngle={2}
                label={({ percent }) =>
                  percent > 0.05 ? `${(percent * 100).toFixed(0)}%` : ""
                }
                labelLine={false}
              >
                {exitReasonData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "white",
                  border: "1px solid #e0d7cc",
                  borderRadius: "8px",
                  padding: "12px",
                }}
                content={({ active, payload }) => {
                  if (!active || !payload || !payload.length) return null;
                  const data = payload[0]?.payload as ExitReasonData;
                  const percent = ((data.value / totalTrades) * 100).toFixed(1);
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
                      <div style={{ fontWeight: 600, marginBottom: "8px", color: data.color }}>
                        {data.name}
                      </div>
                      <div>Trades: {data.value} ({percent}%)</div>
                      <div style={{ color: data.pnl >= 0 ? "var(--accent)" : "var(--danger)" }}>
                        P&L: $
                        {data.pnl.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </div>
                    </div>
                  );
                }}
              />
              <Legend
                layout="vertical"
                align="right"
                verticalAlign="middle"
                wrapperStyle={{ fontSize: "0.8rem" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Summary Table */}
        <div style={{ flex: "1", minWidth: "250px" }}>
          <table className="table" style={{ fontSize: "0.85rem" }}>
            <thead>
              <tr>
                <th>Reason</th>
                <th style={{ textAlign: "right" }}>Count</th>
                <th style={{ textAlign: "right" }}>P&L</th>
              </tr>
            </thead>
            <tbody>
              {exitReasonData.map((row) => (
                <tr key={row.name}>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        width: "10px",
                        height: "10px",
                        borderRadius: "50%",
                        background: row.color,
                        marginRight: "8px",
                      }}
                    />
                    {row.name}
                  </td>
                  <td style={{ textAlign: "right" }}>{row.value}</td>
                  <td
                    style={{
                      textAlign: "right",
                      color: row.pnl >= 0 ? "var(--accent)" : "var(--danger)",
                      fontWeight: 600,
                    }}
                  >
                    ${row.pnl.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
