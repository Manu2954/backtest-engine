"""
Unit tests for multi-column indicator base alias mapping in condition_engine.

Tests that base aliases (e.g., "macd_2") are automatically mapped to their
primary sub-columns (e.g., "macd_2_macd") when evaluating conditions.
"""

import pandas as pd
import pytest

from app.engine.condition_engine import evaluate_conditions


def test_macd_base_alias_mapping():
    """Test that MACD base alias maps to _macd sub-column."""
    df = pd.DataFrame({
        "close": [100, 102, 101, 103, 104],
        "macd_12_macd": [1.0, 1.5, 1.2, 1.8, 2.0],
        "macd_12_signal": [0.8, 1.0, 1.0, 1.3, 1.6],
        "macd_12_hist": [0.2, 0.5, 0.2, 0.5, 0.4],
    })

    # Reference base alias "macd_12" which should map to "macd_12_macd"
    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "macd_12",  # Base alias
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "1.0",
            }
        ],
    }

    result = evaluate_conditions(df, condition_group)

    # Should use macd_12_macd column (values: 1.0, 1.5, 1.2, 1.8, 2.0)
    # GT 1.0 -> False, True, True, True, True
    expected = pd.Series([False, True, True, True, True])
    pd.testing.assert_series_equal(result.reset_index(drop=True), expected, check_names=False)


def test_bb_base_alias_mapping():
    """Test that BB base alias maps to _mid sub-column."""
    df = pd.DataFrame({
        "close": [100, 102, 101, 103, 104],
        "bb_20_upper": [105, 107, 106, 108, 109],
        "bb_20_mid": [100, 102, 101, 103, 104],
        "bb_20_lower": [95, 97, 96, 98, 99],
    })

    # Reference base alias "bb_20" which should map to "bb_20_mid"
    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "bb_20",  # Base alias
            }
        ],
    }

    result = evaluate_conditions(df, condition_group)

    # close == bb_20_mid, so GT should be all False
    expected = pd.Series([False, False, False, False, False])
    pd.testing.assert_series_equal(result.reset_index(drop=True), expected, check_names=False)


def test_stoch_base_alias_mapping():
    """Test that STOCH base alias maps to _k sub-column."""
    df = pd.DataFrame({
        "close": [100, 102, 101, 103, 104],
        "stoch_14_k": [30, 45, 50, 70, 80],
        "stoch_14_d": [35, 40, 48, 65, 75],
    })

    # Reference base alias "stoch_14" which should map to "stoch_14_k"
    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "stoch_14",  # Base alias
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "50",
            }
        ],
    }

    result = evaluate_conditions(df, condition_group)

    # stoch_14_k > 50: False, False, False, True, True
    expected = pd.Series([False, False, False, True, True])
    pd.testing.assert_series_equal(result.reset_index(drop=True), expected, check_names=False)


def test_ichimoku_base_alias_mapping():
    """Test that ICHIMOKU base alias maps to _tenkan sub-column."""
    df = pd.DataFrame({
        "close": [100, 102, 101, 103, 104],
        "ichi_tenkan": [99, 101, 100, 102, 103],
        "ichi_kijun": [98, 100, 99, 101, 102],
        "ichi_span_a": [98.5, 100.5, 99.5, 101.5, 102.5],
        "ichi_span_b": [97, 99, 98, 100, 101],
        "ichi_chikou": [100, 102, 101, 103, 104],
    })

    # Reference base alias "ichi" which should map to "ichi_tenkan"
    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "ichi",  # Base alias
            }
        ],
    }

    result = evaluate_conditions(df, condition_group)

    # close > ichi_tenkan: (100>99, 102>101, 101>100, 103>102, 104>103)
    # All True
    expected = pd.Series([True, True, True, True, True])
    pd.testing.assert_series_equal(result.reset_index(drop=True), expected, check_names=False)


def test_adx_base_alias_exists():
    """Test that ADX base alias exists directly (no mapping needed)."""
    df = pd.DataFrame({
        "close": [100, 102, 101, 103, 104],
        "adx_14": [20, 25, 30, 35, 40],
        "adx_14_dmp": [15, 20, 25, 30, 35],
        "adx_14_dmn": [10, 15, 20, 25, 30],
    })

    # Reference base alias "adx_14" which exists directly
    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "adx_14",  # Base alias exists
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "25",
            }
        ],
    }

    result = evaluate_conditions(df, condition_group)

    # adx_14 > 25: False, False, True, True, True
    expected = pd.Series([False, False, True, True, True])
    pd.testing.assert_series_equal(result.reset_index(drop=True), expected, check_names=False)


