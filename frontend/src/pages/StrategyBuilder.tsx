import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useStrategyBuilderStore } from "../store/strategyBuilderStore";
import { IndicatorPalette, IndicatorCard, ConditionBuilder } from "../components/strategy";
import { createStrategy, getStrategy, updateStrategy, createBacktest, validateTicker } from "../api";
import type { StrategyCreate, IndicatorInput, ConditionGroupInput, Strategy } from "../types";

const steps = ["Indicators", "Conditions", "Backtest", "Review"];

export default function StrategyBuilderVisual() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tickerValid, setTickerValid] = useState<boolean | null>(null);

  // Zustand store
  const name = useStrategyBuilderStore((s) => s.name);
  const description = useStrategyBuilderStore((s) => s.description);
  const indicators = useStrategyBuilderStore((s) => s.indicators);
  const entry = useStrategyBuilderStore((s) => s.entry);
  const exit = useStrategyBuilderStore((s) => s.exit);
  const setName = useStrategyBuilderStore((s) => s.setName);
  const setDescription = useStrategyBuilderStore((s) => s.setDescription);
  const loadStrategy = useStrategyBuilderStore((s) => s.loadStrategy);
  const reset = useStrategyBuilderStore((s) => s.reset);
  const undo = useStrategyBuilderStore((s) => s.undo);
  const redo = useStrategyBuilderStore((s) => s.redo);
  const historyIndex = useStrategyBuilderStore((s) => s.historyIndex);
  const historyLength = useStrategyBuilderStore((s) => s.history.length);

  // Backtest config state
  const [ticker, setTicker] = useState("AAPL");
  const [assetClass, setAssetClass] = useState<"STOCK" | "CRYPTO">("STOCK");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2023-12-31");
  const [initialCapital, setInitialCapital] = useState("10000");
  const [resolution, setResolution] = useState("1d");
  const [positionSizeType, setPositionSizeType] = useState<"full_capital" | "percent_capital">("full_capital");
  const [positionSizeValue, setPositionSizeValue] = useState("100");
  const [stopLossPct, setStopLossPct] = useState("");
  const [takeProfitPct, setTakeProfitPct] = useState("");

  const resolutionOptions =
    assetClass === "CRYPTO"
      ? ["1m", "5m", "15m", "1h", "4h", "1d"]
      : ["1m", "5m", "15m", "1h", "1d"];

  // Load existing strategy
  useEffect(() => {
    if (!id) {
      reset();
      return;
    }
    setLoading(true);
    getStrategy(id)
      .then((strategy: Strategy) => {
        const entryGroup = strategy.condition_groups.find((g) => g.group_type === "ENTRY");
        const exitGroup = strategy.condition_groups.find((g) => g.group_type === "EXIT");
        loadStrategy({
          name: strategy.name,
          description: strategy.description || "",
          indicators: strategy.indicators.map((ind, idx) => ({
            indicator_type: ind.indicator_type,
            alias: ind.alias,
            params: ind.params || {},
            display_order: ind.display_order ?? idx,
          })) as IndicatorInput[],
          entry: entryGroup
            ? { logic: entryGroup.logic as "AND" | "OR", conditions: entryGroup.conditions }
            : { logic: "AND", conditions: [] },
          exit: exitGroup
            ? { logic: exitGroup.logic as "AND" | "OR", conditions: exitGroup.conditions }
            : { logic: "AND", conditions: [] },
        });
      })
      .catch((err: Error) => setError(err.message || "Failed to load strategy"))
      .finally(() => setLoading(false));
  }, [id, loadStrategy, reset]);

  const handleValidateTicker = async () => {
    try {
      const valid = await validateTicker(ticker, assetClass);
      setTickerValid(valid);
    } catch {
      setTickerValid(false);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: StrategyCreate = {
        name,
        description,
        indicators,
        entry: entry as ConditionGroupInput,
        exit: exit as ConditionGroupInput,
      };
      const strategy = id ? await updateStrategy(id, payload) : await createStrategy(payload);
      const backtest = await createBacktest({
        strategy_id: strategy.id,
        ticker,
        asset_class: assetClass,
        start_date: startDate,
        end_date: endDate,
        bar_resolution: resolution,
        initial_capital: Number(initialCapital),
        position_size_type: positionSizeType,
        position_size_value: Number(positionSizeValue),
        stop_loss_pct: stopLossPct ? Number(stopLossPct) : null,
        take_profit_pct: takeProfitPct ? Number(takeProfitPct) : null,
      });
      navigate(`/backtests/${backtest.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container fade-in">
      {/* Header */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h1>{id ? "Edit Strategy" : "New Strategy"}</h1>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn secondary" onClick={undo} disabled={historyIndex < 0}>
              Undo
            </button>
            <button className="btn secondary" onClick={redo} disabled={historyIndex >= historyLength - 1}>
              Redo
            </button>
          </div>
        </div>
        <div className="stepper" style={{ marginTop: 12 }}>
          {steps.map((label, idx) => (
            <div
              key={label}
              className={`step ${idx === step ? "active" : ""}`}
              style={{ cursor: "pointer" }}
              onClick={() => setStep(idx)}
            >
              {label}
            </div>
          ))}
        </div>
      </div>

      {error && <div className="notice">{error}</div>}

      {/* Step 0: Indicators */}
      {step === 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 24 }}>
          {/* Left: Palette */}
          <IndicatorPalette />

          {/* Right: Configured Indicators */}
          <div className="card">
            <div className="row" style={{ marginBottom: 16 }}>
              <div>
                <label>Strategy Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="My Strategy" />
              </div>
              <div>
                <label>Description</label>
                <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" />
              </div>
            </div>

            <h3>Configured Indicators ({indicators.length})</h3>
            {indicators.length === 0 && (
              <div className="notice">Click an indicator in the palette to add it.</div>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {indicators.map((ind, idx) => (
                <IndicatorCard key={`${ind.alias}-${idx}`} indicator={ind} index={idx} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Step 1: Conditions */}
      {step === 1 && <ConditionBuilder />}

      {/* Step 2: Backtest Config */}
      {step === 2 && (
        <div className="card">
          <h2>Backtest Configuration</h2>
          <div className="row">
            <div>
              <label>Ticker</label>
              <input value={ticker} onChange={(e) => setTicker(e.target.value)} />
            </div>
            <div>
              <label>Asset Class</label>
              <select value={assetClass} onChange={(e) => setAssetClass(e.target.value as "STOCK" | "CRYPTO")}>
                <option value="STOCK">Stock</option>
                <option value="CRYPTO">Crypto</option>
              </select>
            </div>
            <div>
              <label>Initial Capital</label>
              <input type="number" value={initialCapital} onChange={(e) => setInitialCapital(e.target.value)} />
            </div>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <div>
              <label>Start Date</label>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div>
              <label>End Date</label>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
            <div>
              <label>Resolution</label>
              <select value={resolution} onChange={(e) => setResolution(e.target.value)}>
                {resolutionOptions.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <div>
              <label>Position Sizing</label>
              <select value={positionSizeType} onChange={(e) => setPositionSizeType(e.target.value as "full_capital" | "percent_capital")}>
                <option value="full_capital">Full Capital</option>
                <option value="percent_capital">Percent of Capital</option>
              </select>
            </div>
            {positionSizeType === "percent_capital" && (
              <div>
                <label>Percentage (%)</label>
                <input type="number" value={positionSizeValue} onChange={(e) => setPositionSizeValue(e.target.value)} />
              </div>
            )}
            <div>
              <label>Stop Loss (%)</label>
              <input type="number" value={stopLossPct} onChange={(e) => setStopLossPct(e.target.value)} placeholder="Optional" />
            </div>
            <div>
              <label>Take Profit (%)</label>
              <input type="number" value={takeProfitPct} onChange={(e) => setTakeProfitPct(e.target.value)} placeholder="Optional" />
            </div>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn secondary" onClick={handleValidateTicker}>
              Validate Ticker
            </button>
            {tickerValid !== null && (
              <span className="tag">{tickerValid ? "Valid" : "Invalid"}</span>
            )}
          </div>
        </div>
      )}

      {/* Step 3: Review */}
      {step === 3 && (
        <div className="card">
          <h2>Review & Submit</h2>
          <div className="grid grid-2" style={{ marginBottom: 24 }}>
            <div>
              <h3>Strategy</h3>
              <p><strong>{name || "Untitled"}</strong></p>
              <p>{description || "No description"}</p>
              <p>Indicators: {indicators.length}</p>
              <p>Entry conditions: {entry.conditions.length} ({entry.logic})</p>
              <p>Exit conditions: {exit.conditions.length} ({exit.logic})</p>
            </div>
            <div>
              <h3>Backtest</h3>
              <p><strong>Ticker:</strong> {ticker} ({assetClass})</p>
              <p><strong>Period:</strong> {startDate} to {endDate}</p>
              <p><strong>Resolution:</strong> {resolution}</p>
              <p><strong>Capital:</strong> ${Number(initialCapital).toLocaleString()}</p>
              <p><strong>Position:</strong> {positionSizeType === "full_capital" ? "100%" : `${positionSizeValue}%`}</p>
              {stopLossPct && <p><strong>Stop Loss:</strong> {stopLossPct}%</p>}
              {takeProfitPct && <p><strong>Take Profit:</strong> {takeProfitPct}%</p>}
            </div>
          </div>
          <button className="btn" onClick={handleSubmit} disabled={loading}>
            {loading ? "Submitting..." : "Run Backtest"}
          </button>
        </div>
      )}

      {/* Navigation */}
      <div className="row">
        <button className="btn secondary" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
          Back
        </button>
        <button className="btn" disabled={step === steps.length - 1} onClick={() => setStep((s) => s + 1)}>
          Next
        </button>
      </div>
    </div>
  );
}
