"""
Empirical Binning Analyzer

This module provides post-backtest analysis to determine which indicator value
ranges correlate with profitable trades. Unlike Phase 1B's approach (arbitrary
thresholds like RSI < 30), this uses data-driven quintile binning.

Key Concepts:
- Bin indicator values by quintiles (5 bins)
- Calculate avg P&L per bin
- Compute trade-level Spearman correlation (indicator value vs P&L)
- Identify which indicators are predictive of outcomes

Limitations:
- Requires 50+ trades for statistical validity
- Only analyzes entry snapshots (exit values are post-hoc)
- Skips crossover conditions (binary signals, not continuous values)
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def _is_crossover_indicator(
    indicator_alias: str,
    conditions: List[Dict[str, Any]]
) -> bool:
    """
    Check if an indicator is used ONLY in crossover conditions.

    Crossover conditions (CROSSES_ABOVE, CROSSES_BELOW) produce binary signals,
    not continuous values, so they're not suitable for binning analysis.

    Args:
        indicator_alias: Indicator alias (e.g., "rsi_14")
        conditions: List of condition dicts from strategy

    Returns:
        True if indicator appears ONLY in crossover conditions
    """
    crossover_operators = {"CROSSES_ABOVE", "CROSSES_BELOW"}
    comparison_operators = {"GT", "LT", "EQ", "GTE", "LTE", "IS_RISING", "IS_FALLING"}

    uses_crossover = False
    uses_comparison = False

    for cond in conditions:
        operator = cond.get("operator", "")
        left_operand = cond.get("left_operand_value", "")
        right_operand = cond.get("right_operand_value", "")

        # Check if this condition uses the indicator
        if indicator_alias in [left_operand, right_operand]:
            if operator in crossover_operators:
                uses_crossover = True
            elif operator in comparison_operators:
                uses_comparison = True

    # Only return True if used in crossover but NOT in comparison
    return uses_crossover and not uses_comparison


def _compute_bin_stats(
    values: np.ndarray,
    pnls: np.ndarray,
    bin_edges: np.ndarray
) -> List[Dict[str, Any]]:
    """
    Compute statistics for each bin.

    Args:
        values: Indicator values for each trade
        pnls: P&L values for each trade
        bin_edges: Bin boundaries (e.g., [0, 20, 40, 60, 80, 100])

    Returns:
        List of bin stat dicts with keys: range, count, avg_pnl, win_rate
    """
    bins = []
    n_bins = len(bin_edges) - 1

    for i in range(n_bins):
        bin_min = bin_edges[i]
        bin_max = bin_edges[i + 1]

        # Include right edge on last bin, otherwise exclude it
        if i == n_bins - 1:
            mask = (values >= bin_min) & (values <= bin_max)
        else:
            mask = (values >= bin_min) & (values < bin_max)

        bin_pnls = pnls[mask]
        count = len(bin_pnls)

        if count > 0:
            avg_pnl = float(np.mean(bin_pnls))
            win_rate = float(np.sum(bin_pnls > 0) / count)
        else:
            avg_pnl = 0.0
            win_rate = 0.0

        bins.append({
            "range": [float(bin_min), float(bin_max)],
            "count": int(count),
            "avg_pnl": avg_pnl,
            "win_rate": win_rate
        })

    return bins


def analyze_indicator_bins(
    trades: List[Any],
    indicators: List[str],
    conditions: Optional[List[Dict[str, Any]]] = None,
    n_bins: int = 5
) -> Dict[str, Any]:
    """
    Bin each indicator's entry values and calculate avg P&L per bin.

    This is a diagnostic tool to validate which indicators predict outcomes.
    Unlike Phase 1B (arbitrary thresholds), this learns from actual data.

    Args:
        trades: List of TradeLog objects with indicator_snapshot_entry
        indicators: List of indicator aliases to analyze (e.g., ["rsi_14", "sma_50"])
        conditions: Optional list of condition dicts (for crossover detection)
        n_bins: Number of bins (default 5 = quintiles)

    Returns:
        {
            "indicator_alias": {
                "bins": [
                    {"range": [0, 20], "count": 30, "avg_pnl": 250.0, "win_rate": 0.67},
                    ...
                ],
                "bin_edges": [0, 20, 40, 60, 80, 100],
                "correlation": 0.72,  # Spearman correlation (trade-level)
                "p_value": 0.001,     # Statistical significance
                "sample_size": 100    # Number of trades with this indicator
            },
            "summary": {
                "total_indicators": 5,
                "significant_indicators": 2,  # count with p < 0.05
                "skipped_indicators": ["ema_cross"],  # Crossover-only indicators
                "insufficient_data": False
            }
        }

        Returns None if insufficient data (< 50 trades with snapshots).
    """
    # Filter trades with indicator snapshots
    valid_trades = [t for t in trades if t.indicator_snapshot_entry is not None]

    if len(valid_trades) < 50:
        return None

    result = {}
    skipped_indicators = []
    significant_count = 0

    for indicator_alias in indicators:
        # Check if this is a crossover-only indicator
        if conditions and _is_crossover_indicator(indicator_alias, conditions):
            skipped_indicators.append(indicator_alias)
            continue

        # Collect indicator values and P&L for trades that have this indicator
        values = []
        pnls = []

        for trade in valid_trades:
            snapshot = trade.indicator_snapshot_entry
            if indicator_alias in snapshot:
                value = snapshot[indicator_alias]

                # Skip NaN values
                if value is not None and not (isinstance(value, float) and np.isnan(value)):
                    values.append(float(value))
                    pnls.append(float(trade.pnl))

        # Need at least 50 trades for this indicator
        if len(values) < 50:
            continue

        values = np.array(values)
        pnls = np.array(pnls)

        # Check if all values are identical (can't bin)
        if np.all(values == values[0]):
            continue

        # Compute quintile bin edges
        bin_edges = np.quantile(values, np.linspace(0, 1, n_bins + 1))

        # Ensure bin edges are unique (handles cases with repeated values)
        bin_edges = np.unique(bin_edges)
        if len(bin_edges) < 2:
            continue

        # Compute bin statistics
        bins = _compute_bin_stats(values, pnls, bin_edges)

        # Compute trade-level Spearman correlation
        correlation, p_value = spearmanr(values, pnls)

        # Check for NaN (happens if one array is constant)
        if np.isnan(correlation):
            correlation = 0.0
            p_value = 1.0

        # Count as significant if p < 0.05
        if p_value < 0.05:
            significant_count += 1

        result[indicator_alias] = {
            "bins": bins,
            "bin_edges": bin_edges.tolist(),
            "correlation": float(correlation),
            "p_value": float(p_value),
            "sample_size": len(values)
        }

    # Count analyzed indicators before adding summary
    analyzed_count = len(result)

    # Add summary
    result["summary"] = {
        "total_indicators": len(indicators),
        "analyzed_indicators": analyzed_count,
        "significant_indicators": significant_count,
        "skipped_indicators": skipped_indicators,
        "insufficient_data": False
    }

    return result
