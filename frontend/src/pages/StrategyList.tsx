import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, createBacktest, deleteStrategy, validateTicker } from "../api/client";
import type { StrategyOut } from "../types";

export default function StrategyList() {
  const [strategies, setStrategies] = useState<StrategyOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<StrategyOut | null>(null);
  const [pendingBacktest, setPendingBacktest] = useState<StrategyOut | null>(null);
  const [ticker, setTicker] = useState("AAPL");
  const [assetClass, setAssetClass] = useState<"STOCK" | "CRYPTO">("STOCK");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2023-12-31");
  const [initialCapital, setInitialCapital] = useState("10000");
  const [resolution, setResolution] = useState("1d");
  const [submitting, setSubmitting] = useState(false);
  const [tickerValid, setTickerValid] = useState<boolean | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .get<StrategyOut[]>("/strategies")
      .then((res) => setStrategies(res.data))
      .catch((err) => setError(err.message || "Failed to load strategies"));
  }, []);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await deleteStrategy(id);
      setStrategies((prev) => prev.filter((s) => s.id !== id));
    } catch (err: any) {
      setError(err.message || "Failed to delete strategy");
    } finally {
      setDeletingId(null);
    }
  };

  const resolutionOptions = useMemo(
    () =>
      assetClass === "CRYPTO"
        ? ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1mo"]
        : ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
    [assetClass]
  );

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

  const handleCreateBacktest = async (strategyId: string) => {
    setSubmitting(true);
    setError(null);
    try {
      const run = await createBacktest({
        strategy_id: strategyId,
        ticker,
        asset_class: assetClass,
        start_date: startDate,
        end_date: endDate,
        bar_resolution: resolution,
        initial_capital: Number(initialCapital),
      });
      setPendingBacktest(null);
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
        <h1>Strategies</h1>
        {error && <div className="notice">{error}</div>}
        <div className="row" style={{ marginBottom: "16px" }}>
          <Link className="btn" to="/strategies/new">
            New Strategy
          </Link>
        </div>
        {strategies.length === 0 ? (
          <p>No strategies yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Indicators</th>
                <th>Conditions</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {strategies.map((strategy) => (
                <tr key={strategy.id}>
                  <td>{strategy.name}</td>
                  <td>{strategy.description || "—"}</td>
                  <td>{strategy.indicators.length}</td>
                  <td>{strategy.condition_groups.length}</td>
                  <td>
                    <Link className="btn secondary" to={`/strategies/${strategy.id}`}>
                      View / Edit
                    </Link>
                    <button
                      className="btn secondary"
                      style={{ marginLeft: "8px" }}
                      onClick={() => setPendingBacktest(strategy)}
                    >
                      Run Backtest
                    </button>
                    <button
                      className="btn warning"
                      style={{ marginLeft: "8px" }}
                      onClick={() => setPendingDelete(strategy)}
                      disabled={deletingId === strategy.id}
                    >
                      {deletingId === strategy.id ? "Deleting..." : "Delete"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {pendingDelete && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>Delete Strategy</h3>
            <p>
              Are you sure you want to delete <strong>{pendingDelete.name}</strong>?
              This cannot be undone.
            </p>
            <div className="row" style={{ justifyContent: "flex-end" }}>
              <button className="btn secondary" onClick={() => setPendingDelete(null)}>
                Cancel
              </button>
              <button
                className="btn warning"
                onClick={() => {
                  handleDelete(pendingDelete.id);
                  setPendingDelete(null);
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
      {pendingBacktest && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>Run Backtest</h3>
            <p>
              Strategy: <strong>{pendingBacktest.name}</strong>
            </p>
            <div className="row" style={{ marginTop: "12px" }}>
              <div>
                <label>Ticker</label>
                <input value={ticker} onChange={(e) => setTicker(e.target.value)} />
              </div>
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
              <div>
                <label>Initial Capital</label>
                <input
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(e.target.value)}
                />
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
            {assetClass === "STOCK" && isIntraday && rangeDays > 60 && (
              <p className="notice" style={{ marginTop: "12px" }}>
                Yahoo intraday data is limited to the most recent 60 days. Reduce the date range.
              </p>
            )}
            <div className="row" style={{ justifyContent: "flex-end", marginTop: "16px" }}>
              <button className="btn secondary" onClick={() => setPendingBacktest(null)}>
                Cancel
              </button>
              <button
                className="btn"
                onClick={() => handleCreateBacktest(pendingBacktest.id)}
                disabled={submitting}
              >
                {submitting ? "Submitting..." : "Submit Backtest"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
