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
