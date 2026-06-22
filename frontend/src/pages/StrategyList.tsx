import { useEffect, useMemo, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  createBacktest,
  deleteStrategy,
  validateTicker,
  getStrategies,
  getBacktests,
} from "../api/client";
import type { StrategyOut, BacktestOut, IndicatorType } from "../types";
import StrategyCard from "../components/strategy/StrategyCard";
import StrategyFilters, {
  type SortOption,
  type BacktestFilter,
} from "../components/strategy/StrategyFilters";
import ViewToggle, { type ViewMode } from "../components/shared/ViewToggle";

export default function StrategyList() {
  const [strategies, setStrategies] = useState<StrategyOut[]>([]);
  const [backtests, setBacktests] = useState<BacktestOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<StrategyOut | null>(null);
  const [pendingBacktest, setPendingBacktest] = useState<StrategyOut | null>(null);
  const [ticker, setTicker] = useState("AAPL");
  const [assetClass, setAssetClass] = useState<"STOCK" | "CRYPTO">("STOCK");
  const [provider, setProvider] = useState<string>("");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2023-12-31");
  const [initialCapital, setInitialCapital] = useState("10000");
  const [resolution, setResolution] = useState("1d");
  const [submitting, setSubmitting] = useState(false);
  const [tickerValid, setTickerValid] = useState<boolean | null>(null);

  // Advanced backtest options
  const [positionSizeType, setPositionSizeType] = useState<
    "full_capital" | "percent_capital" | "fixed_amount" | "risk_based"
  >("full_capital");
  const [positionSizeValue, setPositionSizeValue] = useState("100");
  const [stopLossPct, setStopLossPct] = useState("");
  const [takeProfitPct, setTakeProfitPct] = useState("");
  const [dynamicStopColumn, setDynamicStopColumn] = useState("");
  const [commissionPerTrade, setCommissionPerTrade] = useState("0");
  const [commissionPct, setCommissionPct] = useState("0");
  const [slippagePct, setSlippagePct] = useState("0");

  // View and filter state
  const [viewMode, setViewMode] = useState<ViewMode>("card");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIndicators, setSelectedIndicators] = useState<IndicatorType[]>([]);
  const [backtestFilter, setBacktestFilter] = useState<BacktestFilter>("all");
  const [sortBy, setSortBy] = useState<SortOption>("name");

  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([getStrategies(), getBacktests()])
      .then(([strategiesData, backtestsData]) => {
        setStrategies(strategiesData);
        setBacktests(backtestsData);
      })
      .catch((err) => setError(err.message || "Failed to load data"));
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
        ? [
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
            "1mo",
          ]
        : ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
    [assetClass]
  );

  // Get indicator aliases from pending strategy for dynamic stop dropdown
  const indicatorAliases = useMemo(() => {
    if (!pendingBacktest) return [];
    return pendingBacktest.indicators.map((ind) => ind.alias);
  }, [pendingBacktest]);

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
        provider: provider || undefined,
        start_date: startDate,
        end_date: endDate,
        bar_resolution: resolution,
        initial_capital: Number(initialCapital),
        position_size_type: positionSizeType,
        position_size_value: Number(positionSizeValue),
        stop_loss_pct: stopLossPct ? Number(stopLossPct) : null,
        take_profit_pct: takeProfitPct ? Number(takeProfitPct) : null,
        dynamic_stop_column: dynamicStopColumn || null,
        commission_per_trade: Number(commissionPerTrade),
        commission_pct: Number(commissionPct),
        slippage_pct: Number(slippagePct),
      });
      setPendingBacktest(null);
      navigate(`/backtests/${run.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create backtest");
    } finally {
      setSubmitting(false);
    }
  };

  // Get backtests for a specific strategy
  const getBacktestsForStrategy = useCallback(
    (strategyId: string) => {
      return backtests.filter((b) => b.strategy_id === strategyId);
    },
    [backtests]
  );

  // Get all indicator types used across strategies
  const allIndicatorTypes = useMemo(() => {
    const types = new Set<IndicatorType>();
    strategies.forEach((s) => {
      s.indicators.forEach((ind) => types.add(ind.indicator_type));
    });
    return Array.from(types);
  }, [strategies]);

  // Filter and sort strategies
  const filteredStrategies = useMemo(() => {
    let result = [...strategies];

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (s) =>
          s.name.toLowerCase().includes(query) ||
          (s.description && s.description.toLowerCase().includes(query))
      );
    }

    // Indicator type filter
    if (selectedIndicators.length > 0) {
      result = result.filter((s) =>
        selectedIndicators.some((ind) =>
          s.indicators.some((indicator) => indicator.indicator_type === ind)
        )
      );
    }

    // Backtest filter
    if (backtestFilter !== "all") {
      result = result.filter((s) => {
        const hasBacktests = backtests.some((b) => b.strategy_id === s.id);
        return backtestFilter === "yes" ? hasBacktests : !hasBacktests;
      });
    }

    // Sort
    result.sort((a, b) => {
      switch (sortBy) {
        case "name":
          return a.name.localeCompare(b.name);
        case "date":
          // Assuming newer strategies have later IDs (UUIDs are time-based in many implementations)
          return b.id.localeCompare(a.id);
        case "complexity":
          const complexityA = a.indicators.length + a.condition_groups.length;
          const complexityB = b.indicators.length + b.condition_groups.length;
          return complexityB - complexityA;
        default:
          return 0;
      }
    });

    return result;
  }, [strategies, searchQuery, selectedIndicators, backtestFilter, sortBy, backtests]);

  return (
    <div className="container fade-in">
      <div className="card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "20px",
          }}
        >
          <h1 style={{ margin: 0 }}>Strategies</h1>
          <Link className="btn" to="/strategies/new">
            New Strategy
          </Link>
        </div>
        {error && <div className="notice" style={{ marginBottom: "16px" }}>{error}</div>}

        {/* Toolbar */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            gap: "16px",
            flexWrap: "wrap",
            marginBottom: "20px",
            paddingBottom: "16px",
            borderBottom: "1px solid var(--line)",
          }}
        >
          <StrategyFilters
            searchValue={searchQuery}
            onSearchChange={setSearchQuery}
            indicatorTypes={allIndicatorTypes}
            selectedIndicators={selectedIndicators}
            onIndicatorChange={setSelectedIndicators}
            backtestFilter={backtestFilter}
            onBacktestFilterChange={setBacktestFilter}
            sortBy={sortBy}
            onSortChange={setSortBy}
          />
          <ViewToggle value={viewMode} onChange={setViewMode} />
        </div>

        {/* Results count */}
        <div
          style={{
            fontSize: "0.9rem",
            color: "var(--muted)",
            marginBottom: "16px",
          }}
        >
          {filteredStrategies.length} strateg{filteredStrategies.length === 1 ? "y" : "ies"} found
        </div>

        {filteredStrategies.length === 0 ? (
          <p style={{ textAlign: "center", color: "var(--muted)", padding: "40px 0" }}>
            {strategies.length === 0 ? "No strategies yet." : "No strategies match your filters."}
          </p>
        ) : viewMode === "card" ? (
          /* Card Grid View */
          <div className="strategy-grid">
            {filteredStrategies.map((strategy) => (
              <StrategyCard
                key={strategy.id}
                strategy={strategy}
                backtests={getBacktestsForStrategy(strategy.id)}
                onRunBacktest={setPendingBacktest}
                onDelete={setPendingDelete}
                isDeleting={deletingId === strategy.id}
              />
            ))}
          </div>
        ) : (
          /* Table View */
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Indicators</th>
                <th>Conditions</th>
                <th>Backtests</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredStrategies.map((strategy) => {
                const strategyBacktests = getBacktestsForStrategy(strategy.id);
                return (
                  <tr key={strategy.id}>
                    <td>{strategy.name}</td>
                    <td
                      style={{
                        maxWidth: "200px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {strategy.description || "—"}
                    </td>
                    <td>{strategy.indicators.length}</td>
                    <td>{strategy.condition_groups.length}</td>
                    <td>{strategyBacktests.length}</td>
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
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {pendingDelete && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>Delete Strategy</h3>
            <p>
              Are you sure you want to delete <strong>{pendingDelete.name}</strong>? This cannot be
              undone.
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

      {/* Run Backtest Modal */}
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
                <label>Data Provider</label>
                <select value={provider} onChange={(e) => setProvider(e.target.value)}>
                  <option value="">Auto (default)</option>
                  <option value="yfinance">Yahoo Finance</option>
                  <option value="binance">Binance</option>
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
            <div className="notice" style={{ marginTop: "8px", fontSize: "0.85rem" }}>
              <strong>Data Provider:</strong> Leave as "Auto" to use yfinance for stocks and binance
              for crypto.
            </div>
            <div className="row" style={{ marginTop: "12px" }}>
              <div>
                <label>Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
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
