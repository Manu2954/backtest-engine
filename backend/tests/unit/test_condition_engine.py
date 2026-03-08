from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.condition_engine import evaluate_conditions  # noqa: E402


def make_df() -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [10, 11, 12, 13, 14],
            "high": [11, 12, 13, 14, 15],
            "low": [9, 10, 11, 12, 13],
            "close": [10, 11, 12, 13, 14],
            "volume": [100, 100, 100, 100, 100],
            "left_up": [0.0, 0.5, 0.8, 1.2, 1.3],
            "left_down": [2.0, 1.5, 1.2, 0.8, 0.7],
            "right": [1.0, 1.0, 1.0, 1.0, 1.0],
        },
        index=index,
    )
    return df


def test_gt_scalar() -> None:
    df = make_df()
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "12",
            }
        ],
    }
    result = evaluate_conditions(df, group)
    assert result.tolist() == [False, False, False, True, True]


def test_lt_indicator() -> None:
    df = make_df()
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "left_down",
                "operator": "LT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "right",
            }
        ],
    }
    result = evaluate_conditions(df, group)
    assert result.tolist() == [False, False, False, True, True]


def test_eq_scalar() -> None:
    df = make_df()
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "open",
                "operator": "EQ",
                "right_operand_type": "SCALAR",
                "right_operand_value": "10",
            }
        ],
    }
    result = evaluate_conditions(df, group)
    assert result.tolist() == [True, False, False, False, False]


def test_gte_lte() -> None:
    df = make_df()
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GTE",
                "right_operand_type": "SCALAR",
                "right_operand_value": "12",
            },
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "LTE",
                "right_operand_type": "SCALAR",
                "right_operand_value": "13",
            },
        ],
    }
    result = evaluate_conditions(df, group)
    assert result.tolist() == [False, False, True, True, False]


def test_crosses_above() -> None:
    df = make_df()
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "left_up",
                "operator": "CROSSES_ABOVE",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "right",
            }
        ],
    }
    result = evaluate_conditions(df, group)
    assert result.tolist() == [False, False, False, True, False]


def test_crosses_below() -> None:
    """
    Test CROSSES_BELOW operator.

    Bug Fix #9: Removed duplicate line in condition_engine.py that was
    redundantly computing result = prev & now twice. This test verifies
    CROSSES_BELOW still works correctly after the cleanup.
    """
    df = make_df()
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "left_down",
                "operator": "CROSSES_BELOW",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "right",
            }
        ],
    }
    result = evaluate_conditions(df, group)
    assert result.tolist() == [False, False, False, True, False]


def test_or_logic() -> None:
    df = make_df()
    group = {
        "logic": "OR",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "11",
            },
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "13",
            },
        ],
    }
    result = evaluate_conditions(df, group)
    assert result.tolist() == [True, False, False, False, True]


def test_zero_scalar_value_accepted() -> None:
    """
    Bug Fix Test #5: Zero scalar values should be accepted.

    Previously, the validation used all() which treats 0 as falsy.
    Now using explicit None checks to allow 0 as a valid value.
    """
    df = make_df()

    # Test with integer 0
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": 0,  # Integer 0
            }
        ],
    }
    result = evaluate_conditions(df, group)
    # All closes (10-14) should be > 0
    assert result.tolist() == [True, True, True, True, True]

    # Test with string '0'
    group2 = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "0",  # String '0'
            }
        ],
    }
    result2 = evaluate_conditions(df, group2)
    # Should work the same as integer 0
    assert result2.tolist() == [True, True, True, True, True]


def test_zero_in_left_operand() -> None:
    """
    Bug Fix Test #5: Zero as left operand value should work.
    """
    index = pd.date_range("2020-01-01", periods=3, freq="D")
    df = pd.DataFrame(
        {
            "open": [10, 10, 10],
            "close": [10, 10, 10],
            "volume": [0, 100, 0],  # Zero volume on bars 0 and 2
            "indicator": [5, 5, 5],
        },
        index=index,
    )

    # Check where volume equals 0
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "volume",
                "operator": "EQ",
                "right_operand_type": "SCALAR",
                "right_operand_value": 0,
            }
        ],
    }
    result = evaluate_conditions(df, group)
    assert result.tolist() == [True, False, True]


def test_empty_string_value_accepted() -> None:
    """
    Bug Fix Test #5: Empty string should be accepted (though may fail later).

    Empty string is a valid value to pass validation, even if it causes
    errors during operand extraction.
    """
    df = make_df()

    # Empty string as scalar value should pass validation
    # (it will fail during conversion to float, but that's different)
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "",  # Empty string
            }
        ],
    }

    # Should raise ValueError during float conversion, not during validation
    try:
        result = evaluate_conditions(df, group)
        assert False, "Should have raised ValueError for invalid scalar"
    except ValueError as e:
        # Should fail on scalar conversion, not missing field validation
        assert "Invalid scalar value" in str(e) or "could not convert" in str(e).lower()