def test_macd_base_alias_in_lookback():
    """Test that MACD base alias mapping works in LOOKBACK operands."""
    df = pd.DataFrame({
        "close": [100, 102, 101, 103, 104],
        "macd_12_macd": [1.0, 1.5, 1.2, 1.8, 2.0],
        "macd_12_signal": [0.8, 1.0, 1.0, 1.3, 1.6],
        "macd_12_hist": [0.2, 0.5, 0.2, 0.5, 0.4],
    })

    # Reference base alias "macd_12" in LOOKBACK
    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "macd_12",  # Base alias
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "macd_12:-1",  # Base alias in lookback
            }
        ],
    }

    result = evaluate_conditions(df, condition_group)

    # macd_12_macd: [1.0, 1.5, 1.2, 1.8, 2.0]
    # macd_12_macd shifted by 1: [NaN, 1.0, 1.5, 1.2, 1.8]
    # Current > Previous: False, True, False, True, True
    expected = pd.Series([False, True, False, True, True])
    pd.testing.assert_series_equal(result.reset_index(drop=True), expected, check_names=False)


def test_explicit_subcolumn_still_works():
    """Test that explicit sub-column references still work correctly."""
    df = pd.DataFrame({
        "close": [100, 102, 101, 103, 104],
        "macd_12_macd": [1.0, 1.5, 1.2, 1.8, 2.0],
        "macd_12_signal": [0.8, 1.0, 1.0, 1.3, 1.6],
        "macd_12_hist": [0.2, 0.5, 0.2, 0.5, 0.4],
    })

    # Explicitly reference "macd_12_signal" (not base alias)
    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "macd_12_signal",  # Explicit sub-column
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "1.0",
            }
        ],
    }

    result = evaluate_conditions(df, condition_group)

    # macd_12_signal > 1.0: False, False, False, True, True
    expected = pd.Series([False, False, False, True, True])
    pd.testing.assert_series_equal(result.reset_index(drop=True), expected, check_names=False)


def test_invalid_alias_still_raises_error():
    """Test that truly invalid aliases still raise ValueError."""
    df = pd.DataFrame({
        "close": [100, 102, 101, 103, 104],
        "rsi_14": [30, 45, 50, 70, 80],
    })

    # Reference non-existent indicator "nonexistent"
    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "nonexistent",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "50",
            }
        ],
    }

    with pytest.raises(ValueError, match="Operand column not found: nonexistent"):
        evaluate_conditions(df, condition_group)


def test_macd_crosses_above_with_base_alias():
    """Test CROSSES_ABOVE operator with MACD base alias mapping."""
    df = pd.DataFrame({
        "close": [100, 102, 101, 103, 104],
        "macd_12_macd": [0.5, 0.8, 1.2, 1.5, 1.8],
        "macd_12_signal": [0.8, 0.9, 1.0, 1.3, 1.6],
        "macd_12_hist": [-0.3, -0.1, 0.2, 0.2, 0.2],
    })

    # MACD crosses above signal line (using base aliases)
    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "macd_12",  # Maps to macd_12_macd
                "operator": "CROSSES_ABOVE",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "macd_12_signal",  # Explicit
            }
        ],
    }

    result = evaluate_conditions(df, condition_group)

    # Index 0: false (no previous)
    # Index 1: 0.8 > 0.9? No
    # Index 2: 1.2 > 1.0 and 0.8 < 0.9? Yes (CROSS!)
    # Index 3: 1.5 > 1.3 and 1.2 > 1.0? No (already above)
    # Index 4: 1.8 > 1.6 and 1.5 > 1.3? No (already above)
    expected = pd.Series([False, False, True, False, False])
    pd.testing.assert_series_equal(result.reset_index(drop=True), expected, check_names=False)


def test_bb_base_alias_with_upper_lower():
    """Test BB base alias vs explicit upper/lower comparisons."""
    df = pd.DataFrame({
        "close": [100, 102, 108, 103, 99],
        "bb_20_upper": [105, 107, 106, 108, 109],
        "bb_20_mid": [100, 102, 101, 103, 104],
        "bb_20_lower": [95, 97, 96, 98, 99],
    })

    # Close crosses above upper band
    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "bb_20_upper",  # Explicit
            }
        ],
    }

    result = evaluate_conditions(df, condition_group)

    # close > bb_20_upper: (100>105, 102>107, 108>106, 103>108, 99>109)
    # False, False, True, False, False
    expected = pd.Series([False, False, True, False, False])
    pd.testing.assert_series_equal(result.reset_index(drop=True), expected, check_names=False)
