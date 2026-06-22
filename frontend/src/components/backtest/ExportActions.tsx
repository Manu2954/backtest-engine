import type { BacktestOut, TradeLog } from "../../types";

interface ExportActionsProps {
  run: BacktestOut;
  trades: TradeLog[];
}

function downloadCSV(filename: string, csvContent: string) {
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

function generateTradeLogCSV(trades: TradeLog[]): string {
  const headers = [
    "Entry Date",
    "Entry Price",
    "Exit Date",
    "Exit Price",
    "Shares",
    "P&L",
    "P&L %",
    "Duration (days)",
    "Exit Reason",
  ];

  const rows = trades.map((t) => [
    t.entry_date,
    t.entry_price.toFixed(2),
    t.exit_date,
    t.exit_price.toFixed(2),
    t.shares.toFixed(4),
    t.pnl.toFixed(2),
    t.pnl_pct.toFixed(2),
    t.trade_duration_days.toString(),
    t.exit_reason || "",
  ]);

  return [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
}

function generateSummaryCSV(run: BacktestOut): string {
  const report = run.report || run.results;
  const lines: string[] = [
    "Backtest Summary Report",
    "",
    "Configuration",
    `Ticker,${run.ticker}`,
    `Asset Class,${run.asset_class}`,
    `Start Date,${run.start_date}`,
    `End Date,${run.end_date}`,
    `Bar Resolution,${run.bar_resolution}`,
    `Initial Capital,$${run.initial_capital.toFixed(2)}`,
    `Position Size Type,${run.position_size_type || "full_capital"}`,
    `Position Size Value,${run.position_size_value || 100}`,
    `Stop Loss %,${run.stop_loss_pct ?? "N/A"}`,
    `Take Profit %,${run.take_profit_pct ?? "N/A"}`,
    `Commission Per Trade,$${run.commission_per_trade || 0}`,
    `Commission %,${run.commission_pct || 0}%`,
    `Slippage %,${run.slippage_pct || 0}%`,
    "",
    "Performance Metrics",
    `Total Return %,${report?.total_return_pct?.toFixed(2) ?? "N/A"}`,
    `CAGR %,${report?.cagr?.toFixed(2) ?? "N/A"}`,
    `Sharpe Ratio,${report?.sharpe_ratio?.toFixed(2) ?? "N/A"}`,
    `Max Drawdown %,${report?.max_drawdown_pct?.toFixed(2) ?? "N/A"}`,
    `Final Capital,$${report?.final_capital?.toFixed(2) ?? "N/A"}`,
    "",
    "Trade Statistics",
    `Total Trades,${report?.total_trades ?? "N/A"}`,
    `Win Rate %,${report?.win_rate?.toFixed(2) ?? "N/A"}`,
    `Profit Factor,${report?.profit_factor?.toFixed(2) ?? "N/A"}`,
    `Avg Win,$${report?.avg_win?.toFixed(2) ?? "N/A"}`,
    `Avg Loss,$${report?.avg_loss?.toFixed(2) ?? "N/A"}`,
    `Largest Win,$${report?.largest_win?.toFixed(2) ?? "N/A"}`,
    `Largest Loss,$${report?.largest_loss?.toFixed(2) ?? "N/A"}`,
    `Avg Trade Duration (days),${report?.avg_trade_duration_days?.toFixed(1) ?? "N/A"}`,
    "",
    "Benchmark Comparison",
    `Benchmark Return %,${report?.benchmark_return_pct?.toFixed(2) ?? "N/A"}`,
    `Alpha,${report?.alpha?.toFixed(2) ?? "N/A"}`,
    `Beta,${report?.beta?.toFixed(2) ?? "N/A"}`,
  ];

  return lines.join("\n");
}

function handlePrint() {
  window.print();
}

export default function ExportActions({ run, trades }: ExportActionsProps) {
  const handleExportTradeLog = () => {
    const csv = generateTradeLogCSV(trades);
    const filename = `trade_log_${run.ticker}_${run.start_date}_${run.end_date}.csv`;
    downloadCSV(filename, csv);
  };

  const handleExportSummary = () => {
    const csv = generateSummaryCSV(run);
    const filename = `backtest_summary_${run.ticker}_${run.start_date}_${run.end_date}.csv`;
    downloadCSV(filename, csv);
  };

  return (
    <div className="card">
      <h2>Export</h2>
      <p style={{ color: "var(--muted)", marginBottom: "16px", fontSize: "0.9rem" }}>
        Download backtest data for further analysis or reporting.
      </p>
      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
        <button
          className="btn secondary"
          onClick={handleExportSummary}
          style={{ display: "flex", alignItems: "center", gap: "8px" }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Summary CSV
        </button>
        <button
          className="btn secondary"
          onClick={handleExportTradeLog}
          disabled={trades.length === 0}
          style={{ display: "flex", alignItems: "center", gap: "8px" }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Trade Log CSV ({trades.length} trades)
        </button>
        <button
          className="btn secondary"
          onClick={handlePrint}
          style={{ display: "flex", alignItems: "center", gap: "8px" }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="6 9 6 2 18 2 18 9" />
            <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
            <rect x="6" y="14" width="12" height="8" />
          </svg>
          Print Report
        </button>
      </div>
    </div>
  );
}
