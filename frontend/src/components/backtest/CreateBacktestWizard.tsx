import { useMemo, useState } from "react";
import { validateTicker } from "../../api/client";
import type { BacktestCreate, StrategyOut } from "../../types";

interface CreateBacktestWizardProps {
  strategies: StrategyOut[];
  onSubmit: (payload: BacktestCreate) => Promise<void>;
  onClose: () => void;
  initialData?: Partial<BacktestCreate>;
}

type WizardStep = 1 | 2 | 3;

const tickerPresets = [
  { label: "AAPL", ticker: "AAPL", assetClass: "STOCK" as const },
  { label: "MSFT", ticker: "MSFT", assetClass: "STOCK" as const },
  { label: "SPY", ticker: "SPY", assetClass: "STOCK" as const },
  { label: "BTC", ticker: "BTCUSDT", assetClass: "CRYPTO" as const },
  { label: "ETH", ticker: "ETHUSDT", assetClass: "CRYPTO" as const },
];

const datePresets = [
  { label: "YTD", getRange: () => ({ start: `${new Date().getFullYear()}-01-01`, end: new Date().toISOString().split("T")[0] }) },
  { label: "1Y", getRange: () => {
    const end = new Date();
    const start = new Date(end);
    start.setFullYear(start.getFullYear() - 1);
    return { start: start.toISOString().split("T")[0], end: end.toISOString().split("T")[0] };
  }},
  { label: "3Y", getRange: () => {
    const end = new Date();
    const start = new Date(end);
    start.setFullYear(start.getFullYear() - 3);
    return { start: start.toISOString().split("T")[0], end: end.toISOString().split("T")[0] };
  }},
  { label: "5Y", getRange: () => {
    const end = new Date();
    const start = new Date(end);
    start.setFullYear(start.getFullYear() - 5);
    return { start: start.toISOString().split("T")[0], end: end.toISOString().split("T")[0] };
  }},
];

