import { useEffect, useState, useMemo, useCallback } from "react";
import { useParams } from "react-router-dom";
import { getBacktestTrades } from "../api/client";
import { exportTradesToCSV } from "../lib/exportTrades";
import type { TradeLog, TradeFilters, SortField, SortDirection } from "../types";
import TradeTable from "../components/trades/TradeTable";
import TradeFiltersPanel from "../components/trades/TradeFilters";
import TradeDetailModal from "../components/trades/TradeDetailModal";
import PnLHistogram from "../components/trades/PnLHistogram";
import CumulativePnLChart from "../components/trades/CumulativePnLChart";
import TradeCard from "../components/trades/TradeCard";

const FETCH_LIMIT = 10000;

export default function TradeLogPage() {
  const { id } = useParams();
  const [allTrades, setAllTrades] = useState<TradeLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filters, setFilters] = useState<TradeFilters>({
    directions: [],
    result: "all",
    exitReasons: [],
    entryDateFrom: "",
    entryDateTo: "",
  });
  const [filtersCollapsed, setFiltersCollapsed] = useState(false);

  // Sorting
  const [sortField, setSortField] = useState<SortField>("entry_date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  // Modal
  const [selectedTrade, setSelectedTrade] = useState<TradeLog | null>(null);
  const [selectedTradeIndex, setSelectedTradeIndex] = useState<number>(0);

  // Responsive
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getBacktestTrades(id, FETCH_LIMIT, 0)
      .then((trades) => {
        // Add default direction if not present
        const normalizedTrades = trades.map((t) => ({
          ...t,
          direction: t.direction || "LONG",
        }));
        setAllTrades(normalizedTrades as TradeLog[]);
        setError(null);
      })
      .catch((err) => setError(err.message || "Failed to load trades"))
      .finally(() => setLoading(false));
  }, [id]);

  // Get unique exit reasons for filter dropdown
  const availableExitReasons = useMemo(() => {
    const reasons = new Set(allTrades.map((t) => t.exit_reason).filter(Boolean) as string[]);
    return Array.from(reasons).sort();
  }, [allTrades]);

  // Apply filters
  const filteredTrades = useMemo(() => {
    return allTrades.filter((trade) => {
      // Direction filter
      if (filters.directions.length > 0 && !filters.directions.includes(trade.direction || "LONG")) {
        return false;
      }

      // Result filter
      if (filters.result === "winners" && trade.pnl <= 0) return false;
      if (filters.result === "losers" && trade.pnl > 0) return false;

      // Exit reason filter
      if (filters.exitReasons.length > 0 && !filters.exitReasons.includes(trade.exit_reason || "")) {
        return false;
      }

      // Date range filter
      if (filters.entryDateFrom) {
        const entryDate = trade.entry_date.split("T")[0];
        if (entryDate < filters.entryDateFrom) return false;
      }
      if (filters.entryDateTo) {
        const entryDate = trade.entry_date.split("T")[0];
        if (entryDate > filters.entryDateTo) return false;
      }

      return true;
    });
  }, [allTrades, filters]);

  // Apply sorting
  const sortedTrades = useMemo(() => {
    const sorted = [...filteredTrades];
    sorted.sort((a, b) => {
      let aVal: number | string;
      let bVal: number | string;

      switch (sortField) {
        case "entry_date":
          aVal = new Date(a.entry_date).getTime();
          bVal = new Date(b.entry_date).getTime();
          break;
        case "exit_date":
          aVal = new Date(a.exit_date).getTime();
          bVal = new Date(b.exit_date).getTime();
          break;
        case "pnl":
          aVal = a.pnl;
          bVal = b.pnl;
          break;
        case "shares":
          aVal = a.shares;
          bVal = b.shares;
          break;
        case "trade_duration_days":
          aVal = a.trade_duration_days;
          bVal = b.trade_duration_days;
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [filteredTrades, sortField, sortDirection]);

  const handleSort = useCallback((field: SortField) => {
    setSortField((prev) => {
      if (prev === field) {
        setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
        return field;
      }
      setSortDirection("asc");
      return field;
    });
  }, []);

  const handleRowClick = useCallback((trade: TradeLog) => {
    const index = sortedTrades.findIndex((t) => t.id === trade.id);
    setSelectedTradeIndex(index + 1);
    setSelectedTrade(trade);
  }, [sortedTrades]);

  const handleExportCSV = useCallback(() => {
    exportTradesToCSV(sortedTrades, `trades-${id}.csv`);
  }, [sortedTrades, id]);

  // Stats
  const stats = useMemo(() => {
    if (filteredTrades.length === 0) {
      return { totalTrades: 0, winners: 0, losers: 0, totalPnl: 0, avgPnl: 0 };
    }
    const winners = filteredTrades.filter((t) => t.pnl > 0).length;
    const losers = filteredTrades.filter((t) => t.pnl <= 0).length;
    const totalPnl = filteredTrades.reduce((sum, t) => sum + t.pnl, 0);
    return {
      totalTrades: filteredTrades.length,
      winners,
      losers,
      totalPnl,
      avgPnl: totalPnl / filteredTrades.length,
    };
  }, [filteredTrades]);

  if (!id) {
    return <div className="container">Missing backtest id.</div>;
  }

  return (
    <div className="container fade-in trade-log-page">
      {/* Header */}
      <div className="card page-header">
        <div className="header-row">
          <h1>Trade Log</h1>
          <button className="btn secondary" onClick={handleExportCSV} disabled={sortedTrades.length === 0}>
            Export CSV
          </button>
        </div>
        {error && <div className="notice">{error}</div>}
      </div>

      {/* Charts Row */}
      {!loading && filteredTrades.length > 0 && (
        <div className="charts-row">
          <PnLHistogram trades={filteredTrades} />
          <CumulativePnLChart trades={filteredTrades} />
        </div>
      )}

      {/* Stats Bar */}
      {!loading && (
        <div className="stats-bar card">
          <div className="stat-item">
            <span className="stat-label">Total Trades</span>
            <span className="stat-value">{stats.totalTrades}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Winners</span>
            <span className="stat-value" style={{ color: "var(--accent)" }}>
              {stats.winners}
            </span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Losers</span>
            <span className="stat-value" style={{ color: "var(--danger)" }}>
              {stats.losers}
            </span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Total P&L</span>
            <span
              className="stat-value"
              style={{ color: stats.totalPnl >= 0 ? "var(--accent)" : "var(--danger)" }}
            >
              ${stats.totalPnl.toFixed(2)}
            </span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Avg P&L</span>
            <span
              className="stat-value"
              style={{ color: stats.avgPnl >= 0 ? "var(--accent)" : "var(--danger)" }}
            >
              ${stats.avgPnl.toFixed(2)}
            </span>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="trade-log-content">
        {/* Filters Panel */}
        <TradeFiltersPanel
          filters={filters}
          onFiltersChange={setFilters}
          availableExitReasons={availableExitReasons}
          isCollapsed={filtersCollapsed}
          onToggleCollapse={() => setFiltersCollapsed(!filtersCollapsed)}
        />

        {/* Table / Cards */}
        <div className="trades-list-container card">
          {loading ? (
            <div className="loading-container">
              <div className="spinner" />
              <span>Loading trades...</span>
            </div>
          ) : sortedTrades.length === 0 ? (
            <div className="empty-state">
              {allTrades.length === 0
                ? "No trades found for this backtest."
                : "No trades match the current filters."}
            </div>
          ) : isMobile ? (
            <div className="trade-cards-grid">
              {sortedTrades.map((trade, index) => (
                <TradeCard
                  key={trade.id}
                  trade={trade}
                  tradeNumber={index + 1}
                  onClick={() => handleRowClick(trade)}
                />
              ))}
            </div>
          ) : (
            <TradeTable
              trades={sortedTrades}
              sortField={sortField}
              sortDirection={sortDirection}
              onSort={handleSort}
              onRowClick={handleRowClick}
            />
          )}
        </div>
      </div>

      {/* Detail Modal */}
      {selectedTrade && (
        <TradeDetailModal
          trade={selectedTrade}
          tradeNumber={selectedTradeIndex}
          onClose={() => setSelectedTrade(null)}
        />
      )}
    </div>
  );
}
