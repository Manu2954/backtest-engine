"""
Test script for boolean expression API support.

Tests creating a strategy with expression-based conditions via API.
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_create_strategy_with_expressions():
    """Test creating a strategy with boolean expressions via API."""

    API_URL = "http://localhost:8080"

    # Strategy with expression-based conditions
    payload = {
        "name": "Complex Boolean Expression Strategy",
        "description": "RSI oversold with strong trend OR golden cross",
        "indicators": [
            {
                "indicator_type": "RSI",
                "alias": "rsi_14",
                "params": {"period": 14, "source": "close"},
            },
            {
                "indicator_type": "ADX",
                "alias": "adx_14",
                "params": {"period": 14},
            },
            {
                "indicator_type": "EMA",
                "alias": "ema_50",
                "params": {"period": 50, "source": "close"},
            },
            {
                "indicator_type": "EMA",
                "alias": "ema_200",
                "params": {"period": 200, "source": "close"},
            },
        ],
        # Named condition groups
        "entry_groups": {
            "oversold": {
                "group_name": "oversold",
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
                "group_name": "trending",
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
                "group_name": "golden_cross",
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
        },
        # Boolean expression combining groups
        "entry_expression": "(oversold && trending) || golden_cross",
        # Simple exit
        "exit_groups": {
            "overbought": {
                "group_name": "overbought",
                "logic": "OR",
                "conditions": [
                    {
                        "left_operand_type": "INDICATOR",
                        "left_operand_value": "rsi_14",
                        "operator": "GT",
                        "right_operand_type": "SCALAR",
                        "right_operand_value": "70",
                    }
                ],
            }
        },
        "exit_expression": "overbought",
    }

    print("=" * 80)
    print("Testing Boolean Expression API Support")
    print("=" * 80)

    # Create strategy
    print("\n1. Creating strategy with boolean expressions...")
    response = requests.post(f"{API_URL}/strategies", json=payload, timeout=10)

    if response.status_code != 200:
        print(f"❌ Failed to create strategy: {response.status_code}")
        print(f"Response: {response.text}")
        try:
            print(f"JSON: {response.json()}")
        except:
            pass
        return False

    strategy = response.json()
    strategy_id = strategy["id"]
    print(f"✅ Strategy created: {strategy_id}")
    print(f"   Name: {strategy['name']}")
    print(f"   Entry expression: {strategy.get('entry_expression')}")
    print(f"   Exit expression: {strategy.get('exit_expression')}")
    print(f"   Condition groups: {len(strategy['condition_groups'])}")

    # Verify condition groups have names
    print("\n2. Verifying condition group names...")
    entry_groups = [g for g in strategy["condition_groups"] if g["group_type"] == "ENTRY"]
    exit_groups = [g for g in strategy["condition_groups"] if g["group_type"] == "EXIT"]

    print(f"   Entry groups: {[g['group_name'] for g in entry_groups]}")
    print(f"   Exit groups: {[g['group_name'] for g in exit_groups]}")

    expected_entry_names = {"oversold", "trending", "golden_cross"}
    actual_entry_names = {g["group_name"] for g in entry_groups}

    if expected_entry_names != actual_entry_names:
        print(f"❌ Entry group names mismatch!")
        print(f"   Expected: {expected_entry_names}")
        print(f"   Actual: {actual_entry_names}")
        return False

    print("✅ All entry groups have correct names")

    # Retrieve strategy
    print("\n3. Retrieving strategy...")
    response = requests.get(f"{API_URL}/strategies/{strategy_id}", timeout=10)

    if response.status_code != 200:
        print(f"❌ Failed to retrieve strategy: {response.status_code}")
        return False

    retrieved = response.json()
    print(f"✅ Strategy retrieved")
    print(f"   Entry expression: {retrieved.get('entry_expression')}")
    print(f"   Exit expression: {retrieved.get('exit_expression')}")

    # Verify expressions match
    if retrieved.get("entry_expression") != payload["entry_expression"]:
        print(f"❌ Entry expression mismatch!")
        print(f"   Expected: {payload['entry_expression']}")
        print(f"   Actual: {retrieved.get('entry_expression')}")
        return False

    print("✅ Expressions match")

    # Clean up
    print("\n4. Cleaning up...")
    response = requests.delete(f"{API_URL}/strategies/{strategy_id}", timeout=10)

    if response.status_code != 200:
        print(f"⚠️  Failed to delete strategy: {response.status_code}")
    else:
        print(f"✅ Strategy deleted")

    print("\n" + "=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    try:
        success = test_create_strategy_with_expressions()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
