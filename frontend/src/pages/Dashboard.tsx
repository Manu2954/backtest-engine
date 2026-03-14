import { Link } from "react-router-dom";

export default function Dashboard() {
  return (
    <div className="container fade-in">
      <div className="card" style={{ background: "linear-gradient(135deg, var(--card) 0%, #f8f6f2 100%)" }}>
        <h1 style={{ fontSize: "2.5rem", marginBottom: "16px" }}>Build, Test, Optimize</h1>
        <p style={{ fontSize: "1.1rem", color: "var(--muted)", maxWidth: "600px" }}>
          Create technical indicator-based trading strategies, backtest them against historical data,
          and analyze comprehensive performance metrics—all in one place.
        </p>
        <div className="row" style={{ marginTop: "24px" }}>
          <Link className="btn" to="/strategies/new">
            Create Strategy
          </Link>
          <Link className="btn secondary" to="/strategies">
            View Strategies
          </Link>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3 style={{ color: "var(--accent)" }}>✨ What You Can Do</h3>
          <ul style={{ lineHeight: "1.8", color: "var(--muted)" }}>
            <li><strong>11 Technical Indicators</strong> - RSI, MACD, EMA, SMA, Bollinger Bands, ATR, ADX, Ichimoku, and more</li>
            <li><strong>Advanced Operators</strong> - Crossovers, trend detection (IS_RISING/IS_FALLING), lookback comparisons</li>
            <li><strong>Risk Management</strong> - Stop loss, take profit, risk-based position sizing, dynamic stops</li>
            <li><strong>Multiple Asset Classes</strong> - Test on stocks (via Yahoo Finance) or crypto (via Binance)</li>
            <li><strong>Realistic Simulation</strong> - Commission, slippage, and periodic contributions</li>
          </ul>
        </div>

        <div className="card">
          <h3 style={{ color: "var(--accent)" }}>📊 Get Started</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <Link
              className="btn secondary"
              to="/strategies/new"
              style={{ textAlign: "left", padding: "16px" }}
            >
              <div style={{ fontWeight: 600, marginBottom: "4px" }}>1. Strategy Builder</div>
              <div style={{ fontSize: "0.9rem", opacity: 0.8 }}>
                Define indicators and entry/exit conditions
              </div>
            </Link>
            <Link
              className="btn secondary"
              to="/backtests"
              style={{ textAlign: "left", padding: "16px" }}
            >
              <div style={{ fontWeight: 600, marginBottom: "4px" }}>2. Run Backtests</div>
              <div style={{ fontSize: "0.9rem", opacity: 0.8 }}>
                Test strategies on historical data
              </div>
            </Link>
            <div className="btn secondary" style={{ textAlign: "left", padding: "16px", cursor: "default" }}>
              <div style={{ fontWeight: 600, marginBottom: "4px" }}>3. Analyze Results</div>
              <div style={{ fontSize: "0.9rem", opacity: 0.8 }}>
                Review metrics, equity curves, and trade logs
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ background: "#fff6e8", border: "1px solid #f2e2c6" }}>
        <h3 style={{ color: "var(--accent-2)", marginBottom: "12px" }}>💡 Pro Tips</h3>
        <div className="grid grid-2" style={{ gap: "12px" }}>
          <div>
            <strong>Start Simple</strong> - Begin with 1-2 indicators and basic conditions, then add complexity.
          </div>
          <div>
            <strong>Test Realistically</strong> - Always include commission and slippage for accurate results.
          </div>
          <div>
            <strong>Compare Benchmarks</strong> - Check if your strategy beats buy-and-hold returns.
          </div>
          <div>
            <strong>Use LOOKBACK</strong> - Detect trends by comparing current values to historical ones (e.g., "adx:-3").
          </div>
        </div>
      </div>
    </div>
  );
}
