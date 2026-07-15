/* eslint-disable @typescript-eslint/no-explicit-any */

interface RegimeDetectionResultsProps {
  report: Record<string, any>;
}

const COLORS = {
  robust: 'hsl(var(--profit))',
  moderate: 'hsl(var(--warning))',
  fragile: 'hsl(var(--loss))',
  muted: 'hsl(var(--muted))',
  mutedForeground: 'hsl(var(--muted-foreground))',
  border: 'hsl(var(--border))',
  profitBg: 'hsl(var(--profit) / 0.15)',
  lossBg: 'hsl(var(--loss) / 0.15)',
};

const REGIME_COLORS: Record<string, string> = {
  BULL: COLORS.robust,
  BEAR: COLORS.fragile,
  CHOPPY: COLORS.moderate,
  RANGING: COLORS.mutedForeground,
  HIGH_VOL: COLORS.fragile,
  LOW_VOL: COLORS.robust,
  TRANSITION: COLORS.moderate,
};

function getRegimeColor(regime: string): string {
  return REGIME_COLORS[regime] || COLORS.mutedForeground;
}

function getLevelColor(level: string): string {
  switch (level) {
    case "INDEPENDENT":
    case "ROBUST":
      return COLORS.robust;
    case "MODERATE":
      return COLORS.moderate;
    case "DEPENDENT":
    case "FRAGILE":
      return COLORS.fragile;
    default:
      return COLORS.muted;
  }
}

