"""
Direct test of boolean expression support without API server.

Tests the complete flow: database models → condition evaluation
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Add backend directory to path
ROOT = Path(__file__).resolve().parents[1]  # backend directory
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.condition_engine import evaluate_expression  # noqa: E402


def make_test_df() -> pd.DataFrame:
    """Create test DataFrame with OHLCV and indicators."""
    index = pd.date_range("2020-01-01", periods=100, freq="D")
    close = pd.Series(range(100), index=index, dtype="float") + 100.0

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

    # Add indicators
    df["rsi_14"] = 50.0
    df["adx_14"] = 20.0
    df["ema_50"] = close
    df["ema_200"] = close - 10

    return df


def test_expression_evaluation():
    """Test that boolean expressions work correctly."""
    print("=" * 80)
    print("Testing Boolean Expression Evaluation")
    print("=" * 80)

    df = make_test_df()

    # Set up conditions for specific bars
    # Bar 25: oversold AND trending (RSI < 30 AND ADX > 25)
    df.loc[df.index[25], "rsi_14"] = 28
    df.loc[df.index[25], "adx_14"] = 30

    # Bar 50: golden cross (EMA 50 crosses above EMA 200)
    df.loc[df.index[49], "ema_50"] = 95  # Below EMA 200
    df.loc[df.index[50], "ema_50"] = 105  # Above EMA 200

    # Define condition groups (matching API format)
    condition_groups = {
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
        "golden_cross": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "ema_50",
                    "operator": "CROSSES_ABOVE",
                    "right_operand_type": "INDICATOR",
                    "right_operand_value": "ema_200",
                }
            ],
        },
    }

    # Test expression: (oversold && trending) || golden_cross
    expression = "(oversold && trending) || golden_cross"

    print(f"\n1. Evaluating expression: {expression}")
    print(f"   Groups: {list(condition_groups.keys())}")

    result = evaluate_expression(df, condition_groups, expression)

    print(f"\n2. Results:")
    print(f"   Total bars: {len(df)}")
    print(f"   Signals triggered: {result.sum()}")

    # Find bars where signal triggered
    triggered_bars = result[result].index.tolist()
    triggered_indices = [df.index.get_loc(bar) for bar in triggered_bars]

    print(f"   Bar indices: {triggered_indices}")

    # Verify expected bars
    print(f"\n3. Verification:")

    # Bar 25 should trigger (oversold && trending)
    if result.iloc[25]:
        print(f"   ✅ Bar 25: (oversold && trending) triggered")
        print(f"      RSI={df.iloc[25]['rsi_14']}, ADX={df.iloc[25]['adx_14']}")
    else:
        print(f"   ❌ Bar 25: Expected trigger but didn't fire")
        return False

    # Bar 50 should trigger (golden_cross)
    if result.iloc[50]:
        print(f"   ✅ Bar 50: golden_cross triggered")
        print(f"      EMA50={df.iloc[50]['ema_50']}, EMA200={df.iloc[50]['ema_200']}")
    else:
        print(f"   ❌ Bar 50: Expected trigger but didn't fire")
        return False

    # Other bars should NOT trigger
    expected_triggers = {25, 50}
    actual_triggers = set(triggered_indices)

    if expected_triggers != actual_triggers:
        print(f"   ⚠️  Unexpected triggers:")
        print(f"      Expected: {expected_triggers}")
        print(f"      Actual: {actual_triggers}")
        print(f"      Extra: {actual_triggers - expected_triggers}")
        return False

    print(f"   ✅ All bars correct (only expected bars triggered)")

    # Test complex nested expression
    print(f"\n4. Testing nested expression: A && (B || C)")
    expression2 = "oversold && (trending || golden_cross)"
    result2 = evaluate_expression(df, condition_groups, expression2)

    print(f"   Signals triggered: {result2.sum()}")
    triggered_indices2 = [df.index.get_loc(bar) for bar in result2[result2].index]
    print(f"   Bar indices: {triggered_indices2}")

    # Bar 25 should trigger (oversold && trending)
    # Bar 50 should NOT trigger (oversold=False, so fails even though golden_cross=True)
    if result2.iloc[25] and not result2.iloc[50]:
        print(f"   ✅ Nested expression works correctly")
    else:
        print(f"   ❌ Nested expression failed")
        print(f"      Bar 25: {result2.iloc[25]} (expected True)")
        print(f"      Bar 50: {result2.iloc[50]} (expected False)")
        return False

    print("\n" + "=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)
    print("\n📝 Summary:")
    print("   - Boolean expressions work correctly")
    print("   - Named condition groups evaluate properly")
    print("   - Complex nested logic (A && (B || C)) supported")
    print("   - Ready for API integration")

    return True


if __name__ == "__main__":
    try:
        success = test_expression_evaluation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
