/* eslint-disable @typescript-eslint/no-explicit-any */

interface FeatureConditioningResultsProps {
  report: Record<string, any>;
}

function getLevelColor(level: string): string {
  switch (level) {
    case "PREDICTABLE":
    case "ROBUST":
      return "#1b7f6b";
    case "MODERATE":
      return "#d59f0f";
    case "RANDOM":
    case "FRAGILE":
      return "#b42318";
    default:
      return "var(--muted)";
  }
}

function formatFeatureName(name: string): string {
  return (name || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function FeatureConditioningResults({
  report,
}: FeatureConditioningResultsProps) {
  const features = report.features || [];
  const winningConditions = report.winning_conditions || [];
  const losingConditions = report.losing_conditions || [];
  const summary = report.summary || {};
  const assessment = report.assessment || {};

  const sortedFeatures = features.length > 0
    ? [...features].sort((a: any, b: any) => (b.importance || 0) - (a.importance || 0))
    : [];

  return (
    <div className="fade-in">
      {/* Assessment Card */}
      <div className="card" style={{ marginBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <div style={{ flex: 1 }}>
            <h3 style={{ marginBottom: "8px" }}>Condition Predictability</h3>
            {assessment.level && (
              <div
                style={{
                  fontSize: "1.5rem",
                  fontWeight: 700,
                  color: getLevelColor(assessment.level),
                }}
              >
                {assessment.level}
              </div>
            )}
            {summary.most_important_feature && (
              <div
                className="tag"
                style={{
                  marginTop: "8px",
                  background: getLevelColor(assessment.level || ""),
                  color: "white",
                }}
              >
                Most Important: {formatFeatureName(summary.most_important_feature)}
              </div>
            )}
          </div>
          <div style={{ flex: 2 }}>
            {assessment.recommendation && (
              <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
                {assessment.recommendation}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      {(summary.total_features || summary.total_trades_analyzed || summary.overall_win_rate) && (
        <div className="card" style={{ marginBottom: "16px" }}>
          <h4>Analysis Summary</h4>
          <div className="metrics" style={{ marginTop: "12px" }}>
            {summary.total_features !== undefined && (
              <div className="metric">
                <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                  Features Analyzed
                </div>
                <div style={{ fontSize: "1.2rem", fontWeight: 600 }}>
                  {summary.total_features}
                </div>
              </div>
            )}
            {summary.total_trades_analyzed !== undefined && (
              <div className="metric">
                <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                  Trades Analyzed
                </div>
                <div style={{ fontSize: "1.2rem", fontWeight: 600 }}>
                  {summary.total_trades_analyzed}
                </div>
              </div>
            )}
            {summary.overall_win_rate !== undefined && (
              <div className="metric">
                <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                  Overall Win Rate
                </div>
                <div style={{ fontSize: "1.2rem", fontWeight: 600 }}>
                  {((summary.overall_win_rate || 0) * 100).toFixed(1)}%
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

      {/* Winning and Losing Conditions */}
      {(winningConditions.length > 0 || losingConditions.length > 0) && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
          <div className="card">
            <h4 style={{ color: "#1b7f6b" }}>Winning Conditions</h4>
            {winningConditions.length === 0 ? (
              <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
                No significant winning conditions found.
              </p>
            ) : (
              <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
                {winningConditions.slice(0, 5).map((cond: any, i: number) => (
                  <div
                    key={i}
                    style={{
                      padding: "12px",
                      background: "#e6f4f1",
                      borderRadius: "8px",
                      borderLeft: "4px solid #1b7f6b",
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>
                      {formatFeatureName(cond.feature)} {cond.quartile && `- ${cond.quartile}`}
                    </div>
                    <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                      {cond.condition && <span>{cond.condition} - </span>}
                      Win Rate: <strong style={{ color: "#1b7f6b" }}>
                        {((cond.win_rate || 0) * 100).toFixed(1)}%
                      </strong>
                      {cond.trade_count && <span> ({cond.trade_count} trades)</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <h4 style={{ color: "#b42318" }}>Losing Conditions</h4>
            {losingConditions.length === 0 ? (
              <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
                No significant losing conditions found.
              </p>
            ) : (
              <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
                {losingConditions.slice(0, 5).map((cond: any, i: number) => (
                  <div
                    key={i}
                    style={{
                      padding: "12px",
                      background: "#fde8e7",
                      borderRadius: "8px",
                      borderLeft: "4px solid #b42318",
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>
                      {formatFeatureName(cond.feature)} {cond.quartile && `- ${cond.quartile}`}
                    </div>
                    <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                      {cond.condition && <span>{cond.condition} - </span>}
                      Win Rate: <strong style={{ color: "#b42318" }}>
                        {((cond.win_rate || 0) * 100).toFixed(1)}%
                      </strong>
                      {cond.trade_count && <span> ({cond.trade_count} trades)</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Feature Importance Ranking */}
      {sortedFeatures.length > 0 && (
        <div className="card">
          <h4>Feature Importance</h4>
          <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "12px" }}>
            Higher importance indicates more variation in win rates across quartiles.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {sortedFeatures.map((feature: any) => {
              const importancePercent = (feature.importance || 0) * 100;
              return (
                <div
                  key={feature.feature_name}
                  style={{ display: "flex", alignItems: "center", gap: "12px" }}
                >
                  <div style={{ width: "140px", fontSize: "0.85rem", fontWeight: 600 }}>
                    {formatFeatureName(feature.feature_name)}
                  </div>
                  <div
                    style={{
                      flex: 1,
                      height: "20px",
                      background: "#f0f0f0",
                      borderRadius: "4px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${importancePercent}%`,
                        height: "100%",
                        background:
                          feature.feature_name === summary.most_important_feature
                            ? "#1b7f6b"
                            : "#6a6157",
                      }}
                    />
                  </div>
                  <div style={{ width: "50px", fontSize: "0.85rem", textAlign: "right" }}>
                    {importancePercent.toFixed(0)}%
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
