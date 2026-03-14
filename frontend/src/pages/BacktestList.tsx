import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, createBacktest, validateTicker } from "../api/client";
import type { BacktestOut, StrategyOut } from "../types";

export default function BacktestList() {
  const [runs, setRuns] = useState<BacktestOut[]>([]);
  const [strategies, setStrategies] = useState<StrategyOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pendingBacktest, setPendingBacktest] = useState(false);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>("");
  const [ticker, setTicker] = useState("AAPL");
  const [assetClass, setAssetClass] = useState<"STOCK" | "CRYPTO">("STOCK");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2023-12-31");
  const [initialCapital, setInitialCapital] = useState("10000");
  const [resolution, setResolution] = useState("1d");
  const [submitting, setSubmitting] = useState(false);
  const [tickerValid, setTickerValid] = useState<boolean | null>(null);
  const [contributionEnabled, setContributionEnabled] = useState(false);
  const [contributionAmount, setContributionAmount] = useState("2000");
  const [contributionFrequency, setContributionFrequency] = useState<
    "daily" | "weekly" | "monthly" | "interval_days"
  >("monthly");
  const [intervalDays, setIntervalDays] = useState("30");
  const [includeStart, setIncludeStart] = useState(false);

  // Advanced backtest options
  const [positionSizeType, setPositionSizeType] = useState<"full_capital" | "percent_capital" | "fixed_amount" | "risk_based">("full_capital");
  const [positionSizeValue, setPositionSizeValue] = useState("100");
  const [stopLossPct, setStopLossPct] = useState("");
  const [takeProfitPct, setTakeProfitPct] = useState("");
  const [dynamicStopColumn, setDynamicStopColumn] = useState("");
  const [commissionPerTrade, setCommissionPerTrade] = useState("0");
  const [commissionPct, setCommissionPct] = useState("0");
  const [slippagePct, setSlippagePct] = useState("0");

  const navigate = useNavigate();

  useEffect(() => {
    api
      .get<BacktestOut[]>("/backtests")
      .then((res) => setRuns(res.data))
      .catch((err) => setError(err.message || "Failed to load backtests"));
  }, []);

  useEffect(() => {
    api
      .get<StrategyOut[]>("/strategies")
      .then((res) => {
        setStrategies(res.data);
        if (res.data.length > 0) {
          setSelectedStrategyId(res.data[0].id);
        }
      })
      .catch((err) => setError(err.message || "Failed to load strategies"));
  }, []);

  const resolutionOptions = useMemo(
    () =>
      assetClass === "CRYPTO"
        ? ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1mo"]
        : ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
    [assetClass]
  );

  // Get indicator aliases from selected strategy for dynamic stop dropdown
  const indicatorAliases = useMemo(() => {
    const strategy = strategies.find(s => s.id === selectedStrategyId);
    if (!strategy) return [];
    return strategy.indicators.map(ind => ind.alias);
  }, [strategies, selectedStrategyId]);

  const isIntraday = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"].includes(resolution);
  const rangeDays = Math.max(
    0,
    (new Date(endDate).getTime() - new Date(startDate).getTime()) / (1000 * 60 * 60 * 24)
  );

  const handleValidateTicker = async () => {
    try {
      const valid = await validateTicker(ticker, assetClass);
      setTickerValid(valid);
    } catch {
      setTickerValid(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedStrategyId) {
      setError("Select a strategy to run a backtest.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const periodicContribution = contributionEnabled
        ? {
            amount: Number(contributionAmount),
            frequency: contributionFrequency,
            interval_days:
              contributionFrequency === "interval_days" ? Number(intervalDays) : undefined,
            include_start: includeStart,
          }
        : null;
      const run = await createBacktest({
        strategy_id: selectedStrategyId,
        ticker,
        asset_class: assetClass,
        start_date: startDate,
        end_date: endDate,
        bar_resolution: resolution,
        initial_capital: Number(initialCapital),
        periodic_contribution: periodicContribution,
        position_size_type: positionSizeType,
        position_size_value: Number(positionSizeValue),
        stop_loss_pct: stopLossPct ? Number(stopLossPct) : null,
        take_profit_pct: takeProfitPct ? Number(takeProfitPct) : null,
        dynamic_stop_column: dynamicStopColumn || null,
        commission_per_trade: Number(commissionPerTrade),
        commission_pct: Number(commissionPct),
        slippage_pct: Number(slippagePct),
      });
      setPendingBacktest(false);
      navigate(`/backtests/${run.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create backtest");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container fade-in">
      <div className="card">
        <h1>Backtest Jobs</h1>
        {error && <div className="notice">{error}</div>}
        <div className="row" style={{ marginBottom: "16px" }}>
          <button className="btn" onClick={() => setPendingBacktest(true)}>
            Run Backtest
          </button>
        </div>
        {runs.length === 0 ? (
          <p>No backtests yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Asset</th>
                <th>Period</th>
                <th>Status</th>
                <th>Capital</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td>{run.ticker}</td>
                  <td>{run.asset_class}</td>
                  <td>
                    {run.start_date} → {run.end_date}
                  </td>
                  <td>{run.status}</td>
                  <td>${run.initial_capital}</td>
                  <td>
                    <Link className="btn secondary" to={`/backtests/${run.id}`}>
                      View
                    </Link>
                    <Link className="btn secondary" style={{ marginLeft: "8px" }} to={`/backtests/${run.id}/trades`}>
                      Trades
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {pendingBacktest && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>Run Backtest</h3>
            <div className="row" style={{ marginTop: "12px" }}>
              <div>
                <label>Strategy</label>
                <select
                  value={selectedStrategyId}
                  onChange={(e) => setSelectedStrategyId(e.target.value)}
                >
                  {strategies.map((strategy) => (
                    <option key={strategy.id} value={strategy.id}>
                      {strategy.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label>Ticker</label>
                <input value={ticker} onChange={(e) => setTicker(e.target.value)} />
              </div>
            </div>
            <div className="row" style={{ marginTop: "12px" }}>
              <div>
                <label>Asset Class</label>
                <select
                  value={assetClass}
                  onChange={(e) => setAssetClass(e.target.value as "STOCK" | "CRYPTO")}
                >
                  <option value="STOCK">STOCK</option>
                  <option value="CRYPTO">CRYPTO</option>
                </select>
              </div>
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
                <label>Initial Capital</label>
                <input
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(e.target.value)}
                />
              </div>
            </div>
            <div className="row" style={{ marginTop: "12px" }}>
              <div>
                <label>Start Date</label>
                <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </div>
              <div>
                <label>End Date</label>
                <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
            </div>
            <div className="row" style={{ marginTop: "12px", alignItems: "center" }}>
              <button className="btn secondary" onClick={handleValidateTicker}>
                Validate Ticker
              </button>
              {tickerValid !== null && (
                <span className="tag">{tickerValid ? "Valid" : "Invalid"}</span>
              )}
            </div>
            <div className="card" style={{ marginTop: "16px" }}>
              <h4>Periodic Contribution</h4>
              <div className="row">
                <div>
                  <label>Enable</label>
                  <select
                    value={contributionEnabled ? "yes" : "no"}
                    onChange={(e) => setContributionEnabled(e.target.value === "yes")}
                  >
                    <option value="no">No</option>
                    <option value="yes">Yes</option>
                  </select>
                </div>
                <div>
                  <label>Amount</label>
                  <input
                    type="number"
                    value={contributionAmount}
                    onChange={(e) => setContributionAmount(e.target.value)}
                    disabled={!contributionEnabled}
                  />
                </div>
                <div>
                  <label>Frequency</label>
                  <select
                    value={contributionFrequency}
                    onChange={(e) =>
                      setContributionFrequency(
                        e.target.value as "daily" | "weekly" | "monthly" | "interval_days"
                      )
                    }
                    disabled={!contributionEnabled}
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="interval_days">Every N Days</option>
                  </select>
                </div>
              </div>
              {contributionFrequency === "interval_days" && (
                <div className="row" style={{ marginTop: "12px" }}>
                  <div>
                    <label>Interval Days</label>
                    <input
                      type="number"
                      value={intervalDays}
                      onChange={(e) => setIntervalDays(e.target.value)}
                      disabled={!contributionEnabled}
                    />
                  </div>
                </div>
              )}
              <div className="row" style={{ marginTop: "12px" }}>
                <div>
                  <label>Include Start Period</label>
                  <select
                    value={includeStart ? "yes" : "no"}
                    onChange={(e) => setIncludeStart(e.target.value === "yes")}
                    disabled={!contributionEnabled}
                  >
                    <option value="no">No</option>
                    <option value="yes">Yes</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="card" style={{ marginTop: "16px" }}>
              <h4>Position Sizing</h4>
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
                      positionSizeType === "percent_capital" ? "Percent (0-100)" :
                      positionSizeType === "fixed_amount" ? "Dollar amount" :
                      positionSizeType === "risk_based" ? "Risk % (e.g., 1)" :
                      "Not used"
                    }
                  />
                </div>
              </div>
            </div>

            <div className="card" style={{ marginTop: "16px" }}>
              <h4>Risk Management</h4>
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
              <div className="row" style={{ marginTop: "12px" }}>
                <div>
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
                </div>
              </div>
              <div className="notice" style={{ marginTop: "12px", fontSize: "0.85rem" }}>
                <strong>Dynamic Stop:</strong> Select an indicator column to use as a trailing stop.
                Takes priority over fixed percentage stops.
              </div>
            </div>

            <div className="card" style={{ marginTop: "16px" }}>
              <h4>Transaction Costs</h4>
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

            {assetClass === "STOCK" && isIntraday && rangeDays > 60 && (
              <p className="notice" style={{ marginTop: "12px" }}>
                Yahoo intraday data is limited to the most recent 60 days. Reduce the date range.
              </p>
            )}
            <div className="row" style={{ justifyContent: "flex-end", marginTop: "16px" }}>
              <button className="btn secondary" onClick={() => setPendingBacktest(false)}>
                Cancel
              </button>
              <button className="btn" onClick={handleSubmit} disabled={submitting}>
                {submitting ? "Submitting..." : "Submit Backtest"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