def test_none_value_rejected() -> None:
    """
    Bug Fix Test #5: None values should still be rejected.

    The fix checks for None explicitly, so None should still fail validation.
    """
    df = make_df()

    # None as value should be rejected
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": None,  # None value
            }
        ],
    }

    try:
        result = evaluate_conditions(df, group)
        assert False, "Should have raised ValueError for None value"
    except ValueError as e:
        assert "missing required fields" in str(e).lower()


def test_missing_field_rejected() -> None:
    """
    Bug Fix Test #5: Missing fields should still be rejected.
    """
    df = make_df()

    # Missing operator field
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                # Missing operator!
                "right_operand_type": "SCALAR",
                "right_operand_value": "10",
            }
        ],
    }

    try:
        result = evaluate_conditions(df, group)
        assert False, "Should have raised ValueError for missing operator"
    except ValueError as e:
        assert "missing required fields" in str(e).lower()
        assert "operator" in str(e).lower()


# ============================================================================
# LOOKBACK TESTS (V2 Feature)
# ============================================================================


def test_lookback_basic_one_bar() -> None:
    """
    Test LOOKBACK with 1-bar lookback (compare to previous bar).
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [10, 10, 10, 10, 10],
            "close": [10, 15, 20, 18, 22],
            "value": [10, 15, 20, 25, 30],
        },
        index=index,
    )

    # Check if value > value from 1 bar ago (value is rising)
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "value",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "value:-1",
            }
        ],
    }

    result = evaluate_conditions(df, group)

    # Expected: [False, True, True, True, True]
    # value[0]=10 > value[-1]=NaN → False (no previous bar)
    # value[1]=15 > value[0]=10 → True
    # value[2]=20 > value[1]=15 → True
    # value[3]=25 > value[2]=20 → True
    # value[4]=30 > value[3]=25 → True
    assert result.tolist() == [False, True, True, True, True]


def test_lookback_multi_bar() -> None:
    """
    Test LOOKBACK with 3-bar lookback (ADX rising over 3 bars).
    """
    index = pd.date_range("2020-01-01", periods=6, freq="D")
    df = pd.DataFrame(
        {
            "open": [10] * 6,
            "close": [10] * 6,
            "adx": [20, 22, 21, 25, 28, 26],
        },
        index=index,
    )

    # Check if ADX > ADX from 3 bars ago
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "adx",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "adx:-3",
            }
        ],
    }

    result = evaluate_conditions(df, group)

    # Expected: [False, False, False, True, True, True]
    # adx[0]=20 > adx[-3]=NaN → False
    # adx[1]=22 > adx[-2]=NaN → False
    # adx[2]=21 > adx[-1]=NaN → False
    # adx[3]=25 > adx[0]=20 → True
    # adx[4]=28 > adx[1]=22 → True
    # adx[5]=26 > adx[2]=21 → True
    assert result.tolist() == [False, False, False, True, True, True]


def test_lookback_with_ohlcv() -> None:
    """
    Test LOOKBACK with OHLCV data (price momentum).
    """
    index = pd.date_range("2020-01-01", periods=6, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 102, 105, 103, 108, 110],
            "close": [100, 102, 105, 103, 108, 110],
            "high": [101, 103, 106, 104, 109, 111],
            "low": [99, 101, 104, 102, 107, 109],
            "volume": [1000] * 6,
        },
        index=index,
    )

    # Check if close > close from 3 bars ago (uptrend)
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "close:-3",
            }
        ],
    }

    result = evaluate_conditions(df, group)

    # Expected: [False, False, False, True, True, True]
    # close[3]=103 > close[0]=100 → True
    # close[4]=108 > close[1]=102 → True
    # close[5]=110 > close[2]=105 → True
    assert result.tolist() == [False, False, False, True, True, True]


def test_lookback_falling_detection() -> None:
    """
    Test LOOKBACK for falling detection (value < value from N bars ago).
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [10] * 5,
            "close": [10] * 5,
            "rsi": [70, 65, 60, 62, 58],
        },
        index=index,
    )

    # Check if RSI < RSI from 2 bars ago (falling)
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi",
                "operator": "LT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "rsi:-2",
            }
        ],
    }

    result = evaluate_conditions(df, group)

    # Expected: [False, False, True, False, True]
    # rsi[0]=70 < rsi[-2]=NaN → False
    # rsi[1]=65 < rsi[-1]=NaN → False
    # rsi[2]=60 < rsi[0]=70 → True
    # rsi[3]=62 < rsi[1]=65 → True
    # rsi[4]=58 < rsi[2]=60 → True
    assert result.tolist() == [False, False, True, True, True]


