from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.attribution import (  # noqa: E402
    StrengthCalculatorRegistry,
    get_indicator_snapshot,
    get_indicators_used_in_conditions,
    calculate_market_return,
)
from app.engine.attribution.calculators.confluence import ConfluenceStrengthCalculator  # noqa: E402


def make_test_df() -> pd.DataFrame:
    """Create test DataFrame with OHLCV and indicator data."""
    index = pd.date_range("2023-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            "high": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
            "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
            "close": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            "volume": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900],
            "rsi_14": [30, 35, 40, 45, 50, 55, 60, 65, 70, 75],
            "sma_50": [100, 100.5, 101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5],
            "macd": [-0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3],
        },
        index=index,
    )
    return df


def test_confluence_strength_calculator():
    """Test ConfluenceStrengthCalculator basic functionality."""
    calc = ConfluenceStrengthCalculator()
    df = make_test_df()

    # Test with 3 conditions met out of 5 total
    conditions_met = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
    all_conditions = [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}, {"id": "5"}]

    strength = calc.calculate(df, 0, conditions_met, all_conditions)
    assert strength == 0.6  # 3/5 = 0.6


def test_confluence_strength_all_conditions_met():
    """Test ConfluenceStrengthCalculator when all conditions met."""
    calc = ConfluenceStrengthCalculator()
    df = make_test_df()

    conditions_met = [{"id": "1"}, {"id": "2"}]
    all_conditions = [{"id": "1"}, {"id": "2"}]

    strength = calc.calculate(df, 0, conditions_met, all_conditions)
    assert strength == 1.0


def test_confluence_strength_no_conditions_met():
    """Test ConfluenceStrengthCalculator when no conditions met."""
    calc = ConfluenceStrengthCalculator()
    df = make_test_df()

    conditions_met = []
    all_conditions = [{"id": "1"}, {"id": "2"}]

    strength = calc.calculate(df, 0, conditions_met, all_conditions)
    assert strength == 0.0


def test_confluence_strength_invalid_data():
    """Test ConfluenceStrengthCalculator with invalid data."""
    calc = ConfluenceStrengthCalculator()
    df = make_test_df()

    # Empty all_conditions (divide by zero protection)
    conditions_met = []
    all_conditions = []

    strength = calc.calculate(df, 0, conditions_met, all_conditions)
    assert strength == 0.5  # Returns 0.5 for empty conditions


def test_calculator_registry():
    """Test StrengthCalculatorRegistry pattern."""
    df = make_test_df()

    # Test default calculator is confluence
    registry = StrengthCalculatorRegistry
    active_calc = registry.get_active()
    assert isinstance(active_calc, ConfluenceStrengthCalculator)

    # Test calculate_strength delegates correctly
    conditions_met = [{"id": "1"}]
    all_conditions = [{"id": "1"}, {"id": "2"}]

    strength = registry.calculate_strength(df, 0, conditions_met, all_conditions)
    assert strength == 0.5


def test_get_indicators_used_in_conditions():
    """Test extraction of indicator aliases from conditions."""
    conditions = [
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "rsi_14",
            "operator": "LT",
            "right_operand_type": "SCALAR",
            "right_operand_value": "30",
        },
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "sma_50",
            "operator": "GT",
            "right_operand_type": "INDICATOR",
            "right_operand_value": "close",
        },
        {
            "left_operand_type": "OHLCV",
            "left_operand_value": "close",
            "operator": "GT",
            "right_operand_type": "SCALAR",
            "right_operand_value": "100",
        },
    ]

    indicators = get_indicators_used_in_conditions(conditions)
    assert "rsi_14" in indicators
    assert "sma_50" in indicators
    assert "close" in indicators
    assert len(indicators) == 3


def test_get_indicators_used_in_conditions_empty():
    """Test with no indicator conditions."""
    conditions = [
        {
            "left_operand_type": "OHLCV",
            "left_operand_value": "close",
            "operator": "GT",
            "right_operand_type": "SCALAR",
            "right_operand_value": "100",
        },
    ]

    indicators = get_indicators_used_in_conditions(conditions)
    # OHLCV is not considered an indicator
    assert len(indicators) == 0