export default function CreateBacktestWizard({
  strategies,
  onSubmit,
  onClose,
  initialData,
}: CreateBacktestWizardProps) {
  const [step, setStep] = useState<WizardStep>(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tickerValid, setTickerValid] = useState<boolean | null>(null);

  // Step 1: Strategy + Ticker + Asset Class
  const [strategyId, setStrategyId] = useState(initialData?.strategy_id || strategies[0]?.id || "");
  const [ticker, setTicker] = useState(initialData?.ticker || "AAPL");
  const [assetClass, setAssetClass] = useState<"STOCK" | "CRYPTO">((initialData?.asset_class as "STOCK" | "CRYPTO") || "STOCK");
  const [provider, setProvider] = useState(initialData?.provider || "");

  // Step 2: Date Range + Resolution + Capital
  const [startDate, setStartDate] = useState(initialData?.start_date || "2020-01-01");
  const [endDate, setEndDate] = useState(initialData?.end_date || "2023-12-31");
  const [resolution, setResolution] = useState(initialData?.bar_resolution || "1d");
  const [initialCapital, setInitialCapital] = useState(String(initialData?.initial_capital || 10000));

  // Step 3: Position Sizing + Risk + Costs
  const [positionSizeType, setPositionSizeType] = useState<"full_capital" | "percent_capital" | "fixed_amount" | "risk_based">(
    (initialData?.position_size_type as any) || "full_capital"
  );
  const [positionSizeValue, setPositionSizeValue] = useState(String(initialData?.position_size_value || 100));
  const [stopLossPct, setStopLossPct] = useState(initialData?.stop_loss_pct != null ? String(initialData.stop_loss_pct) : "");
  const [takeProfitPct, setTakeProfitPct] = useState(initialData?.take_profit_pct != null ? String(initialData.take_profit_pct) : "");
  const [dynamicStopColumn, setDynamicStopColumn] = useState(initialData?.dynamic_stop_column || "");
  const [commissionPerTrade, setCommissionPerTrade] = useState(String(initialData?.commission_per_trade || 0));
  const [commissionPct, setCommissionPct] = useState(String(initialData?.commission_pct || 0));
  const [slippagePct, setSlippagePct] = useState(String(initialData?.slippage_pct || 0));

  // Collapsible sections for Step 3
  const [riskExpanded, setRiskExpanded] = useState(false);
  const [costsExpanded, setCostsExpanded] = useState(false);

  const resolutionOptions = useMemo(
    () =>
      assetClass === "CRYPTO"
        ? ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1mo"]
        : ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
    [assetClass]
  );

  const indicatorAliases = useMemo(() => {
    const strategy = strategies.find((s) => s.id === strategyId);
    if (!strategy) return [];
    return strategy.indicators.map((ind) => ind.alias);
  }, [strategies, strategyId]);

  const handleValidateTicker = async () => {
    try {
      const valid = await validateTicker(ticker, assetClass);
      setTickerValid(valid);
    } catch {
      setTickerValid(false);
    }
  };

  const handleSubmit = async () => {
    if (!strategyId) {
      setError("Please select a strategy");
      return;
    }
    setSubmitting(true);
    setError(null);

    try {
      await onSubmit({
        strategy_id: strategyId,
        ticker,
        asset_class: assetClass,
        provider: provider || undefined,
        start_date: startDate,
        end_date: endDate,
        bar_resolution: resolution,
        initial_capital: Number(initialCapital),
        position_size_type: positionSizeType,
        position_size_value: Number(positionSizeValue),
        stop_loss_pct: stopLossPct ? Number(stopLossPct) : undefined,
        take_profit_pct: takeProfitPct ? Number(takeProfitPct) : undefined,
        dynamic_stop_column: dynamicStopColumn || undefined,
        commission_per_trade: Number(commissionPerTrade),
        commission_pct: Number(commissionPct),
        slippage_pct: Number(slippagePct),
      });
    } catch (err: any) {
      setError(err.message || "Failed to create backtest");
    } finally {
      setSubmitting(false);
    }
  };

  const canProceed = (currentStep: WizardStep): boolean => {
    if (currentStep === 1) {
      return !!strategyId && !!ticker;
    }
    if (currentStep === 2) {
      return !!startDate && !!endDate && !!resolution && Number(initialCapital) > 0;
    }
    return true;
  };

  const isIntraday = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"].includes(resolution);
  const rangeDays = Math.max(
    0,
    (new Date(endDate).getTime() - new Date(startDate).getTime()) / (1000 * 60 * 60 * 24)
  );

  return (
    <div className="modal-backdrop">
      <div className="modal" style={{ width: "min(700px, 95vw)" }}>
        <h2 style={{ marginBottom: "20px" }}>Create Backtest</h2>

        {/* Stepper */}
        <div className="stepper" style={{ marginBottom: "24px" }}>
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`step ${step === s ? "active" : ""}`}
              style={{ cursor: s < step ? "pointer" : "default" }}
              onClick={() => s < step && setStep(s as WizardStep)}
            >
              {s === 1 && "1. Strategy & Ticker"}
              {s === 2 && "2. Date & Capital"}
              {s === 3 && "3. Settings"}
            </div>
          ))}
        </div>

        {error && (
          <div className="notice" style={{ marginBottom: "16px", background: "#ffe8e6", borderColor: "#ffcccc", color: "var(--danger)" }}>
            {error}
          </div>
        )}

        {/* Step 1: Strategy + Ticker + Asset Class */}
        {step === 1 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <label>Strategy</label>
              <select value={strategyId} onChange={(e) => setStrategyId(e.target.value)}>
                <option value="">Select a strategy...</option>
                {strategies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="row">
              <div>
                <label>Ticker Symbol</label>
                <input
                  value={ticker}
                  onChange={(e) => {
                    setTicker(e.target.value.toUpperCase());
                    setTickerValid(null);
                  }}
                  placeholder="e.g., AAPL, BTCUSDT"
                />
              </div>
              <div>
                <label>Asset Class</label>
                <select
                  value={assetClass}
                  onChange={(e) => setAssetClass(e.target.value as "STOCK" | "CRYPTO")}
                >
                  <option value="STOCK">Stock</option>
                  <option value="CRYPTO">Crypto</option>
                </select>
              </div>
            </div>

            {/* Quick presets */}
            <div>
              <label style={{ display: "block", marginBottom: "8px" }}>Quick Select</label>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                {tickerPresets.map((preset) => (
                  <button
                    key={preset.label}
                    className="btn secondary"
                    style={{
                      padding: "6px 12px",
                      fontSize: "0.85rem",
                      background: ticker === preset.ticker && assetClass === preset.assetClass ? "var(--accent)" : undefined,
                      color: ticker === preset.ticker && assetClass === preset.assetClass ? "white" : undefined,
                    }}
                    onClick={() => {
                      setTicker(preset.ticker);
                      setAssetClass(preset.assetClass);
                      setTickerValid(null);
                    }}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="row" style={{ alignItems: "center" }}>
              <button className="btn secondary" onClick={handleValidateTicker} style={{ flex: "none", width: "auto" }}>
                Validate Ticker
              </button>
              {tickerValid !== null && (
                <span
                  className="tag"
                  style={{
                    background: tickerValid ? "#e8f5f3" : "#ffe8e6",
                    color: tickerValid ? "var(--accent)" : "var(--danger)",
                  }}
                >
                  {tickerValid ? "Valid" : "Invalid"}
                </span>
              )}
            </div>

            <div>
              <label>Data Provider (optional)</label>
              <select value={provider} onChange={(e) => setProvider(e.target.value)}>
                <option value="">Auto (default)</option>
                <option value="yfinance">Yahoo Finance</option>
                <option value="binance">Binance</option>
              </select>
              <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginTop: "4px" }}>
                Leave as Auto to use yfinance for stocks, binance for crypto
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Date Range + Resolution + Capital */}
        {step === 2 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <label style={{ display: "block", marginBottom: "8px" }}>Date Range Presets</label>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                {datePresets.map((preset) => (
                  <button
                    key={preset.label}
                    className="btn secondary"
                    style={{ padding: "6px 12px", fontSize: "0.85rem" }}
                    onClick={() => {
                      const range = preset.getRange();
                      setStartDate(range.start);
                      setEndDate(range.end);
                    }}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="row">
              <div>
                <label>Start Date</label>
                <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </div>
              <div>
                <label>End Date</label>
                <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
            </div>

            <div className="row">
              <div>
                <label>Resolution</label>
                <select value={resolution} onChange={(e) => setResolution(e.target.value)}>
                  {resolutionOptions.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label>Initial Capital ($)</label>
                <input
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(e.target.value)}
                  min={1}
                />
              </div>
            </div>

            {assetClass === "STOCK" && isIntraday && rangeDays > 60 && (
              <div className="notice">
                Yahoo intraday data is limited to the most recent 60 days. Reduce the date range or use daily resolution.
              </div>
            )}
          </div>
        )}

        {/* Step 3: Position Sizing + Risk + Costs */}
        {step === 3 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Position Sizing */}
            <div className="card" style={{ padding: "16px", margin: 0 }}>
              <h4 style={{ margin: "0 0 12px 0" }}>Position Sizing</h4>
              <div className="row">
                <div>
                  <label>Type</label>
                  <select
                    value={positionSizeType}
                    onChange={(e) => setPositionSizeType(e.target.value as any)}
                  >
                    <option value="full_capital">Full Capital</option>
                    <option value="percent_capital">Percent of Capital</option>
                    <option value="fixed_amount">Fixed Amount</option>
                    <option value="risk_based">Risk-Based</option>
                  </select>
                </div>
                <div>
                  <label>Value</label>
                  <input
                    type="number"
                    value={positionSizeValue}
                    onChange={(e) => setPositionSizeValue(e.target.value)}
                    placeholder={
                      positionSizeType === "percent_capital"
                        ? "Percent (0-100)"
                        : positionSizeType === "fixed_amount"
                        ? "Dollar amount"
                        : positionSizeType === "risk_based"
                        ? "Risk % (e.g., 1)"
                        : "Not used"
                    }
                  />
                </div>
              </div>
            </div>

            {/* Risk Management (collapsible) */}
            <div className="card" style={{ padding: "16px", margin: 0 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  cursor: "pointer",
                }}
                onClick={() => setRiskExpanded(!riskExpanded)}
              >
                <h4 style={{ margin: 0 }}>Risk Management</h4>
                <span style={{ color: "var(--muted)" }}>{riskExpanded ? "−" : "+"}</span>
              </div>
              {riskExpanded && (
                <div style={{ marginTop: "12px" }}>
                  <div className="row">
                    <div>
                      <label>Stop Loss %</label>
                      <input
                        type="number"
                        value={stopLossPct}
                        onChange={(e) => setStopLossPct(e.target.value)}
                        placeholder="e.g., 5"
                      />
                    </div>
                    <div>
                      <label>Take Profit %</label>
                      <input
                        type="number"
                        value={takeProfitPct}
                        onChange={(e) => setTakeProfitPct(e.target.value)}
                        placeholder="e.g., 10"
                      />
                    </div>
                  </div>
                  <div style={{ marginTop: "12px" }}>
                    <label>Dynamic Stop (Indicator-based)</label>
                    <select
                      value={dynamicStopColumn}
                      onChange={(e) => setDynamicStopColumn(e.target.value)}
                    >
                      <option value="">None</option>
                      {indicatorAliases.map((alias) => (
                        <option key={alias} value={alias}>
                          {alias}
                        </option>
                      ))}
                    </select>
                    <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginTop: "4px" }}>
                      Uses indicator value as trailing stop
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Transaction Costs (collapsible) */}
            <div className="card" style={{ padding: "16px", margin: 0 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  cursor: "pointer",
                }}
                onClick={() => setCostsExpanded(!costsExpanded)}
              >
                <h4 style={{ margin: 0 }}>Transaction Costs</h4>
                <span style={{ color: "var(--muted)" }}>{costsExpanded ? "−" : "+"}</span>
              </div>
              {costsExpanded && (
                <div style={{ marginTop: "12px" }}>
                  <div className="row">
                    <div>
                      <label>Commission per Trade ($)</label>
                      <input
                        type="number"
                        value={commissionPerTrade}
                        onChange={(e) => setCommissionPerTrade(e.target.value)}
                        placeholder="e.g., 1"
                      />
                    </div>
                    <div>
                      <label>Commission %</label>
                      <input
                        type="number"
                        value={commissionPct}
                        onChange={(e) => setCommissionPct(e.target.value)}
                        placeholder="e.g., 0.1"
                      />
                    </div>
                    <div>
                      <label>Slippage %</label>
                      <input
                        type="number"
                        value={slippagePct}
                        onChange={(e) => setSlippagePct(e.target.value)}
                        placeholder="e.g., 0.05"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Navigation buttons */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: "24px",
            paddingTop: "16px",
            borderTop: "1px solid var(--line)",
          }}
        >
          <button className="btn secondary" onClick={onClose}>
            Cancel
          </button>
          <div style={{ display: "flex", gap: "8px" }}>
            {step > 1 && (
              <button className="btn secondary" onClick={() => setStep((step - 1) as WizardStep)}>
                Back
              </button>
            )}
            {step < 3 ? (
              <button
                className="btn"
                onClick={() => setStep((step + 1) as WizardStep)}
                disabled={!canProceed(step)}
              >
                Next
              </button>
            ) : (
              <button className="btn" onClick={handleSubmit} disabled={submitting}>
                {submitting ? "Creating..." : "Run Backtest"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
