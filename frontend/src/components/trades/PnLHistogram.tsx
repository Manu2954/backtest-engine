import { useMemo } from "react";
import type { TradeLog } from "../../types";

interface PnLHistogramProps {
  trades: TradeLog[];
}

const NUM_BINS = 20;

export default function PnLHistogram({ trades }: PnLHistogramProps) {
  const histogramData = useMemo(() => {
    if (trades.length === 0) return [];

    const pnls = trades.map((t) => t.pnl);
    const minPnl = Math.min(...pnls);
    const maxPnl = Math.max(...pnls);

    // Handle edge case where all trades have same P&L
    if (minPnl === maxPnl) {
      return [{ binStart: minPnl, binEnd: maxPnl, count: trades.length, isPositive: minPnl >= 0 }];
    }

    const binWidth = (maxPnl - minPnl) / NUM_BINS;
    const bins: { binStart: number; binEnd: number; count: number; isPositive: boolean }[] = [];

    for (let i = 0; i < NUM_BINS; i++) {
      const binStart = minPnl + i * binWidth;
      const binEnd = binStart + binWidth;
      const count = pnls.filter((p) => p >= binStart && (i === NUM_BINS - 1 ? p <= binEnd : p < binEnd)).length;
      bins.push({
        binStart,
        binEnd,
        count,
        isPositive: (binStart + binEnd) / 2 >= 0,
      });
    }

    return bins;
  }, [trades]);

  const maxCount = Math.max(...histogramData.map((b) => b.count), 1);

  if (trades.length === 0) {
    return (
      <div className="chart-card">
        <h3>P&L Distribution</h3>
        <div className="chart-empty">No trades to display</div>
      </div>
    );
  }

  return (
    <div className="chart-card">
      <h3>P&L Distribution</h3>
      <div className="histogram-container">
        <div className="histogram-bars">
          {histogramData.map((bin, i) => (
            <div key={i} className="histogram-bar-wrapper">
              <div
                className="histogram-bar"
                style={{
                  height: `${(bin.count / maxCount) * 100}%`,
                  backgroundColor: bin.isPositive ? "var(--accent)" : "var(--danger)",
                }}
                title={`$${bin.binStart.toFixed(0)} to $${bin.binEnd.toFixed(0)}: ${bin.count} trades`}
              />
            </div>
          ))}
        </div>
        <div className="histogram-labels">
          <span>${histogramData[0]?.binStart.toFixed(0) || 0}</span>
          <span>$0</span>
          <span>${histogramData[histogramData.length - 1]?.binEnd.toFixed(0) || 0}</span>
        </div>
      </div>
    </div>
  );
}
