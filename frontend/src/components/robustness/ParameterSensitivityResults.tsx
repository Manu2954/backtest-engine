import type { ParameterSensitivityReport } from "../../types";

interface ParameterSensitivityResultsProps {
  report: ParameterSensitivityReport;
}

// Theme-aware colors using CSS variables
const COLORS = {
  robust: 'hsl(var(--profit))',
  moderate: 'hsl(var(--warning))',
  fragile: 'hsl(var(--loss))',
  muted: 'hsl(var(--muted))',
  mutedForeground: 'hsl(var(--muted-foreground))',
  profitBg: 'hsl(var(--profit) / 0.15)',
  lossBg: 'hsl(var(--loss) / 0.15)',
};

function getLevelColor(level: string): string {
  switch (level) {
    case "ROBUST":
      return COLORS.robust;
    case "MODERATE":
      return COLORS.moderate;
    case "FRAGILE":
      return COLORS.fragile;
    default:
      return COLORS.mutedForeground;
  }
}

function formatMetricName(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMetricValue(name: string, value: unknown): string {
  // Handle non-numeric values
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  if (typeof value !== 'number' || isNaN(value)) return String(value);

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
  // Handle various API response formats with safe fallbacks
  const reportAny = report as unknown as Record<string, unknown>;
  const baseline = (reportAny?.baseline ?? {}) as Record<string, unknown>;
  const variants = (reportAny?.variants ?? []) as Array<{
    indicator_alias: string;
    param_name: string;
    original_value: number;
    variant_value: number;
    direction: string;
    deltas: Record<string, number>;
  }>;

  const stabilityMetrics = reportAny?.stability_metrics as Record<string, unknown> | undefined;
  const stabilityScore = (stabilityMetrics?.stability_score ?? stabilityMetrics?.overall_stability_score ?? 0) as number;
  const metricCvs = (stabilityMetrics?.metric_cvs ?? stabilityMetrics?.per_metric_cv ?? {}) as Record<string, number>;

  const assessment = reportAny?.assessment as Record<string, unknown> | undefined;
  const level = ((assessment?.level ?? assessment?.robustness_level ?? 'UNKNOWN') as string);
  const flags = (assessment?.flags ?? assessment?.risk_flags ?? []) as string[];
  const recommendation = (assessment?.recommendation ?? '') as string;

  const scorePercent = Math.min(100, Math.max(0, stabilityScore * 100));

  // Group variants by indicator
  const variantsByIndicator = variants.reduce(
    (acc, v) => {
      const alias = v.indicator_alias || 'unknown';
      if (!acc[alias]) {
        acc[alias] = [];
      }
      acc[alias].push(v);
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
                color: getLevelColor(level),
              }}
            >
              {(stabilityScore * 100).toFixed(0)}%
            </div>
            <div
              className="tag"
              style={{
                marginTop: "8px",
                background: getLevelColor(level),
                color: "white",
              }}
            >
              {level}
            </div>
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
                  background: getLevelColor(level),
                  transition: "width 0.5s ease",
                }}
              />
            </div>
            <p style={{ marginTop: "12px", color: "var(--muted)", fontSize: "0.9rem" }}>
              {recommendation}
            </p>
          </div>
        </div>
      </div>

      {/* Assessment Flags */}
      {flags.length > 0 && (
        <div className="notice" style={{ marginBottom: "16px" }}>
          <strong>Analysis Notes:</strong>
          <ul style={{ margin: "8px 0 0 20px", padding: 0 }}>
            {flags.map((flag, i) => (
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
          {Object.entries(metricCvs).map(([metric, cv]) => {
            const cvValue = typeof cv === 'number' ? cv : 0;
            const cvPercent = Math.min(100, cvValue * 100);
            const isHigh = cvValue > 0.3;
            return (
              <div key={metric} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ width: "140px", fontSize: "0.85rem" }}>
                  {formatMetricName(metric)}
                </div>
                <div
                  style={{
                    flex: 1,
                    height: "20px",
                    background: COLORS.muted,
                    borderRadius: "4px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${cvPercent}%`,
                      height: "100%",
                      background: isHigh ? COLORS.moderate : COLORS.robust,
                    }}
                  />
                </div>
                <div style={{ width: "50px", fontSize: "0.85rem", textAlign: "right" }}>
                  {(cvValue * 100).toFixed(1)}%
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
                  const deltas = v.deltas || {};
                  const returnDelta = deltas.total_return ?? deltas.total_pnl_pct ?? deltas.total_return_pct ?? 0;
                  const sharpeDelta = deltas.sharpe_ratio ?? deltas.sharpe ?? 0;
                  return (
                    <tr key={i}>
                      <td>
                        {v.param_name || 'unknown'}{" "}
                        <span style={{ color: v.direction === "up" ? COLORS.robust : COLORS.fragile }}>
                          ({v.direction === "up" ? "+" : "-"}20%)
                        </span>
                      </td>
                      <td>{v.original_value ?? '—'}</td>
                      <td>{v.variant_value ?? '—'}</td>
                      <td
                        style={{
                          color: returnDelta >= 0 ? COLORS.robust : COLORS.fragile,
                        }}
                      >
                        {returnDelta >= 0 ? "+" : ""}
                        {typeof returnDelta === 'number' ? (returnDelta * 100).toFixed(2) : '0.00'}%
                      </td>
                      <td
                        style={{
                          color: sharpeDelta >= 0 ? COLORS.robust : COLORS.fragile,
                        }}
                      >
                        {sharpeDelta >= 0 ? "+" : ""}
                        {typeof sharpeDelta === 'number' ? sharpeDelta.toFixed(2) : '0.00'}
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
