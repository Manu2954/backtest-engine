import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, createBacktest } from "../api/client";
import type { BacktestCreate, BacktestOut, StrategyOut } from "../types";
import {
  BacktestCard,
  BacktestFilters,
  CreateBacktestWizard,
  type SortOption,
  type StatusFilter,
} from "../components/backtest";

export default function BacktestList() {
  const [runs, setRuns] = useState<BacktestOut[]>([]);
  const [strategies, setStrategies] = useState<StrategyOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [wizardInitialData, setWizardInitialData] = useState<Partial<BacktestCreate> | undefined>();

  // Filters state
  const [filterStrategyId, setFilterStrategyId] = useState("");
  const [statusFilters, setStatusFilters] = useState<StatusFilter[]>(["PENDING", "RUNNING", "COMPLETE", "FAILED"]);
  const [sortBy, setSortBy] = useState<SortOption>("newest");

  // Batch selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const navigate = useNavigate();

  // Create strategy lookup map
  const strategyMap = useMemo(() => {
    const map = new Map<string, StrategyOut>();
    strategies.forEach((s) => map.set(s.id, s));
    return map;
  }, [strategies]);

  // Fetch backtests
  useEffect(() => {
    const fetchBacktests = async () => {
      try {
        const res = await api.get<BacktestOut[]>("/backtests");
        setRuns(res.data);
      } catch (err: any) {
        setError(err.message || "Failed to load backtests");
      }
    };
    fetchBacktests();
  }, []);

  // Fetch strategies
  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const res = await api.get<StrategyOut[]>("/strategies");
        setStrategies(res.data);
      } catch (err: any) {
        setError(err.message || "Failed to load strategies");
      }
    };
    fetchStrategies();
  }, []);

  // Poll for running backtests
  useEffect(() => {
    const hasRunning = runs.some((r) => r.status === "PENDING" || r.status === "RUNNING");
    if (!hasRunning) return;

    const interval = setInterval(async () => {
      try {
        const res = await api.get<BacktestOut[]>("/backtests");
        setRuns(res.data);
      } catch (err) {
        // Silently fail on poll
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [runs]);

  // Filter and sort backtests
  const filteredRuns = useMemo(() => {
    let result = runs.filter((run) => {
      // Strategy filter
      if (filterStrategyId && run.strategy_id !== filterStrategyId) {
        return false;
      }
      // Status filter
      if (!statusFilters.includes(run.status as StatusFilter)) {
        return false;
      }
      return true;
    });

    // Sort
    result.sort((a, b) => {
      switch (sortBy) {
        case "newest":
          return new Date(b.start_date).getTime() - new Date(a.start_date).getTime();
        case "oldest":
          return new Date(a.start_date).getTime() - new Date(b.start_date).getTime();
        case "best_return": {
          const returnA = (a.report?.total_return_pct as number) ?? -Infinity;
          const returnB = (b.report?.total_return_pct as number) ?? -Infinity;
          return returnB - returnA;
        }
        case "worst_return": {
          const returnA = (a.report?.total_return_pct as number) ?? Infinity;
          const returnB = (b.report?.total_return_pct as number) ?? Infinity;
          return returnA - returnB;
        }
        default:
          return 0;
      }
    });

    return result;
  }, [runs, filterStrategyId, statusFilters, sortBy]);

  const handleCreateBacktest = async (payload: BacktestCreate) => {
    const run = await createBacktest(payload);
    setShowWizard(false);
    setWizardInitialData(undefined);
    navigate(`/backtests/${run.id}`);
  };

  const handleRerun = useCallback((backtest: BacktestOut) => {
    setWizardInitialData({
      strategy_id: backtest.strategy_id,
      ticker: backtest.ticker,
      asset_class: backtest.asset_class as "STOCK" | "CRYPTO",
      start_date: backtest.start_date,
      end_date: backtest.end_date,
      bar_resolution: backtest.bar_resolution,
      initial_capital: backtest.initial_capital,
      position_size_type: backtest.position_size_type,
      position_size_value: backtest.position_size_value,
      stop_loss_pct: backtest.stop_loss_pct,
      take_profit_pct: backtest.take_profit_pct,
      dynamic_stop_column: backtest.dynamic_stop_column,
      commission_per_trade: backtest.commission_per_trade,
      commission_pct: backtest.commission_pct,
      slippage_pct: backtest.slippage_pct,
    });
    setShowWizard(true);
  }, []);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await api.delete(`/backtests/${id}`);
      setRuns((prev) => prev.filter((r) => r.id !== id));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } catch (err: any) {
      setError(err.message || "Failed to delete backtest");
    }
  }, []);

  const handleSelectToggle = useCallback((id: string, selected: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (selected) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  }, []);

  const handleSelectAll = () => {
    if (selectedIds.size === filteredRuns.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredRuns.map((r) => r.id)));
    }
  };

  return (
    <div className="container fade-in">
      {/* Header */}
      <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ margin: 0 }}>Backtest Jobs</h1>
          <p style={{ margin: "4px 0 0 0", color: "var(--muted)", fontSize: "0.9rem" }}>
            {filteredRuns.length} of {runs.length} backtests
          </p>
        </div>
        <button className="btn" onClick={() => { setWizardInitialData(undefined); setShowWizard(true); }}>
          New Backtest
        </button>
      </div>

      {error && <div className="notice">{error}</div>}

      {/* Filters */}
      <BacktestFilters
        strategies={strategies}
        selectedStrategyId={filterStrategyId}
        onStrategyChange={setFilterStrategyId}
        statusFilters={statusFilters}
        onStatusChange={setStatusFilters}
        sortBy={sortBy}
        onSortChange={setSortBy}
      />

      {/* Batch selection controls */}
      {filteredRuns.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <button className="btn secondary" style={{ padding: "6px 12px", fontSize: "0.85rem" }} onClick={handleSelectAll}>
            {selectedIds.size === filteredRuns.length ? "Deselect All" : "Select All"}
          </button>
          {selectedIds.size > 0 && (
            <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
              {selectedIds.size} selected
            </span>
          )}
        </div>
      )}

      {/* Card Grid */}
      {filteredRuns.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px" }}>
          <p style={{ color: "var(--muted)", marginBottom: "16px" }}>
            {runs.length === 0 ? "No backtests yet. Create your first backtest to get started." : "No backtests match your filters."}
          </p>
          {runs.length === 0 && (
            <button className="btn" onClick={() => setShowWizard(true)}>
              Create First Backtest
            </button>
          )}
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
            gap: "20px",
          }}
        >
          {filteredRuns.map((run) => (
            <BacktestCard
              key={run.id}
              backtest={run}
              strategy={strategyMap.get(run.strategy_id)}
              onDelete={handleDelete}
              onRerun={handleRerun}
              selected={selectedIds.has(run.id)}
              onSelect={handleSelectToggle}
            />
          ))}
        </div>
      )}

      {/* Wizard modal */}
      {showWizard && (
        <CreateBacktestWizard
          strategies={strategies}
          onSubmit={handleCreateBacktest}
          onClose={() => { setShowWizard(false); setWizardInitialData(undefined); }}
          initialData={wizardInitialData}
        />
      )}
    </div>
  );
}
