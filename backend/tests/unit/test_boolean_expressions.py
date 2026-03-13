from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.condition_engine import evaluate_expression  # noqa: E402


def make_df(rows: int = 100) -> pd.DataFrame:
    """Create test DataFrame with OHLCV data and indicators."""
    index = pd.date_range("2020-01-01", periods=rows, freq="D")
    close = pd.Series(range(rows), index=index, dtype="float") + 100.0

    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
        },
        index=index,
    )

    # Add mock indicators
    df["rsi_14"] = 50.0  # Neutral RSI
    df["adx_14"] = 20.0  # Weak trend
    df["ema_20"] = close
    df["ema_50"] = close - 5

    return df


def test_simple_and_expression() -> None:
    """Test simple A && B expression."""
    df = make_df(10)

    # Set conditions: bar 5 has both true
    df.loc[df.index[5], "rsi_14"] = 25  # Oversold
    df.loc[df.index[5], "adx_14"] = 30  # Trending

    groups = {
        "oversold": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "30",
                }
            ],
        },
        "trending": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "adx_14",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "25",
                }
            ],
        },
    }

    result = evaluate_expression(df, groups, "oversold && trending")

    # Only bar 5 should be True
    assert result.iloc[5] is True
    assert result.sum() == 1


def test_simple_or_expression() -> None:
    """Test simple A || B expression."""
    df = make_df(10)

    # Bar 3: oversold only
    df.loc[df.index[3], "rsi_14"] = 25

    # Bar 7: trending only
    df.loc[df.index[7], "adx_14"] = 30

    groups = {
        "oversold": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "30",
                }
            ],
        },
        "trending": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "adx_14",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "25",
                }
            ],
        },
    }

    result = evaluate_expression(df, groups, "oversold || trending")

    # Bars 3 and 7 should be True
    assert result.iloc[3] is True
    assert result.iloc[7] is True
    assert result.sum() == 2


def test_complex_expression_with_parentheses() -> None:
    """Test (A && B) || C expression."""
    df = make_df(10)

    # Bar 2: A && B true
    df.loc[df.index[2], "rsi_14"] = 25
    df.loc[df.index[2], "adx_14"] = 30

    # Bar 5: C true only
    df.loc[df.index[5], "ema_20"] = 110

    groups = {
        "A": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "30",
                }
            ],
        },
        "B": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "adx_14",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "25",
                }
            ],
        },
        "C": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "ema_20",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "105",
                }
            ],
        },
    }

    result = evaluate_expression(df, groups, "(A && B) || C")

    # Bars 2 and 5 should be True
    assert result.iloc[2] is True
    assert result.iloc[5] is True
    assert result.sum() == 2


def test_not_operator() -> None:
    """Test NOT operator (!)."""
    df = make_df(10)

    # All bars have ADX = 20 (< 25)
    # So "trending" is False everywhere
    # "!trending" should be True everywhere

    groups = {
        "trending": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "adx_14",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "25",
                }
            ],
        },
    }

    result = evaluate_expression(df, groups, "!trending")

    # All bars should be True (NOT trending)
    assert result.sum() == len(df)


def test_complex_nested_expression() -> None:
    """Test A && (B || C) && D expression."""
    df = make_df(10)

    # Bar 4: A, B, D all true (C false)
    df.loc[df.index[4], "rsi_14"] = 25  # A
    df.loc[df.index[4], "adx_14"] = 30  # B
    df.loc[df.index[4], "ema_20"] = 110  # D

    groups = {
        "A": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "30",
                }
            ],
        },
        "B": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "adx_14",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "25",
                }
            ],
        },
        "C": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "OHLCV",
                    "left_operand_value": "volume",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "2000",
                }
            ],
        },
        "D": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "ema_20",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "105",
                }
            ],
        },
    }

    result = evaluate_expression(df, groups, "A && (B || C) && D")

    # Bar 4: A=T, B=T, C=F, D=T → T && (T || F) && T = T
    assert result.iloc[4] is True
    assert result.sum() == 1


