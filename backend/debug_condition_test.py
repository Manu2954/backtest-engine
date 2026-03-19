from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.condition_engine import evaluate_conditions, evaluate_conditions_with_attribution


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


df = make_test_df()
print("DataFrame:")
print(df.head())
print("\nBar 0 values:")
print(f"rsi_14: {df.iloc[0]['rsi_14']}")
print(f"sma_50: {df.iloc[0]['sma_50']}")

condition_group = {
    "logic": "AND",
    "conditions": [
        {
            "id": "cond-1",
            "left_operand_type": "INDICATOR",
            "left_operand_value": "rsi_14",
            "operator": "LT",
            "right_operand_type": "SCALAR",
            "right_operand_value": "50",
        },
    ],
}

print("\nEvaluating condition: rsi_14 < 50")
result_series = evaluate_conditions(df, condition_group)
print(f"Result series:\n{result_series}")
print(f"\nResult at bar 0: {result_series.iloc[0]}")

triggered, attribution_data = evaluate_conditions_with_attribution(df, condition_group, 0)
print(f"\nWith attribution:")
print(f"Triggered: {triggered}")
print(f"Attribution data: {attribution_data}")
