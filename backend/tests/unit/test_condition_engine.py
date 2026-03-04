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
