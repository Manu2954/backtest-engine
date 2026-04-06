"""
Unit tests for empirical binning analyzer.

Tests cover:
- Basic quintile binning with valid data
- Insufficient trades (< 50)
- Missing indicator snapshots
- Correlation calculation
- Crossover indicator detection and skipping
- NaN value handling
- Identical values (unbinnable)
- Multiple indicators
- Empty bins (skewed distributions)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.attribution.analysis.binning_analyzer import (
    _compute_bin_stats,
    _is_crossover_indicator,
    analyze_indicator_bins,
)


def make_trade_log(
    pnl: float,
    indicator_snapshot_entry: Dict[str, float] | None = None
) -> Mock:
    """Create a mock TradeLog object."""
    trade = Mock()
    trade.pnl = pnl
    trade.indicator_snapshot_entry = indicator_snapshot_entry
    return trade


def test_quintile_binning_basic() -> None:
    """Test basic quintile binning with positively correlated data."""
    # 100 trades: RSI from 10-90, P&L increases with RSI
    trades = []
    for i in range(100):
        rsi_value = 10 + i * 0.8  # 10, 10.8, 11.6, ..., 89.2
        pnl = (rsi_value - 50) * 10  # Higher RSI = higher P&L
        trades.append(make_trade_log(pnl, {"rsi_14": rsi_value}))

    result = analyze_indicator_bins(trades, ["rsi_14"])

    assert result is not None
    assert "rsi_14" in result
    assert "bins" in result["rsi_14"]
    assert len(result["rsi_14"]["bins"]) == 5  # Quintiles

    # Check correlation is positive and significant
    assert result["rsi_14"]["correlation"] > 0.5
    assert result["rsi_14"]["p_value"] < 0.05

    # Check bins have correct structure
    for bin_data in result["rsi_14"]["bins"]:
        assert "range" in bin_data
        assert "count" in bin_data
        assert "avg_pnl" in bin_data
        assert "win_rate" in bin_data
        assert len(bin_data["range"]) == 2

    # Check summary
    assert result["summary"]["total_indicators"] == 1
    assert result["summary"]["analyzed_indicators"] == 1
    assert result["summary"]["significant_indicators"] == 1
    assert result["summary"]["skipped_indicators"] == []


def test_insufficient_trades() -> None:
    """Test that < 50 trades returns None."""
    trades = [make_trade_log(100.0, {"rsi_14": 50.0}) for _ in range(49)]

    result = analyze_indicator_bins(trades, ["rsi_14"])

    assert result is None


def test_missing_indicator_snapshots() -> None:
    """Test that trades without indicator_snapshot_entry are filtered."""
    # 30 trades with snapshots, 30 without
    trades_with = [make_trade_log(100.0, {"rsi_14": 50.0 + i}) for i in range(30)]
    trades_without = [make_trade_log(100.0, None) for _ in range(30)]

    result = analyze_indicator_bins(trades_with + trades_without, ["rsi_14"])

    # Should return None (only 30 valid trades < 50)
    assert result is None


def test_indicator_not_in_snapshots() -> None:
    """Test that indicator not present in snapshots is skipped."""
    # 60 trades but none have "sma_50"
    trades = [make_trade_log(100.0, {"rsi_14": 50.0 + i}) for i in range(60)]

    result = analyze_indicator_bins(trades, ["rsi_14", "sma_50"])

    assert result is not None
    assert "rsi_14" in result
    assert "sma_50" not in result  # Skipped
    assert result["summary"]["analyzed_indicators"] == 1


def test_all_identical_values() -> None:
    """Test that indicator with all identical values is skipped."""
    # All RSI = 50
    trades = [make_trade_log(100.0 + i, {"rsi_14": 50.0}) for i in range(60)]

    result = analyze_indicator_bins(trades, ["rsi_14"])

    assert result is not None
    assert "rsi_14" not in result  # Skipped
    assert result["summary"]["analyzed_indicators"] == 0


def test_correlation_calculation() -> None:
    """Test Spearman correlation calculation with known data."""
    # Perfect negative correlation: RSI increases, P&L decreases
    trades = []
    for i in range(60):
        rsi_value = 20.0 + i  # 20, 21, 22, ..., 79
        pnl = 100.0 - i * 2  # 100, 98, 96, ..., -18
        trades.append(make_trade_log(pnl, {"rsi_14": rsi_value}))

    result = analyze_indicator_bins(trades, ["rsi_14"])

    assert result is not None
    # Should be strong negative correlation
    assert result["rsi_14"]["correlation"] < -0.9
    assert result["rsi_14"]["p_value"] < 0.05


def test_multiple_indicators() -> None:
    """Test binning multiple indicators independently."""
    trades = []
    for i in range(60):
        trades.append(make_trade_log(
            pnl=i * 10,  # Increasing P&L
            indicator_snapshot_entry={
                "rsi_14": 20.0 + i,  # Positive correlation
                "adx_14": 80.0 - i,  # Negative correlation
                "sma_50": 100.0      # Constant (will be skipped)
            }
        ))

    result = analyze_indicator_bins(trades, ["rsi_14", "adx_14", "sma_50"])

    assert result is not None
    assert "rsi_14" in result
    assert "adx_14" in result
    assert "sma_50" not in result  # Skipped (constant)

    # RSI should have positive correlation
    assert result["rsi_14"]["correlation"] > 0.8

    # ADX should have negative correlation
    assert result["adx_14"]["correlation"] < -0.8

    assert result["summary"]["analyzed_indicators"] == 2


def test_nan_values_filtered() -> None:
    """Test that NaN indicator values are excluded from binning."""
    trades = []
    # 50 valid trades
    for i in range(50):
        trades.append(make_trade_log(i * 10, {"rsi_14": 20.0 + i}))

    # 10 trades with NaN
    for i in range(10):
        trades.append(make_trade_log(i * 10, {"rsi_14": float('nan')}))

    result = analyze_indicator_bins(trades, ["rsi_14"])

    assert result is not None
    assert "rsi_14" in result
    # Sample size should be 50 (NaN excluded)
    assert result["rsi_14"]["sample_size"] == 50


def test_empty_bins_skewed_distribution() -> None:
    """Test handling of skewed distributions that may create empty bins."""
    trades = []
    # 50 trades with RSI in range 10-20 (tight distribution)
    for i in range(50):
        rsi_value = 10.0 + (i % 10)  # Repeats 10-19 five times
        trades.append(make_trade_log(i * 10, {"rsi_14": rsi_value}))

    result = analyze_indicator_bins(trades, ["rsi_14"])

    assert result is not None
    assert "rsi_14" in result

    # Bins may have different counts due to quantile-based edges
    bins = result["rsi_14"]["bins"]
    assert len(bins) >= 2  # May have fewer than 5 bins if values collapse


def test_is_crossover_indicator_true() -> None:
    """Test detection of crossover-only indicators."""
    conditions = [
        {
            "operator": "CROSSES_ABOVE",
            "left_operand_value": "ema_20",
            "right_operand_value": "ema_50"
        },
        {
            "operator": "CROSSES_BELOW",
            "left_operand_value": "ema_20",
            "right_operand_value": "sma_100"
        }
    ]

    # ema_20 appears only in crossover conditions
    assert _is_crossover_indicator("ema_20", conditions) is True


def test_is_crossover_indicator_false() -> None:
    """Test that indicators used in comparisons are not flagged as crossover-only."""
    conditions = [
        {
            "operator": "CROSSES_ABOVE",
            "left_operand_value": "ema_20",
            "right_operand_value": "ema_50"
        },
        {
            "operator": "GT",  # Comparison operator
            "left_operand_value": "rsi_14",
            "right_operand_value": "30"
        },
        {
            "operator": "LT",  # Comparison operator
            "left_operand_value": "ema_20",  # Also used in comparison
            "right_operand_value": "100"
        }
    ]

    # ema_20 used in both crossover AND comparison → not crossover-only
    assert _is_crossover_indicator("ema_20", conditions) is False

    # rsi_14 used only in comparison → not crossover-only
    assert _is_crossover_indicator("rsi_14", conditions) is False


def test_crossover_indicator_skipped() -> None:
    """Test that crossover-only indicators are skipped with warning."""
    trades = []
    for i in range(60):
        trades.append(make_trade_log(
            pnl=i * 10,
            indicator_snapshot_entry={
                "ema_20": 100.0 + i,
                "rsi_14": 50.0 + i
            }
        ))

    conditions = [
        {
            "operator": "CROSSES_ABOVE",
            "left_operand_value": "ema_20",
            "right_operand_value": "ema_50"
        },
        {
            "operator": "GT",
            "left_operand_value": "rsi_14",
            "right_operand_value": "30"
        }
    ]

    result = analyze_indicator_bins(
        trades,
        ["ema_20", "rsi_14"],
        conditions=conditions
    )

    assert result is not None
    assert "ema_20" not in result  # Skipped (crossover-only)
    assert "rsi_14" in result  # Analyzed (comparison)
    assert "ema_20" in result["summary"]["skipped_indicators"]


def test_compute_bin_stats() -> None:
    """Test bin statistics calculation."""
    values = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
    pnls = np.array([100, 150, 50, 200, -50, 300, 100, -100, 250, 400])
    bin_edges = np.array([0, 25, 50, 75, 100])

    bins = _compute_bin_stats(values, pnls, bin_edges)

    assert len(bins) == 4  # 4 bins from 5 edges

    # Bin 0: values 10, 20 → P&Ls 100, 150
    assert bins[0]["range"] == [0, 25]
    assert bins[0]["count"] == 2
    assert bins[0]["avg_pnl"] == 125.0
    assert bins[0]["win_rate"] == 1.0  # Both positive

    # Bin 1: values 30, 40 → P&Ls 50, 200
    assert bins[1]["range"] == [25, 50]
    assert bins[1]["count"] == 2

    # Bin 2: values 50, 60, 70 → P&Ls -50, 300, 100
    assert bins[2]["range"] == [50, 75]
    assert bins[2]["count"] == 3


def test_trade_level_correlation_not_bin_level() -> None:
    """Test that correlation is computed on trade-level data, not bin averages."""
    trades = []
    # Create data where bin averages might differ from trade-level correlation
    np.random.seed(42)
    for i in range(60):
        rsi_value = np.random.uniform(20, 80)
        # Add noise to P&L but maintain correlation
        pnl = rsi_value * 5 + np.random.normal(0, 50)
        trades.append(make_trade_log(pnl, {"rsi_14": rsi_value}))

    result = analyze_indicator_bins(trades, ["rsi_14"])

    assert result is not None
    # Should have trade-level correlation with 60 data points
    assert result["rsi_14"]["sample_size"] == 60

    # Correlation should be computed on 60 trades, not 5 bins
    # (If it were bin-level, sample_size would show 5)


def test_p_value_significance() -> None:
    """Test that p-value correctly identifies significant correlations."""
    # Strong correlation
    trades_strong = []
    for i in range(60):
        rsi_value = 20.0 + i
        pnl = rsi_value * 10  # Perfect linear relationship
        trades_strong.append(make_trade_log(pnl, {"rsi_14": rsi_value}))

    result_strong = analyze_indicator_bins(trades_strong, ["rsi_14"])

    assert result_strong is not None
    assert result_strong["rsi_14"]["p_value"] < 0.05
    assert result_strong["summary"]["significant_indicators"] == 1

    # Weak/no correlation
    trades_weak = []
    np.random.seed(42)
    for i in range(60):
        rsi_value = 20.0 + i
        pnl = np.random.uniform(-100, 100)  # Random P&L
        trades_weak.append(make_trade_log(pnl, {"rsi_14": rsi_value}))

    result_weak = analyze_indicator_bins(trades_weak, ["rsi_14"])

    assert result_weak is not None
    # Should not be significant
    assert result_weak["rsi_14"]["p_value"] > 0.05
    assert result_weak["summary"]["significant_indicators"] == 0


def test_bin_edges_returned() -> None:
    """Test that bin edges are returned and represent quintiles."""
    trades = []
    for i in range(100):
        rsi_value = i  # 0-99
        trades.append(make_trade_log(i * 10, {"rsi_14": float(rsi_value)}))

    result = analyze_indicator_bins(trades, ["rsi_14"])

    assert result is not None
    bin_edges = result["rsi_14"]["bin_edges"]

    # Should have 6 edges for 5 bins
    assert len(bin_edges) == 6

    # First edge should be ~0, last edge should be ~99
    assert bin_edges[0] < 5
    assert bin_edges[-1] > 94

    # Edges should be sorted
    assert bin_edges == sorted(bin_edges)


def test_exact_50_trades() -> None:
    """Test edge case: exactly 50 trades (minimum threshold)."""
    trades = [make_trade_log(i * 10, {"rsi_14": 20.0 + i}) for i in range(50)]

    result = analyze_indicator_bins(trades, ["rsi_14"])

    # Should pass (50 is the minimum)
    assert result is not None
    assert "rsi_14" in result
    assert result["rsi_14"]["sample_size"] == 50
