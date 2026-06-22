import type { ParameterSensitivityReport } from "../../types";

interface ParameterSensitivityResultsProps {
  report: ParameterSensitivityReport;
}

function getLevelColor(level: string): string {
  switch (level) {
    case "ROBUST":
      return "#1b7f6b";
    case "MODERATE":
      return "#d59f0f";
    case "FRAGILE":
      return "#b42318";
    default:
      return "var(--muted)";
  }
}

function formatMetricName(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMetricValue(name: string, value: number): string {
  if (name.includes("pct") || name.includes("return") || name.includes("rate") || name.includes("drawdown")) {
    return `${(value * 100).toFixed(2)}%`;
  }
  if (name.includes("ratio") || name.includes("factor")) {
    return value.toFixed(2);
  }
  if (name.includes("trades")) {
    return value.toFixed(0);
  }
  return value.toFixed(2);
}

export default function ParameterSensitivityResults({
  report,
}: ParameterSensitivityResultsProps) {
  const { baseline, variants, stability_metrics, assessment } = report;
  const stabilityScore = stability_metrics.stability_score;
  const scorePercent = Math.min(100, Math.max(0, stabilityScore * 100));

  // Group variants by indicator
  const variantsByIndicator = variants.reduce(
    (acc, v) => {
      if (!acc[v.indicator_alias]) {
        acc[v.indicator_alias] = [];
      }
      acc[v.indicator_alias].push(v);
      return acc;
    },
    {} as Record<string, typeof variants>
  );

  return (
    <div className="fade-in">
      {/* Score Card */}
      <div className="card" style={{ marginBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <div style={{ flex: 1 }}>
            <h3 style={{ marginBottom: "8px" }}>Stability Score</h3>
            <div
              style={{
                fontSize: "2.5rem",
                fontWeight: 700,
                color: getLevelColor(assessment.level),
              }}
            >
              {(stabilityScore * 100).toFixed(0)}%
            </div>
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
          </div>
          <div style={{ flex: 2 }}>
            <div
              style={{
                height: "12px",
                background: "#eee",
                borderRadius: "6px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${scorePercent}%`,
                  height: "100%",
                  background: getLevelColor(assessment.level),
                  transition: "width 0.5s ease",
                }}
              />
            </div>
            <p style={{ marginTop: "12px", color: "var(--muted)", fontSize: "0.9rem" }}>
              {assessment.recommendation}
            </p>
          </div>
        </div>
      </div>

      {/* Assessment Flags */}
      {assessment.flags.length > 0 && (
        <div className="notice" style={{ marginBottom: "16px" }}>
          <strong>Analysis Notes:</strong>
          <ul style={{ margin: "8px 0 0 20px", padding: 0 }}>
            {assessment.flags.map((flag, i) => (
              <li key={i}>{flag}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Baseline Metrics */}
      <div className="card" style={{ marginBottom: "16px" }}>
        <h4>Baseline Performance</h4>
        <div className="metrics" style={{ marginTop: "12px" }}>
          {Object.entries(baseline).map(([name, value]) => (
            <div className="metric" key={name}>
              <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                {formatMetricName(name)}
              </div>
              <div style={{ fontSize: "1.2rem", fontWeight: 600 }}>
                {formatMetricValue(name, value as number)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Metric Variation Chart */}
      <div className="card" style={{ marginBottom: "16px" }}>
        <h4>Metric Coefficient of Variation</h4>
        <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "12px" }}>
          Lower CV indicates more stable metrics across parameter variations.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {Object.entries(stability_metrics.metric_cvs).map(([metric, cv]) => {
            const cvPercent = Math.min(100, cv * 100);
            const isHigh = cv > 0.3;
            return (
              <div key={metric} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ width: "140px", fontSize: "0.85rem" }}>
                  {formatMetricName(metric)}
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
                      width: `${cvPercent}%`,
                      height: "100%",
                      background: isHigh ? "#d59f0f" : "#1b7f6b",
                    }}
                  />
                </div>
                <div style={{ width: "50px", fontSize: "0.85rem", textAlign: "right" }}>
                  {(cv * 100).toFixed(1)}%
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Variant Results by Indicator */}
      <div className="card">
        <h4>Parameter Variants</h4>
        {Object.entries(variantsByIndicator).map(([indicator, indicatorVariants]) => (
          <div key={indicator} style={{ marginTop: "16px" }}>
            <h5
              style={{
                fontSize: "0.95rem",
                color: "var(--accent)",
                marginBottom: "8px",
              }}
            >
              {indicator}
            </h5>
            <table className="table">
              <thead>
                <tr>
                  <th>Parameter</th>
                  <th>Original</th>
                  <th>Variant</th>
                  <th>Return Delta</th>
                  <th>Sharpe Delta</th>
                </tr>
              </thead>
              <tbody>
                {indicatorVariants.map((v, i) => {
                  const returnDelta = v.deltas.total_return || v.deltas.total_pnl_pct || 0;
                  const sharpeDelta = v.deltas.sharpe_ratio || 0;
                  return (
                    <tr key={i}>
                      <td>
                        {v.param_name}{" "}
                        <span style={{ color: v.direction === "up" ? "#1b7f6b" : "#b42318" }}>
                          ({v.direction === "up" ? "+" : "-"}20%)
                        </span>
                      </td>
                      <td>{v.original_value}</td>
                      <td>{v.variant_value}</td>
                      <td
                        style={{
                          color: returnDelta >= 0 ? "#1b7f6b" : "#b42318",
                        }}
                      >
                        {returnDelta >= 0 ? "+" : ""}
                        {(returnDelta * 100).toFixed(2)}%
                      </td>
                      <td
                        style={{
                          color: sharpeDelta >= 0 ? "#1b7f6b" : "#b42318",
                        }}
                      >
                        {sharpeDelta >= 0 ? "+" : ""}
                        {sharpeDelta.toFixed(2)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}
