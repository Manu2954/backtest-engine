#!/usr/bin/env python
"""Quick test to verify condition ID is included in payload."""
from __future__ import annotations

from uuid import UUID
from app.models.strategy import Strategy, ConditionGroup, Condition

# Create mock strategy with condition that has an ID
mock_condition = Condition(
    id=UUID("f4dbf4ad-7ea0-4a57-8e02-7eeabfcec5f2"),
    condition_group_id=UUID("32804afe-40b0-4f75-8dcf-2e3f04eb4cbd"),
    left_operand_type="INDICATOR",
    left_operand_value="sma_50",
    operator="CROSSES_ABOVE",
    right_operand_type="INDICATOR",
    right_operand_value="sma_200",
)

mock_group = ConditionGroup(
    id=UUID("32804afe-40b0-4f75-8dcf-2e3f04eb4cbd"),
    strategy_id=UUID("a9a37092-1fb4-4a64-bb70-7bf3893d8069"),
    group_type="ENTRY",
    logic="AND",
    conditions=[mock_condition],
)

mock_strategy = Strategy(
    id=UUID("a9a37092-1fb4-4a64-bb70-7bf3893d8069"),
    name="Test Strategy",
    user_id=UUID("21fd7c66-5781-43d1-8f75-ccfac7cde742"),
    condition_groups=[mock_group],
)

# Import the function we fixed
from app.tasks.backtest_task import _group_to_payload

# Test it
result = _group_to_payload(mock_strategy, "ENTRY")

print("=" * 80)
print("TESTING CONDITION ID FIX")
print("=" * 80)
print(f"\nResult: {result}")
print()

# Verify the fix
assert "conditions" in result, "Missing 'conditions' key"
assert len(result["conditions"]) == 1, "Should have 1 condition"
condition = result["conditions"][0]

print("Condition fields:")
for key, value in condition.items():
    print(f"  - {key}: {value}")
print()

# Check if 'id' field is present
if "id" in condition:
    print("✅ SUCCESS: 'id' field is present in condition payload")
    print(f"   Condition ID: {condition['id']}")
    print(f"   Expected: f4dbf4ad-7ea0-4a57-8e02-7eeabfcec5f2")
    assert condition['id'] == "f4dbf4ad-7ea0-4a57-8e02-7eeabfcec5f2", "ID mismatch"
    print("   ✅ ID matches expected value")
else:
    print("❌ FAILED: 'id' field is missing from condition payload")
    print("   The fix did not work!")

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
