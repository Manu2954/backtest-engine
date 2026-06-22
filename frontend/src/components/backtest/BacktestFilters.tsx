import type { StrategyOut } from "../../types";

export type SortOption = "newest" | "oldest" | "best_return" | "worst_return";
export type StatusFilter = "PENDING" | "RUNNING" | "COMPLETE" | "FAILED";

interface BacktestFiltersProps {
  strategies: StrategyOut[];
  selectedStrategyId: string;
  onStrategyChange: (strategyId: string) => void;
  statusFilters: StatusFilter[];
  onStatusChange: (statuses: StatusFilter[]) => void;
  sortBy: SortOption;
  onSortChange: (sort: SortOption) => void;
}

const allStatuses: StatusFilter[] = ["PENDING", "RUNNING", "COMPLETE", "FAILED"];

export default function BacktestFilters({
  strategies,
  selectedStrategyId,
  onStrategyChange,
  statusFilters,
  onStatusChange,
  sortBy,
  onSortChange,
}: BacktestFiltersProps) {
  const handleStatusToggle = (status: StatusFilter) => {
    if (statusFilters.includes(status)) {
      // Don't allow deselecting all
      if (statusFilters.length > 1) {
        onStatusChange(statusFilters.filter((s) => s !== status));
      }
    } else {
      onStatusChange([...statusFilters, status]);
    }
  };

  const statusColors: Record<StatusFilter, { bg: string; activeBg: string; color: string }> = {
    PENDING: { bg: "#f3efe9", activeBg: "#fff6e8", color: "#b8860b" },
    RUNNING: { bg: "#f3efe9", activeBg: "#e8f4ff", color: "#0066cc" },
    COMPLETE: { bg: "#f3efe9", activeBg: "#e8f5f3", color: "#1b7f6b" },
    FAILED: { bg: "#f3efe9", activeBg: "#ffe8e6", color: "#b42318" },
  };

  return (
    <div
      className="card"
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "16px",
        alignItems: "center",
        padding: "16px 24px",
      }}
    >
      {/* Strategy filter */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <label style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--muted)" }}>
          Strategy:
        </label>
        <select
          value={selectedStrategyId}
          onChange={(e) => onStrategyChange(e.target.value)}
          style={{ minWidth: "160px" }}
        >
          <option value="">All Strategies</option>
          {strategies.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      {/* Status filter checkboxes */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <label style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--muted)" }}>
          Status:
        </label>
        <div style={{ display: "flex", gap: "6px" }}>
          {allStatuses.map((status) => {
            const isActive = statusFilters.includes(status);
            const colors = statusColors[status];
            return (
              <button
                key={status}
                onClick={() => handleStatusToggle(status)}
                style={{
                  padding: "6px 12px",
                  borderRadius: "999px",
                  border: "none",
                  background: isActive ? colors.activeBg : colors.bg,
                  color: isActive ? colors.color : "var(--muted)",
                  fontWeight: isActive ? 600 : 400,
                  fontSize: "0.8rem",
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
              >
                {status}
              </button>
            );
          })}
        </div>
      </div>

      {/* Sort dropdown */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginLeft: "auto" }}>
        <label style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--muted)" }}>
          Sort:
        </label>
        <select
          value={sortBy}
          onChange={(e) => onSortChange(e.target.value as SortOption)}
          style={{ minWidth: "140px" }}
        >
          <option value="newest">Newest First</option>
          <option value="oldest">Oldest First</option>
          <option value="best_return">Best Return</option>
          <option value="worst_return">Worst Return</option>
        </select>
      </div>
    </div>
  );
}
