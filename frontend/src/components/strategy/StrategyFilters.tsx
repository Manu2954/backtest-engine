import { useState, useEffect, useCallback, type ChangeEvent, type CSSProperties } from "react";
import type { IndicatorType } from "../../types";

export type SortOption = "name" | "date" | "complexity";
export type BacktestFilter = "all" | "yes" | "no";

interface StrategyFiltersProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  indicatorTypes: IndicatorType[];
  selectedIndicators: IndicatorType[];
  onIndicatorChange: (indicators: IndicatorType[]) => void;
  backtestFilter: BacktestFilter;
  onBacktestFilterChange: (filter: BacktestFilter) => void;
  sortBy: SortOption;
  onSortChange: (sort: SortOption) => void;
}

const INDICATOR_OPTIONS: IndicatorType[] = [
  "RSI",
  "EMA",
  "SMA",
  "MACD",
  "BB",
  "ATR",
  "STOCH",
  "ADX",
  "ICHIMOKU",
  "ROC",
  "OBV",
];

const filterContainerStyle: CSSProperties = {
  display: "flex",
  gap: "16px",
  flexWrap: "wrap",
  alignItems: "center",
};

const filterGroupStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "4px",
  minWidth: "150px",
};

const searchInputStyle: CSSProperties = {
  width: "220px",
  padding: "10px 12px",
  paddingLeft: "36px",
  borderRadius: "10px",
  border: "1px solid var(--line)",
  fontSize: "0.95rem",
  background: "#fff",
};

const selectStyle: CSSProperties = {
  padding: "10px 12px",
  borderRadius: "10px",
  border: "1px solid var(--line)",
  fontSize: "0.95rem",
  minWidth: "140px",
};

const labelStyle: CSSProperties = {
  fontWeight: 600,
  fontSize: "0.8rem",
  color: "var(--muted)",
};

const multiSelectContainerStyle: CSSProperties = {
  position: "relative",
};

const multiSelectButtonStyle: CSSProperties = {
  padding: "10px 12px",
  borderRadius: "10px",
  border: "1px solid var(--line)",
  fontSize: "0.95rem",
  minWidth: "160px",
  background: "#fff",
  cursor: "pointer",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "8px",
};

const dropdownStyle: CSSProperties = {
  position: "absolute",
  top: "100%",
  left: 0,
  marginTop: "4px",
  background: "#fff",
  border: "1px solid var(--line)",
  borderRadius: "10px",
  boxShadow: "var(--shadow)",
  padding: "8px",
  zIndex: 10,
  maxHeight: "200px",
  overflowY: "auto",
  minWidth: "160px",
};

const checkboxLabelStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  padding: "6px 8px",
  borderRadius: "6px",
  cursor: "pointer",
  fontSize: "0.9rem",
  transition: "background 0.15s",
};

export default function StrategyFilters({
  searchValue,
  onSearchChange,
  selectedIndicators,
  onIndicatorChange,
  backtestFilter,
  onBacktestFilterChange,
  sortBy,
  onSortChange,
}: StrategyFiltersProps) {
  const [indicatorDropdownOpen, setIndicatorDropdownOpen] = useState(false);
  const [debouncedSearch, setDebouncedSearch] = useState(searchValue);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      onSearchChange(debouncedSearch);
    }, 300);
    return () => clearTimeout(timer);
  }, [debouncedSearch, onSearchChange]);

  const handleSearchInput = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setDebouncedSearch(e.target.value);
  }, []);

  const toggleIndicator = useCallback(
    (indicator: IndicatorType) => {
      if (selectedIndicators.includes(indicator)) {
        onIndicatorChange(selectedIndicators.filter((i) => i !== indicator));
      } else {
        onIndicatorChange([...selectedIndicators, indicator]);
      }
    },
    [selectedIndicators, onIndicatorChange]
  );

  const clearIndicators = useCallback(() => {
    onIndicatorChange([]);
  }, [onIndicatorChange]);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!indicatorDropdownOpen) return;
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest("[data-indicator-dropdown]")) {
        setIndicatorDropdownOpen(false);
      }
    };
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, [indicatorDropdownOpen]);

  return (
    <div style={filterContainerStyle}>
      {/* Search */}
      <div style={{ position: "relative" }}>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--muted)"
          strokeWidth="2"
          style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }}
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="text"
          placeholder="Search strategies..."
          value={debouncedSearch}
          onChange={handleSearchInput}
          style={searchInputStyle}
        />
      </div>

      {/* Indicator Type Multi-Select */}
      <div style={filterGroupStyle}>
        <span style={labelStyle}>Indicator Type</span>
        <div style={multiSelectContainerStyle} data-indicator-dropdown>
          <button
            type="button"
            style={multiSelectButtonStyle}
            onClick={() => setIndicatorDropdownOpen(!indicatorDropdownOpen)}
          >
            <span>
              {selectedIndicators.length === 0
                ? "All Types"
                : `${selectedIndicators.length} selected`}
            </span>
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{
                transform: indicatorDropdownOpen ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 0.2s",
              }}
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          {indicatorDropdownOpen && (
            <div style={dropdownStyle}>
              {selectedIndicators.length > 0 && (
                <button
                  type="button"
                  onClick={clearIndicators}
                  style={{
                    ...checkboxLabelStyle,
                    color: "var(--accent)",
                    fontWeight: 600,
                    marginBottom: "4px",
                    border: "none",
                    background: "transparent",
                    width: "100%",
                    textAlign: "left",
                  }}
                >
                  Clear all
                </button>
              )}
              {INDICATOR_OPTIONS.map((indicator) => (
                <label
                  key={indicator}
                  style={{
                    ...checkboxLabelStyle,
                    background: selectedIndicators.includes(indicator)
                      ? "rgba(27, 127, 107, 0.1)"
                      : "transparent",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedIndicators.includes(indicator)}
                    onChange={() => toggleIndicator(indicator)}
                    style={{ accentColor: "var(--accent)" }}
                  />
                  {indicator}
                </label>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Has Backtests Filter */}
      <div style={filterGroupStyle}>
        <span style={labelStyle}>Has Backtests</span>
        <select
          value={backtestFilter}
          onChange={(e) => onBacktestFilterChange(e.target.value as BacktestFilter)}
          style={selectStyle}
        >
          <option value="all">All</option>
          <option value="yes">Yes</option>
          <option value="no">No</option>
        </select>
      </div>

      {/* Sort */}
      <div style={filterGroupStyle}>
        <span style={labelStyle}>Sort By</span>
        <select
          value={sortBy}
          onChange={(e) => onSortChange(e.target.value as SortOption)}
          style={selectStyle}
        >
          <option value="name">Name</option>
          <option value="date">Date Created</option>
          <option value="complexity">Complexity</option>
        </select>
      </div>
    </div>
  );
}
