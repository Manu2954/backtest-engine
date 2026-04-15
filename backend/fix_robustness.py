#!/usr/bin/env python3
"""
Fix robustness_task.py function signatures to consistently accept session_maker.
"""

# Functions that need session_maker parameter added:
functions_to_fix = [
    ("_create_analysis_record", 2),  # After params
    ("_update_analysis_status", 2),   # After status
    ("_link_backtest_to_analysis", 4),  # After variant_params
    ("_wait_for_backtest_completion", 1),  # After run_id
    ("_get_backtest_metrics", 1),  # After backtest_run_id
    ("_get_strategy", 1),  # After strategy_id
    ("_create_backtest_run", 2),  # After backtest_params
]

# These functions create session_maker, don't need it passed:
# - _create_temporary_strategy (already has it)
# - _delete_temporary_strategy (needs it added)

print("Add session_maker parameter to these functions:")
for func_name, pos in functions_to_fix:
    print(f"  {func_name} - add after arg {pos}")

print("\nRemove _get_session_maker() calls from all helper functions")
print("Remove 'await engine.dispose()' calls from all helper functions")