export default function RegimeDetectionResults({ report }: RegimeDetectionResultsProps) {
  const regimes = report.regimes || [];
  const regimePerformance = report.regime_performance || [];
  const summary = report.summary || {};
  const assessment = report.assessment || {};
  const regimeDependency = report.regime_dependency || {};

  const dependencyScore = summary.dependency_score ?? regimeDependency.cv_return ?? 0;
  const scorePercent = Math.min(100, Math.max(0, (1 - dependencyScore) * 100));

  // Calculate total bars for timeline proportions
  const totalBars = regimes.reduce((sum: number, r: any) => sum + (r.bar_count || 0), 0);

  return (
    <div className="fade-in">
      {/* Score Card */}
      <div className="card" style={{ marginBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <div style={{ flex: 1 }}>
            <h3 style={{ marginBottom: "8px" }}>Regime Independence</h3>
            <div
              style={{
                fontSize: "2.5rem",
                fontWeight: 700,
                color: getLevelColor(assessment.level || regimeDependency.dependency_level || ""),
              }}
            >
              {((1 - dependencyScore) * 100).toFixed(0)}%
            </div>
            {(assessment.level || regimeDependency.dependency_level) && (
              <div
                className="tag"
                style={{
                  marginTop: "8px",
                  background: getLevelColor(assessment.level || regimeDependency.dependency_level),
                  color: "white",
                }}
              >
                {assessment.level || regimeDependency.dependency_level}
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
                  background: getLevelColor(assessment.level || regimeDependency.dependency_level || ""),
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
      {(summary.total_regimes || summary.best_regime || regimePerformance.length > 0) && (
        <div className="card" style={{ marginBottom: "16px" }}>
          <h4>Regime Summary</h4>
          <div className="metrics" style={{ marginTop: "12px" }}>
            <div className="metric">
              <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>Total Regimes</div>
              <div style={{ fontSize: "1.2rem", fontWeight: 600 }}>
                {summary.total_regimes || regimes.length || regimePerformance.length}
              </div>
            </div>
            {summary.best_regime && (
              <div className="metric">
                <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>Best Regime</div>
                <div
                  style={{
                    fontSize: "1.2rem",
                    fontWeight: 600,
                    color: getRegimeColor(summary.best_regime),
                  }}
                >
                  {summary.best_regime}
                </div>
              </div>
            )}
            {summary.worst_regime && (
              <div className="metric">
                <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>Worst Regime</div>
                <div
                  style={{
                    fontSize: "1.2rem",
                    fontWeight: 600,
                    color: getRegimeColor(summary.worst_regime),
                  }}
                >
                  {summary.worst_regime}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

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
      {regimes.length > 0 && totalBars > 0 && (
        <div className="card" style={{ marginBottom: "16px" }}>
          <h4>Regime Timeline</h4>
          <div
            style={{
              display: "flex",
              marginTop: "16px",
              height: "40px",
              borderRadius: "8px",
              overflow: "hidden",
            }}
          >
            {regimes.map((r: any, i: number) => {
              const widthPercent = ((r.bar_count || 0) / totalBars) * 100;
              return (
                <div
                  key={i}
                  style={{
                    width: `${widthPercent}%`,
                    minWidth: "4px",
                    height: "100%",
                    background: getRegimeColor(r.regime),
                    borderRight: i < regimes.length - 1 ? `1px solid ${COLORS.border}` : "none",
                  }}
                  title={`${r.regime}: ${r.bar_count || 0} bars`}
                />
              );
            })}
          </div>
          {regimes[0]?.start_date && (
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: "8px",
                fontSize: "0.75rem",
                color: "var(--muted)",
              }}
            >
              <span>{regimes[0]?.start_date?.split("T")[0] || ""}</span>
              <span>{regimes[regimes.length - 1]?.end_date?.split("T")[0] || ""}</span>
            </div>
          )}
        </div>
      )}

      {/* Performance by Regime */}
      {regimePerformance.length > 0 && (
        <div className="card">
          <h4>Performance by Regime</h4>
          <table className="table" style={{ marginTop: "12px" }}>
            <thead>
              <tr>
                <th>Regime</th>
                <th>Trades</th>
                <th>Win Rate</th>
                <th>Avg Return</th>
                <th>Sharpe</th>
              </tr>
            </thead>
            <tbody>
              {regimePerformance.map((rp: any) => (
                <tr key={rp.regime}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <div
                        style={{
                          width: "12px",
                          height: "12px",
                          borderRadius: "3px",
                          background: getRegimeColor(rp.regime),
                        }}
                      />
                      <strong>{rp.regime}</strong>
                      {rp.regime === summary.best_regime && (
                        <span className="tag" style={{ background: COLORS.profitBg, color: COLORS.robust }}>
                          BEST
                        </span>
                      )}
                      {rp.regime === summary.worst_regime && (
                        <span className="tag" style={{ background: COLORS.lossBg, color: COLORS.fragile }}>
                          WORST
                        </span>
                      )}
                    </div>
                  </td>
                  <td>{rp.total_trades ?? rp.trade_count ?? 0}</td>
                  <td>{((rp.win_rate || 0) * 100).toFixed(1)}%</td>
                  <td
                    style={{
                      color: (rp.avg_return ?? rp.avg_return_pct ?? 0) >= 0 ? COLORS.robust : COLORS.fragile,
                      fontWeight: 600,
                    }}
                  >
                    {((rp.avg_return ?? rp.avg_return_pct ?? 0) * 100).toFixed(2)}%
                  </td>
                  <td>{(rp.sharpe_ratio || 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Fallback: Show regimes table if regime_performance is not available */}
      {regimePerformance.length === 0 && regimes.length > 0 && (
        <div className="card">
          <h4>Regime Statistics</h4>
          <table className="table" style={{ marginTop: "12px" }}>
            <thead>
              <tr>
                <th>Regime</th>
                <th>Bar Count</th>
                <th>Trades</th>
                <th>Win Rate</th>
                <th>Avg Return</th>
              </tr>
            </thead>
            <tbody>
              {regimes.map((r: any, i: number) => (
                <tr key={i}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <div
                        style={{
                          width: "12px",
                          height: "12px",
                          borderRadius: "3px",
                          background: getRegimeColor(r.regime),
                        }}
                      />
                      <strong>{r.regime}</strong>
                    </div>
                  </td>
                  <td>{r.bar_count || 0}</td>
                  <td>{r.trade_count || 0}</td>
                  <td>{((r.win_rate || 0) * 100).toFixed(1)}%</td>
                  <td
                    style={{
                      color: (r.avg_return_pct || 0) >= 0 ? COLORS.robust : COLORS.fragile,
                      fontWeight: 600,
                    }}
                  >
                    {((r.avg_return_pct || 0) * 100).toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