def test_get_indicator_snapshot():
    """Test indicator snapshot extraction from DataFrame."""
    df = make_test_df()
    bar_idx = 5

    indicators = ["rsi_14", "sma_50", "macd"]
    snapshot = get_indicator_snapshot(df, bar_idx, indicators)

    assert snapshot["rsi_14"] == 55
    assert snapshot["sma_50"] == 102.5
    assert snapshot["macd"] == 0.5


def test_get_indicator_snapshot_with_ohlcv():
    """Test indicator snapshot includes OHLCV columns."""
    df = make_test_df()
    bar_idx = 3

    indicators = ["close", "volume", "rsi_14"]
    snapshot = get_indicator_snapshot(df, bar_idx, indicators)

    assert snapshot["close"] == 104
    assert snapshot["volume"] == 1300
    assert snapshot["rsi_14"] == 45


def test_get_indicator_snapshot_missing_column():
    """Test indicator snapshot with missing column."""
    df = make_test_df()
    bar_idx = 2

    indicators = ["rsi_14", "nonexistent_indicator"]
    snapshot = get_indicator_snapshot(df, bar_idx, indicators)

    assert snapshot["rsi_14"] == 40
    assert "nonexistent_indicator" not in snapshot


def test_get_indicator_snapshot_out_of_bounds():
    """Test indicator snapshot with out-of-bounds index."""
    df = make_test_df()

    # Test with negative index
    snapshot = get_indicator_snapshot(df, -1, ["rsi_14"])
    assert snapshot == {}

    # Test with index >= len(df)
    snapshot = get_indicator_snapshot(df, 100, ["rsi_14"])
    assert snapshot == {}


def test_calculate_market_return_long():
    """Test market return calculation for LONG trade."""
    df = make_test_df()
    entry_idx = 0  # close = 101
    exit_idx = 5   # close = 106

    market_return = calculate_market_return(df, entry_idx, exit_idx, "LONG")

    # Market return = (106 - 101) / 101 * 100 = 4.95%
    assert market_return == pytest.approx(4.95, abs=0.01)


def test_calculate_market_return_short():
    """Test market return calculation for SHORT trade."""
    df = make_test_df()
    entry_idx = 0  # close = 101
    exit_idx = 5   # close = 106

    market_return = calculate_market_return(df, entry_idx, exit_idx, "SHORT")

    # Market return = (101 - 106) / 101 * 100 = -4.95%
    assert market_return == pytest.approx(-4.95, abs=0.01)


def test_calculate_market_return_no_change():
    """Test market return when price doesn't change."""
    df = make_test_df()
    entry_idx = 2
    exit_idx = 2  # Same bar

    market_return = calculate_market_return(df, entry_idx, exit_idx, "LONG")
    assert market_return == 0.0


def test_calculate_market_return_negative_long():
    """Test market return calculation for losing LONG trade."""
    df = make_test_df()
    entry_idx = 5  # close = 106
    exit_idx = 0   # close = 101

    market_return = calculate_market_return(df, entry_idx, exit_idx, "LONG")

    # Market return = (101 - 106) / 106 * 100 = -4.72%
    assert market_return == pytest.approx(-4.72, abs=0.01)


def test_calculate_market_return_invalid_direction():
    """Test market return with invalid direction (defaults to LONG)."""
    df = make_test_df()
    entry_idx = 0
    exit_idx = 5

    market_return = calculate_market_return(df, entry_idx, exit_idx, "INVALID")

    # Should default to LONG
    assert market_return == pytest.approx(4.95, abs=0.01)


def test_calculate_market_return_out_of_bounds():
    """Test market return with out-of-bounds indices."""
    df = make_test_df()

    # Invalid entry_idx
    market_return = calculate_market_return(df, -1, 5, "LONG")
    assert market_return == 0.0

    # Invalid exit_idx
    market_return = calculate_market_return(df, 0, 100, "LONG")
    assert market_return == 0.0

    # Both invalid
    market_return = calculate_market_return(df, -1, 100, "LONG")
    assert market_return == 0.0


def test_calculate_market_return_zero_entry_price():
    """Test market return when entry price is zero (edge case)."""
    df = pd.DataFrame({
        "close": [0, 10, 20],
    })

    market_return = calculate_market_return(df, 0, 2, "LONG")
    assert market_return == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