def test_alternative_operator_syntax() -> None:
    """Test that & and | work the same as && and ||."""
    df = make_df(10)

    df.loc[df.index[5], "rsi_14"] = 25
    df.loc[df.index[5], "adx_14"] = 30

    groups = {
        "A": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "30",
                }
            ],
        },
        "B": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "adx_14",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "25",
                }
            ],
        },
    }

    # Test with &&
    result1 = evaluate_expression(df, groups, "A && B")

    # Test with &
    result2 = evaluate_expression(df, groups, "A & B")

    # Should be identical
    assert result1.equals(result2)


def test_undefined_group_error() -> None:
    """Test error when expression references undefined group."""
    df = make_df(10)

    groups = {
        "A": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "30",
                }
            ],
        },
    }

    # Expression references "B" which doesn't exist
    with pytest.raises(ValueError, match="undefined condition groups.*B"):
        evaluate_expression(df, groups, "A && B")


def test_invalid_characters_error() -> None:
    """Test error when expression contains invalid characters."""
    df = make_df(10)

    groups = {
        "A": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "30",
                }
            ],
        },
    }

    # Expression with semicolon (injection attempt)
    with pytest.raises(ValueError, match="Invalid characters"):
        evaluate_expression(df, groups, "A; import os")


def test_empty_expression_error() -> None:
    """Test error when expression is empty."""
    df = make_df(10)

    groups = {
        "A": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "30",
                }
            ],
        },
    }

    with pytest.raises(ValueError, match="expression cannot be empty"):
        evaluate_expression(df, groups, "")


def test_empty_groups_error() -> None:
    """Test error when condition_groups is empty."""
    df = make_df(10)

    with pytest.raises(ValueError, match="condition_groups cannot be empty"):
        evaluate_expression(df, groups={}, expression="A")


def test_multiple_groups_same_name_reused() -> None:
    """Test that groups are only evaluated once even if used multiple times."""
    df = make_df(10)

    df.loc[df.index[5], "rsi_14"] = 25

    groups = {
        "oversold": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "30",
                }
            ],
        },
    }

    # Use same group multiple times in expression
    result = evaluate_expression(df, groups, "oversold || oversold")

    # Should work correctly (same as just "oversold")
    assert result.iloc[5] is True
    assert result.sum() == 1


def test_descriptive_group_names() -> None:
    """Test that descriptive group names work correctly."""
    df = make_df(10)

    df.loc[df.index[3], "rsi_14"] = 25
    df.loc[df.index[3], "adx_14"] = 30

    groups = {
        "rsi_oversold": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "30",
                }
            ],
        },
        "strong_trend": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "adx_14",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "25",
                }
            ],
        },
    }

    result = evaluate_expression(df, groups, "rsi_oversold && strong_trend")

    assert result.iloc[3] is True
    assert result.sum() == 1


def test_real_world_strategy_expression() -> None:
    """Test realistic strategy with multiple condition groups."""
    df = make_df(20)

    # Setup: Bar 10 meets all conditions
    df.loc[df.index[10], "rsi_14"] = 28      # Oversold
    df.loc[df.index[10], "adx_14"] = 27      # Trending
    df.loc[df.index[10], "volume"] = 1500    # Volume surge
    df.loc[df.index[10], "ema_20"] = 115     # Above EMA 50

    groups = {
        "oversold": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "30",
                }
            ],
        },
        "trending": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "adx_14",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "25",
                }
            ],
        },
        "volume_surge": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "OHLCV",
                    "left_operand_value": "volume",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "1200",
                }
            ],
        },
        "price_above_ema": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "ema_20",
                    "operator": "GT",
                    "right_operand_type": "INDICATOR",
                    "right_operand_value": "ema_50",
                }
            ],
        },
    }

    # Entry: (oversold && trending && volume_surge) || price_above_ema
    result = evaluate_expression(
        df, groups, "(oversold && trending && volume_surge) || price_above_ema"
    )

    # Bar 10 should trigger
    assert result.iloc[10] is True
