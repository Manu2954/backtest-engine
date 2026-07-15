import type { WalkForwardReport, WalkForwardWindow } from "../../types";

const COLORS = {
  robust: 'hsl(var(--profit))',
  moderate: 'hsl(var(--warning))',
  fragile: 'hsl(var(--loss))',
  muted: 'hsl(var(--muted))',
  mutedForeground: 'hsl(var(--muted-foreground))',
};

interface WalkForwardResultsProps {
  report: WalkForwardReport;
}

type WindowWithReturn = WalkForwardWindow & { returnValue: number };

function getLevelColor(level: string): string {
  switch (level) {
    case "ROBUST":
      return COLORS.robust;
    case "MODERATE":
      return COLORS.moderate;
    case "FRAGILE":
      return COLORS.fragile;
    default:
      return COLORS.muted;
  }
}

export default function WalkForwardResults({ report }: WalkForwardResultsProps) {
  const windows = report.windows || [];
  const summary = report.summary;
  const consistencyMetrics = report.consistency_metrics;
  const assessment = report.assessment;

  // Handle both API response shapes
  const consistencyScore = summary?.consistency_score ?? consistencyMetrics?.consistency_score ?? 0;
  const profitableWindows = summary?.profitable_windows ?? consistencyMetrics?.profitable_windows ?? 0;
  const totalWindows = summary?.total_windows ?? windows.length;
  const scorePercent = Math.min(100, Math.max(0, consistencyScore * 100));

  // Find best and worst windows
  const windowsWithReturns: WindowWithReturn[] = windows.map((w: WalkForwardWindow) => ({
    ...w,
    returnValue: w.total_return ?? w.total_return_pct ?? 0,
  }));
  const sortedByReturn = [...windowsWithReturns].sort((a, b) => b.returnValue - a.returnValue);
  const bestWindow = sortedByReturn[0];
  const worstWindow = sortedByReturn[sortedByReturn.length - 1];

  return (
    <div className="fade-in">
      {/* Score Card */}
      <div className="card" style={{ marginBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <div style={{ flex: 1 }}>
            <h3 style={{ marginBottom: "8px" }}>Consistency Score</h3>
            <div
              style={{
                fontSize: "2.5rem",
                fontWeight: 700,
                color: getLevelColor(assessment.level || ""),
              }}
            >
              {(consistencyScore * 100).toFixed(0)}%
            </div>
            {assessment.level && (
              <div
                className="tag"
                style={{
                  marginTop: "8px",
                  background: getLevelColor(assessment.level),
                  color: "white",
                }}
              >
                {assessment.level}
              </div>
            )}
          </div>
          <div style={{ flex: 2 }}>
            <div
              style={{
                height: "12px",
                background: COLORS.muted,
                borderRadius: "6px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${scorePercent}%`,
                  height: "100%",
                  background: getLevelColor(assessment.level || ""),
                  transition: "width 0.5s ease",
                }}
              />
            </div>
            {assessment.recommendation && (
              <p style={{ marginTop: "12px", color: "var(--muted)", fontSize: "0.9rem" }}>
                {assessment.recommendation}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="card" style={{ marginBottom: "16px" }}>
        <h4>Summary Statistics</h4>
        <div className="metrics" style={{ marginTop: "12px" }}>
          <div className="metric">
            <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
              Profitable Windows
            </div>
            <div style={{ fontSize: "1.2rem", fontWeight: 600 }}>
              {profitableWindows} / {totalWindows}
            </div>
          </div>
          {summary?.avg_return !== undefined && (
            <div className="metric">
              <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>Average Return</div>
              <div
                style={{
                  fontSize: "1.2rem",
                  fontWeight: 600,
                  color: summary.avg_return >= 0 ? COLORS.robust : COLORS.fragile,
                }}
              >
                {(summary.avg_return * 100).toFixed(2)}%
              </div>
            </div>
          )}
          {summary?.avg_sharpe !== undefined && (
            <div className="metric">
              <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>Average Sharpe</div>
              <div style={{ fontSize: "1.2rem", fontWeight: 600 }}>
                {summary.avg_sharpe.toFixed(2)}
              </div>
            </div>
          )}
          {summary?.avg_trades !== undefined && (
            <div className="metric">
              <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>Average Trades</div>
              <div style={{ fontSize: "1.2rem", fontWeight: 600 }}>
                {summary.avg_trades.toFixed(0)}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Assessment Flags */}
      {assessment.flags?.length > 0 && (
        <div className="notice" style={{ marginBottom: "16px" }}>
          <strong>Analysis Notes:</strong>
          <ul style={{ margin: "8px 0 0 20px", padding: 0 }}>
            {assessment.flags.map((flag: string, i: number) => (
              <li key={i}>{flag}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Timeline Visualization */}
      {windows.length > 0 && (
        <div className="card" style={{ marginBottom: "16px" }}>
          <h4>Window Timeline</h4>
          <div
            style={{
              display: "flex",
              marginTop: "16px",
              gap: "2px",
              height: "80px",
              alignItems: "flex-end",
            }}
          >
            {windowsWithReturns.map((w: WindowWithReturn) => {
              const maxReturn = Math.max(
                ...windowsWithReturns.map((x: WindowWithReturn) => Math.abs(x.returnValue)),
                0.01
              );
              const height = Math.max(10, (Math.abs(w.returnValue) / maxReturn) * 100);
              const isProfitable = w.returnValue >= 0;
              const windowIndex = w.window_index ?? w.window_id ?? 0;
              const isBest = bestWindow && windowIndex === (bestWindow.window_index ?? bestWindow.window_id);
              const isWorst = worstWindow && windowIndex === (worstWindow.window_index ?? worstWindow.window_id);

              return (
                <div
                  key={windowIndex}
                  style={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <div
                    style={{
                      width: "100%",
                      height: `${height}%`,
                      minHeight: "10px",
                      background: isProfitable ? COLORS.robust : COLORS.fragile,
                      borderRadius: "4px 4px 0 0",
                      border: isBest
                        ? `2px solid ${COLORS.robust}`
                        : isWorst
                          ? `2px solid ${COLORS.fragile}`
                          : "none",
                      position: "relative",
                    }}
                    title={`Window ${windowIndex + 1}: ${(w.returnValue * 100).toFixed(2)}%`}
                  >
                    {(isBest || isWorst) && (
                      <div
                        style={{
                          position: "absolute",
                          top: "-20px",
                          left: "50%",
                          transform: "translateX(-50%)",
                          fontSize: "0.7rem",
                          fontWeight: 600,
                          color: isBest ? COLORS.robust : COLORS.fragile,
                        }}
                      >
                        {isBest ? "BEST" : "WORST"}
                      </div>
                    )}
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--muted)" }}>
                    W{windowIndex + 1}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Window Details Table */}
      {windows.length > 0 && (
        <div className="card">
          <h4>Window Details</h4>
          <table className="table" style={{ marginTop: "12px" }}>
            <thead>
              <tr>
                <th>Window</th>
                <th>Period</th>
                <th>Return</th>
                <th>Sharpe</th>
                <th>Max DD</th>
                <th>Trades</th>
                <th>Win Rate</th>
              </tr>
            </thead>
            <tbody>
              {windowsWithReturns.map((w: WindowWithReturn) => {
                const windowIndex = w.window_index ?? w.window_id ?? 0;
                return (
                  <tr key={windowIndex}>
                    <td>
                      <strong>W{windowIndex + 1}</strong>
                    </td>
                    <td style={{ fontSize: "0.85rem" }}>
                      {w.start_date?.split("T")[0] || "N/A"} to {w.end_date?.split("T")[0] || "N/A"}
                    </td>
                    <td
                      style={{
                        color: w.returnValue >= 0 ? COLORS.robust : COLORS.fragile,
                        fontWeight: 600,
                      }}
                    >
                      {(w.returnValue * 100).toFixed(2)}%
                    </td>
                    <td>{(w.sharpe_ratio || 0).toFixed(2)}</td>
                    <td style={{ color: COLORS.fragile }}>
                      -{(Math.abs(w.max_drawdown ?? w.max_drawdown_pct ?? 0) * 100).toFixed(2)}%
                    </td>
                    <td>{w.total_trades || 0}</td>
                    <td>{((w.win_rate || 0) * 100).toFixed(1)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