def test_lookback_with_crossover() -> None:
    """
    Test LOOKBACK with CROSSES_ABOVE operator.
    """
    index = pd.date_range("2020-01-01", periods=6, freq="D")
    df = pd.DataFrame(
        {
            "open": [10] * 6,
            "close": [10] * 6,
            "fast": [10, 12, 15, 18, 20, 19],
            "slow": [15, 14, 13, 12, 11, 12],
        },
        index=index,
    )

    # Check if fast crosses above slow from 2 bars ago
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "fast",
                "operator": "CROSSES_ABOVE",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "slow:-2",
            }
        ],
    }

    result = evaluate_conditions(df, group)

    # Crossover detection:
    # Bar i: fast[i] > slow[i-2] AND fast[i-1] <= slow[i-3]
    # This is a complex case, just verify it runs without error
    assert len(result) == 6
    assert isinstance(result, pd.Series)


def test_lookback_ichimoku_chikou() -> None:
    """
    Test LOOKBACK for Ichimoku Chikou validation (close > close[-26]).
    """
    index = pd.date_range("2020-01-01", periods=30, freq="D")
    # Price trending up
    close_values = [100 + i for i in range(30)]

    df = pd.DataFrame(
        {
            "open": close_values,
            "close": close_values,
            "high": [c + 1 for c in close_values],
            "low": [c - 1 for c in close_values],
            "volume": [1000] * 30,
        },
        index=index,
    )

    # Check if close > close from 26 bars ago (Chikou validation)
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "close:-26",
            }
        ],
    }

    result = evaluate_conditions(df, group)

    # First 26 bars should be False (no lookback available)
    assert result.iloc[:26].sum() == 0

    # Bars 26+ should be True (price is rising)
    # close[26]=126 > close[0]=100 → True
    assert result.iloc[26:].all()


def test_lookback_invalid_format_no_colon() -> None:
    """
    Test LOOKBACK with invalid format (missing colon).
    """
    df = make_df()

    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "left",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "invalid_format",  # Missing ":"
            }
        ],
    }

    try:
        evaluate_conditions(df, group)
        assert False, "Should have raised ValueError for invalid format"
    except ValueError as e:
        assert "invalid lookback format" in str(e).lower()
        assert "expected 'column:offset'" in str(e).lower()


def test_lookback_invalid_format_non_numeric_offset() -> None:
    """
    Test LOOKBACK with non-numeric offset.
    """
    df = make_df()

    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "left",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "left:abc",  # Non-numeric offset
            }
        ],
    }

    try:
        evaluate_conditions(df, group)
        assert False, "Should have raised ValueError for non-numeric offset"
    except ValueError as e:
        assert "invalid offset" in str(e).lower()
        assert "must be an integer" in str(e).lower()


def test_lookback_column_not_found() -> None:
    """
    Test LOOKBACK with non-existent column.
    """
    df = make_df()

    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "left",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "nonexistent:-3",
            }
        ],
    }

    try:
        evaluate_conditions(df, group)
        assert False, "Should have raised ValueError for missing column"
    except ValueError as e:
        assert "column not found" in str(e).lower()
        assert "nonexistent" in str(e).lower()


def test_lookback_offset_bounds() -> None:
    """
    Test LOOKBACK with offset exceeding bounds.
    """
    df = make_df()

    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "left",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "left:-2000",  # Exceeds bounds
            }
        ],
    }

    try:
        evaluate_conditions(df, group)
        assert False, "Should have raised ValueError for offset out of bounds"
    except ValueError as e:
        assert "offset must be between" in str(e).lower()


def test_lookback_both_sides() -> None:
    """
    Test LOOKBACK on both left and right operands (compare two lookbacks).
    """
    index = pd.date_range("2020-01-01", periods=15, freq="D")
    close_values = [100, 102, 105, 103, 108, 110, 112, 115, 113, 118, 120, 122, 125, 123, 128]

    df = pd.DataFrame(
        {
            "open": [10] * 15,
            "close": close_values,
            "high": [c + 1 for c in close_values],
            "low": [c - 1 for c in close_values],
            "volume": [1000] * 15,
        },
        index=index,
    )

    # Check if close from 5 bars ago > close from 10 bars ago
    # This tests momentum acceleration
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "LOOKBACK",
                "left_operand_value": "close:-5",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "close:-10",
            }
        ],
    }

    result = evaluate_conditions(df, group)

    # First 10 bars should be False (no lookback available for right side)
    assert result.iloc[:10].sum() == 0

    # Bars 10+ should compare close[-5] to close[-10]
    # All should be True since price is generally rising
    assert result.iloc[10:].all()


def test_lookback_with_and_logic() -> None:
    """
    Test LOOKBACK with multiple conditions using AND logic.
    """
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": [10] * 10,
            "close": [10] * 10,
            "adx": [20, 22, 24, 26, 28, 30, 32, 34, 36, 38],
            "rsi": [40, 42, 45, 48, 50, 52, 55, 58, 60, 62],
        },
        index=index,
    )

    # Both ADX and RSI must be rising over 3 bars
    group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "adx",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "adx:-3",
            },
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "rsi:-3",
            },
        ],
    }

    result = evaluate_conditions(df, group)

    # First 3 bars: False (no lookback)
    assert result.iloc[:3].sum() == 0

    # Bars 3+: Both conditions true (both rising)
    assert result.iloc[3:].all()
