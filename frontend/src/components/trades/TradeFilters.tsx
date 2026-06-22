import { useState } from "react";
import type { TradeFilters } from "../../types";

interface TradeFiltersProps {
  filters: TradeFilters;
  onFiltersChange: (filters: TradeFilters) => void;
  availableExitReasons: string[];
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export default function TradeFiltersPanel({
  filters,
  onFiltersChange,
  availableExitReasons,
  isCollapsed,
  onToggleCollapse,
}: TradeFiltersProps) {
  const [exitReasonDropdownOpen, setExitReasonDropdownOpen] = useState(false);

  const handleDirectionChange = (direction: "LONG" | "SHORT") => {
    const newDirections = filters.directions.includes(direction)
      ? filters.directions.filter((d) => d !== direction)
      : [...filters.directions, direction];
    onFiltersChange({ ...filters, directions: newDirections });
  };

  const handleResultChange = (result: "all" | "winners" | "losers") => {
    onFiltersChange({ ...filters, result });
  };

  const handleExitReasonToggle = (reason: string) => {
    const newReasons = filters.exitReasons.includes(reason)
      ? filters.exitReasons.filter((r) => r !== reason)
      : [...filters.exitReasons, reason];
    onFiltersChange({ ...filters, exitReasons: newReasons });
  };

  const handleDateChange = (field: "entryDateFrom" | "entryDateTo", value: string) => {
    onFiltersChange({ ...filters, [field]: value });
  };

  const handleClearFilters = () => {
    onFiltersChange({
      directions: [],
      result: "all",
      exitReasons: [],
      entryDateFrom: "",
      entryDateTo: "",
    });
  };

  const hasActiveFilters =
    filters.directions.length > 0 ||
    filters.result !== "all" ||
    filters.exitReasons.length > 0 ||
    filters.entryDateFrom !== "" ||
    filters.entryDateTo !== "";

  return (
    <div className={`filters-panel ${isCollapsed ? "collapsed" : ""}`}>
      <div className="filters-header" onClick={onToggleCollapse}>
        <h3>Filters</h3>
        <button className="btn secondary filter-toggle">
          {isCollapsed ? "Show" : "Hide"}
        </button>
      </div>

      {!isCollapsed && (
        <div className="filters-content">
          {/* Direction Filter */}
          <div className="filter-group">
            <label>Direction</label>
            <div className="checkbox-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={filters.directions.includes("LONG")}
                  onChange={() => handleDirectionChange("LONG")}
                />
                Long
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={filters.directions.includes("SHORT")}
                  onChange={() => handleDirectionChange("SHORT")}
                />
                Short
              </label>
            </div>
          </div>

          {/* Result Filter */}
          <div className="filter-group">
            <label>Result</label>
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  name="result"
                  checked={filters.result === "all"}
                  onChange={() => handleResultChange("all")}
                />
                All
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="result"
                  checked={filters.result === "winners"}
                  onChange={() => handleResultChange("winners")}
                />
                Winners
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="result"
                  checked={filters.result === "losers"}
                  onChange={() => handleResultChange("losers")}
                />
                Losers
              </label>
            </div>
          </div>

          {/* Exit Reason Multi-Select */}
          <div className="filter-group">
            <label>Exit Reason</label>
            <div className="dropdown-container">
              <button
                className="dropdown-trigger btn secondary"
                onClick={() => setExitReasonDropdownOpen(!exitReasonDropdownOpen)}
              >
                {filters.exitReasons.length === 0
                  ? "All Reasons"
                  : `${filters.exitReasons.length} selected`}
              </button>
              {exitReasonDropdownOpen && (
                <div className="dropdown-menu">
                  {availableExitReasons.map((reason) => (
                    <label key={reason} className="dropdown-item">
                      <input
                        type="checkbox"
                        checked={filters.exitReasons.includes(reason)}
                        onChange={() => handleExitReasonToggle(reason)}
                      />
                      {reason}
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Date Range */}
          <div className="filter-group">
            <label>Entry Date From</label>
            <input
              type="date"
              value={filters.entryDateFrom}
              onChange={(e) => handleDateChange("entryDateFrom", e.target.value)}
            />
          </div>

          <div className="filter-group">
            <label>Entry Date To</label>
            <input
              type="date"
              value={filters.entryDateTo}
              onChange={(e) => handleDateChange("entryDateTo", e.target.value)}
            />
          </div>

          {hasActiveFilters && (
            <button className="btn secondary clear-filters" onClick={handleClearFilters}>
              Clear Filters
            </button>
          )}
        </div>
      )}
    </div>
  );
}
