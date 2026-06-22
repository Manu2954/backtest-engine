import type { BacktestOut } from "../../types";

interface QuickStatsProps {
  run: BacktestOut;
}

interface MetricCardProps {
  label: string;
  value: string | number;
  qualitative: string;
  qualitativeColor: string;
  visual?: React.ReactNode;
}

function MetricCard({ label, value, qualitative, qualitativeColor, visual }: MetricCardProps) {
  return (
    <div
      style={{
        flex: "1",
        minWidth: "150px",
        padding: "16px",
        background: "#faf8f5",
        borderRadius: "12px",
        border: "1px solid var(--line)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "8px",
      }}
    >
      {visual && <div style={{ marginBottom: "4px" }}>{visual}</div>}
      <div style={{ fontSize: "1.4rem", fontWeight: 700 }}>{value}</div>
      <div style={{ fontSize: "0.8rem", color: "var(--muted)" }}>{label}</div>
      <div
        style={{
          fontSize: "0.75rem",
          fontWeight: 600,
          padding: "2px 8px",
          borderRadius: "999px",
          background: qualitativeColor,
          color: "#fff",
        }}
      >
        {qualitative}
      </div>
    </div>
  );
}

// Mini donut chart for win rate
function WinRateDonut({ winRate }: { winRate: number }) {
  const radius = 20;
  const strokeWidth = 6;
  const normalizedRadius = radius - strokeWidth / 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (winRate / 100) * circumference;

  return (
    <svg height={radius * 2} width={radius * 2}>
      {/* Background circle */}
      <circle
        stroke="#e0d7cc"
        fill="transparent"
        strokeWidth={strokeWidth}
        r={normalizedRadius}
        cx={radius}
        cy={radius}
      />
      {/* Progress circle */}
      <circle
        stroke={winRate >= 50 ? "var(--accent)" : "var(--danger)"}
        fill="transparent"
        strokeWidth={strokeWidth}
        strokeDasharray={circumference + " " + circumference}
        style={{ strokeDashoffset, transform: "rotate(-90deg)", transformOrigin: "50% 50%" }}
        r={normalizedRadius}
        cx={radius}
        cy={radius}
      />
    </svg>
  );
}

// Mini gauge for Sharpe ratio
function SharpeGauge({ sharpe }: { sharpe: number }) {
  // Map sharpe -1 to 3 onto 0-180 degrees
  const minSharpe = -1;
  const maxSharpe = 3;
  const clampedSharpe = Math.max(minSharpe, Math.min(maxSharpe, sharpe));
  const angle = ((clampedSharpe - minSharpe) / (maxSharpe - minSharpe)) * 180;

  const getColor = () => {
    if (sharpe >= 2) return "var(--accent)";
    if (sharpe >= 1) return "var(--accent-2)";
    if (sharpe >= 0) return "#999";
    return "var(--danger)";
  };

  return (
    <svg width="50" height="30" viewBox="0 0 50 30">
      {/* Background arc */}
      <path
        d="M 5 25 A 20 20 0 0 1 45 25"
        fill="none"
        stroke="#e0d7cc"
        strokeWidth="4"
        strokeLinecap="round"
      />
      {/* Value indicator */}
      <circle
        cx={25 + 20 * Math.cos(((180 - angle) * Math.PI) / 180)}
        cy={25 - 20 * Math.sin(((180 - angle) * Math.PI) / 180)}
        r="4"
        fill={getColor()}
      />
    </svg>
  );
}

function getSharpeQualitative(sharpe: number): { label: string; color: string } {
  if (sharpe >= 2) return { label: "Excellent", color: "var(--accent)" };
  if (sharpe >= 1) return { label: "Good", color: "#4a9" };
  if (sharpe >= 0.5) return { label: "Moderate", color: "var(--accent-2)" };
  if (sharpe >= 0) return { label: "Weak", color: "#999" };
  return { label: "Poor", color: "var(--danger)" };
}

function getDrawdownQualitative(dd: number): { label: string; color: string } {
  const absDd = Math.abs(dd);
  if (absDd <= 10) return { label: "Low", color: "var(--accent)" };
  if (absDd <= 20) return { label: "Moderate", color: "var(--accent-2)" };
  if (absDd <= 30) return { label: "High", color: "#e67e22" };
  return { label: "Severe", color: "var(--danger)" };
}

function getWinRateQualitative(wr: number): { label: string; color: string } {
  if (wr >= 60) return { label: "Strong", color: "var(--accent)" };
  if (wr >= 50) return { label: "Good", color: "#4a9" };
  if (wr >= 40) return { label: "Moderate", color: "var(--accent-2)" };
  return { label: "Weak", color: "var(--danger)" };
}

function getProfitFactorQualitative(pf: number): { label: string; color: string } {
  if (pf >= 2) return { label: "Excellent", color: "var(--accent)" };
  if (pf >= 1.5) return { label: "Good", color: "#4a9" };
  if (pf >= 1) return { label: "Breakeven", color: "var(--accent-2)" };
  return { label: "Losing", color: "var(--danger)" };
}

export default function QuickStats({ run }: QuickStatsProps) {
  const report = run.report;
  if (!report) return null;

  const sharpe = report.sharpe_ratio ?? 0;
  const maxDd = report.max_drawdown_pct ?? 0;
  const winRate = report.win_rate ?? 0;
  const profitFactor = report.profit_factor ?? 0;
  const totalTrades = report.total_trades ?? 0;

  const sharpeQ = getSharpeQualitative(sharpe);
  const ddQ = getDrawdownQualitative(maxDd);
  const wrQ = getWinRateQualitative(winRate);
  const pfQ = getProfitFactorQualitative(profitFactor);

  return (
    <div
      className="card"
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "12px",
        justifyContent: "center",
      }}
    >
      <MetricCard
        label="Sharpe Ratio"
        value={sharpe.toFixed(2)}
        qualitative={sharpeQ.label}
        qualitativeColor={sharpeQ.color}
        visual={<SharpeGauge sharpe={sharpe} />}
      />
      <MetricCard
        label="Max Drawdown"
        value={`${maxDd.toFixed(1)}%`}
        qualitative={ddQ.label}
        qualitativeColor={ddQ.color}
      />
      <MetricCard
        label="Win Rate"
        value={`${winRate.toFixed(1)}%`}
        qualitative={wrQ.label}
        qualitativeColor={wrQ.color}
        visual={<WinRateDonut winRate={winRate} />}
      />
      <MetricCard
        label="Profit Factor"
        value={profitFactor.toFixed(2)}
        qualitative={pfQ.label}
        qualitativeColor={pfQ.color}
      />
      <MetricCard
        label="Total Trades"
        value={totalTrades}
        qualitative={totalTrades >= 30 ? "Sufficient" : "Limited"}
        qualitativeColor={totalTrades >= 30 ? "var(--accent)" : "var(--accent-2)"}
      />
    </div>
  );
}
