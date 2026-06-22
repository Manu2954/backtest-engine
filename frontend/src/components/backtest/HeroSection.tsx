import type { BacktestOut } from "../../types";

interface HeroSectionProps {
  run: BacktestOut;
}

function formatCurrency(value: number): string {
  return `$${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatPercent(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export default function HeroSection({ run }: HeroSectionProps) {
  const report = run.report;
  if (!report) return null;

  const totalReturn = report.total_return_pct || 0;
  const benchmarkReturn = report.benchmark_return_pct;
  const finalCapital = report.final_capital || run.initial_capital;
  const initialCapital = run.initial_capital;
  const capitalDelta = finalCapital - initialCapital;

  const hasBenchmark = benchmarkReturn !== undefined && benchmarkReturn !== null;
  const outperformance = hasBenchmark ? totalReturn - benchmarkReturn : 0;
  const didOutperform = outperformance > 0;

  // Normalize bars to percentage widths (max 100%)
  const maxReturn = hasBenchmark
    ? Math.max(Math.abs(totalReturn), Math.abs(benchmarkReturn))
    : Math.abs(totalReturn);
  const strategyBarWidth = maxReturn > 0 ? (Math.abs(totalReturn) / maxReturn) * 100 : 0;
  const benchmarkBarWidth =
    hasBenchmark && maxReturn > 0 ? (Math.abs(benchmarkReturn) / maxReturn) * 100 : 0;

  return (
    <div className="card hero-section" style={{ textAlign: "center", padding: "32px" }}>
      {/* Total Return - Large Display */}
      <div
        style={{
          fontSize: "48px",
          fontWeight: 700,
          color: totalReturn >= 0 ? "var(--accent)" : "var(--danger)",
          lineHeight: 1.1,
          fontFamily: '"Fraunces", serif',
        }}
      >
        {formatPercent(totalReturn)}
      </div>
      <div
        style={{
          fontSize: "0.95rem",
          color: "var(--muted)",
          marginTop: "4px",
          marginBottom: "24px",
        }}
      >
        Total Return
      </div>

      {/* Benchmark Comparison Bars */}
      {hasBenchmark && (
        <div style={{ marginBottom: "20px" }}>
          {/* Strategy Bar */}
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
            <div style={{ width: "80px", textAlign: "right", fontSize: "0.85rem", fontWeight: 600 }}>
              Strategy
            </div>
            <div
              style={{
                flex: 1,
                height: "24px",
                background: "#f0f0f0",
                borderRadius: "6px",
                overflow: "hidden",
                position: "relative",
              }}
            >
              <div
                style={{
                  width: `${strategyBarWidth}%`,
                  height: "100%",
                  background: totalReturn >= 0 ? "var(--accent)" : "var(--danger)",
                  borderRadius: "6px",
                  transition: "width 0.5s ease",
                }}
              />
            </div>
            <div
              style={{
                width: "70px",
                fontSize: "0.85rem",
                fontWeight: 600,
                color: totalReturn >= 0 ? "var(--accent)" : "var(--danger)",
              }}
            >
              {formatPercent(totalReturn)}
            </div>
          </div>

          {/* Benchmark Bar */}
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ width: "80px", textAlign: "right", fontSize: "0.85rem", fontWeight: 600 }}>
              SPY
            </div>
            <div
              style={{
                flex: 1,
                height: "24px",
                background: "#f0f0f0",
                borderRadius: "6px",
                overflow: "hidden",
                position: "relative",
              }}
            >
              <div
                style={{
                  width: `${benchmarkBarWidth}%`,
                  height: "100%",
                  background: benchmarkReturn >= 0 ? "var(--accent-2)" : "var(--danger)",
                  borderRadius: "6px",
                  transition: "width 0.5s ease",
                }}
              />
            </div>
            <div
              style={{
                width: "70px",
                fontSize: "0.85rem",
                fontWeight: 600,
                color: benchmarkReturn >= 0 ? "var(--accent-2)" : "var(--danger)",
              }}
            >
              {formatPercent(benchmarkReturn)}
            </div>
          </div>

          {/* Outperformance Badge */}
          <div
            style={{
              marginTop: "16px",
              display: "inline-block",
              padding: "6px 14px",
              borderRadius: "999px",
              fontSize: "0.85rem",
              fontWeight: 600,
              background: didOutperform ? "#e8f5f3" : "#ffe8e6",
              color: didOutperform ? "var(--accent)" : "var(--danger)",
              border: `1px solid ${didOutperform ? "var(--accent)" : "var(--danger)"}`,
            }}
          >
            {didOutperform
              ? `Outperformed by ${outperformance.toFixed(2)}%`
              : `Underperformed by ${Math.abs(outperformance).toFixed(2)}%`}
          </div>
        </div>
      )}

      {/* Final Capital with Delta */}
      <div
        style={{
          marginTop: "20px",
          padding: "16px",
          background: "#faf8f5",
          borderRadius: "12px",
          border: "1px solid var(--line)",
        }}
      >
        <div style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "4px" }}>
          Final Capital
        </div>
        <div style={{ fontSize: "1.8rem", fontWeight: 700 }}>{formatCurrency(finalCapital)}</div>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            marginTop: "4px",
            fontSize: "0.9rem",
            fontWeight: 600,
            color: capitalDelta >= 0 ? "var(--accent)" : "var(--danger)",
          }}
        >
          <span>{capitalDelta >= 0 ? "+" : ""}</span>
          <span>{formatCurrency(Math.abs(capitalDelta))}</span>
          <span style={{ fontSize: "1rem" }}>{capitalDelta >= 0 ? "▲" : "▼"}</span>
        </div>
      </div>
    </div>
  );
}
