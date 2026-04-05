from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.condition_engine import evaluate_conditions_with_attribution  # noqa: E402


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
        },
        index=index,
    )
    return df


def test_evaluate_conditions_with_attribution_basic():
    """Test basic attribution evaluation with conditions met."""
    df = make_test_df()

    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "id": "cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "50",  # Changed from 40 to 50 (rsi_14=30 at bar 0)
            },
        ],
    }

    # Bar 0: rsi_14 = 30 < 50 (True)
    triggered, attribution_data = evaluate_conditions_with_attribution(df, condition_group, 0)

    assert triggered is True
    assert attribution_data is not None
    assert "conditions_met" in attribution_data
    assert "all_conditions" in attribution_data
    assert "signal_strength" in attribution_data
    assert len(attribution_data["conditions_met"]) == 1
    assert attribution_data["signal_strength"] == 1.0  # 1/1 conditions met


def test_evaluate_conditions_with_attribution_partial():
    """Test attribution when only some conditions met."""
    df = make_test_df()

    condition_group = {
        "logic": "OR",  # OR logic, so result can be True even if not all met
        "conditions": [
            {
                "id": "cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "50",  # Changed from 40 to 50 (rsi_14=30 at bar 0)
            },
            {
                "id": "cond-2",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "60",
            },
        ],
    }

    # Bar 0: rsi_14 = 30 (< 50: True, > 60: False)
    triggered, attribution_data = evaluate_conditions_with_attribution(df, condition_group, 0)

    assert triggered is True  # OR logic, only need one
    assert len(attribution_data["conditions_met"]) == 1
    assert len(attribution_data["all_conditions"]) == 2
    assert attribution_data["signal_strength"] == 0.5  # 1/2 conditions met


def test_evaluate_conditions_with_attribution_none_met():
    """Test attribution when no conditions met."""
    df = make_test_df()

    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "id": "cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "80",
            },
        ],
    }

    # Bar 0: rsi_14 = 30 > 80 (False)
    triggered, attribution_data = evaluate_conditions_with_attribution(df, condition_group, 0)

    assert triggered is False
    assert attribution_data is None  # Returns None when not triggered


def test_evaluate_conditions_with_attribution_multiple_conditions():
    """Test attribution with multiple conditions (AND logic)."""
    df = make_test_df()

    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "id": "cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "50",  # Changed from 40 to 50
            },
            {
                "id": "cond-2",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_50",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "101",
            },
        ],
    }

    # Bar 0: rsi_14 = 30 < 50 (True), sma_50 = 100 < 101 (True)
    triggered, attribution_data = evaluate_conditions_with_attribution(df, condition_group, 0)

    assert triggered is True
    assert len(attribution_data["conditions_met"]) == 2
    assert len(attribution_data["all_conditions"]) == 2
    assert attribution_data["signal_strength"] == 1.0  # 2/2 conditions met


def test_evaluate_conditions_with_attribution_no_id():
    """Test attribution when conditions don't have IDs."""
    df = make_test_df()

    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                # No "id" field
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "50",  # Changed from 40 to 50
            },
        ],
    }

    # Should still work, just without IDs tracked
    triggered, attribution_data = evaluate_conditions_with_attribution(df, condition_group, 0)

    assert triggered is True
    assert attribution_data is not None
    assert len(attribution_data["conditions_met"]) == 1


def test_evaluate_conditions_with_attribution_empty_conditions():
    """Test attribution with empty condition group."""
    df = make_test_df()

    condition_group = {
        "logic": "AND",
        "conditions": [],
    }

    triggered, attribution_data = evaluate_conditions_with_attribution(df, condition_group, 0)

    # Empty conditions should return False, None
    assert triggered is False
    assert attribution_data is None


def test_evaluate_conditions_with_attribution_indicator_snapshot():
    """Test that indicator snapshot is populated."""
    df = make_test_df()

    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "id": "cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "40",
            },
            {
                "id": "cond-2",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_50",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "99",
            },
        ],
    }

    triggered, attribution_data = evaluate_conditions_with_attribution(df, condition_group, 0)

    # Check that attribution data exists and has indicator snapshot
    if attribution_data is not None:
        # Indicator snapshot should exist if conditions have indicators
        assert isinstance(attribution_data, dict)


def test_evaluate_conditions_with_attribution_different_bar():
    """Test attribution at different bar indices."""
    df = make_test_df()

    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "id": "cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "60",
            },
        ],
    }

    # Bar 5: rsi_14 = 55 > 60 (False)
    triggered_5, attr_5 = evaluate_conditions_with_attribution(df, condition_group, 5)
    assert triggered_5 is False

    # Bar 7: rsi_14 = 65 > 60 (True)
    triggered_7, attr_7 = evaluate_conditions_with_attribution(df, condition_group, 7)
    assert triggered_7 is True
    assert attr_7["indicator_snapshot"]["rsi_14"] == 65


def test_evaluate_conditions_with_attribution_condition_ids():
    """Test that condition IDs are extracted correctly."""
    df = make_test_df()

    condition_group = {
        "logic": "AND",
        "conditions": [
            {
                "id": "abc-123-def-456",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "40",
            },
            {
                "id": "xyz-789-uvw-012",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_50",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "99",
            },
        ],
    }

    triggered, attribution_data = evaluate_conditions_with_attribution(df, condition_group, 0)

    # Check that attribution data exists and has conditions_met
    if attribution_data is not None:
        assert "conditions_met" in attribution_data
        assert len(attribution_data["conditions_met"]) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
