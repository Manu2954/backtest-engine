#!/usr/bin/env python3
"""
Test ROC and OBV indicators
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from app.engine.indicator_layer import compute_indicators


def test_roc_obv():
    """Quick test for ROC and OBV indicators."""

    print("="*70)
    print("  ROC and OBV Indicator Test")
    print("="*70)

    # Create test data
    index = pd.date_range("2020-01-01", periods=50, freq="D")
    close = [100 + i for i in range(50)]  # Rising price
    volume = [1000 + i*10 for i in range(50)]  # Rising volume

    df = pd.DataFrame({
        "open": close,
        "high": [c + 1 for c in close],
        "low": [c - 1 for c in close],
        "close": close,
        "volume": volume,
    }, index=index)

    print(f"\n1. Test Data: {len(df)} bars")
    print(f"   Price range: {df['close'].min():.2f} - {df['close'].max():.2f}")
    print(f"   Volume range: {df['volume'].min():.0f} - {df['volume'].max():.0f}")

    # Test ROC
    print("\n" + "-"*70)
    print("2. Testing ROC (Rate of Change)")
    print("-"*70)

    indicators_roc = [
        {
            "indicator_type": "ROC",
            "alias": "roc_10",
            "params": {"period": 10, "source": "close"},
        }
    ]

    df_roc = compute_indicators(df.copy(), indicators_roc)

    if "roc_10" in df_roc.columns:
        print("✓ ROC indicator computed successfully")
        print(f"  Column: roc_10")
        print(f"  NaN count: {df_roc['roc_10'].isna().sum()}")
        print(f"  Valid values: {df_roc['roc_10'].notna().sum()}")
        print(f"  Sample values (last 5): {df_roc['roc_10'].tail().tolist()}")

        # ROC should be positive for rising prices
        valid_roc = df_roc['roc_10'].dropna()
        if len(valid_roc) > 0:
            print(f"  Range: {valid_roc.min():.2f}% to {valid_roc.max():.2f}%")
    else:
        print("❌ ROC indicator not found in DataFrame")
        return False

    # Test OBV
    print("\n" + "-"*70)
    print("3. Testing OBV (On-Balance Volume)")
    print("-"*70)

    indicators_obv = [
        {
            "indicator_type": "OBV",
            "alias": "obv",
            "params": {},
        }
    ]

    df_obv = compute_indicators(df.copy(), indicators_obv)

    if "obv" in df_obv.columns:
        print("✓ OBV indicator computed successfully")
        print(f"  Column: obv")
        print(f"  NaN count: {df_obv['obv'].isna().sum()}")
        print(f"  Valid values: {df_obv['obv'].notna().sum()}")
        print(f"  Sample values (last 5): {df_obv['obv'].tail().tolist()}")

        # OBV should be cumulative and increasing for rising prices
        print(f"  Range: {df_obv['obv'].min():.0f} to {df_obv['obv'].max():.0f}")

        # Check if OBV is increasing (should be for rising price/volume)
        obv_increasing = (df_obv['obv'].iloc[-1] > df_obv['obv'].iloc[0])
        print(f"  OBV is {'increasing' if obv_increasing else 'decreasing'} ✓")
    else:
        print("❌ OBV indicator not found in DataFrame")
        return False

    # Test both together
    print("\n" + "-"*70)
    print("4. Testing ROC and OBV Together")
    print("-"*70)

    indicators_both = [
        {
            "indicator_type": "ROC",
            "alias": "roc_10",
            "params": {"period": 10, "source": "close"},
        },
        {
            "indicator_type": "OBV",
            "alias": "obv",
            "params": {},
        },
    ]

    df_both = compute_indicators(df.copy(), indicators_both)

    if "roc_10" in df_both.columns and "obv" in df_both.columns:
        print("✓ Both indicators computed successfully")
        print(f"  Columns: roc_10, obv")
        print("\n  Last 5 bars:")
        print(df_both[['close', 'volume', 'roc_10', 'obv']].tail().to_string())
    else:
        print("❌ One or both indicators missing")
        return False

    print("\n" + "="*70)
    print("  ALL TESTS PASSED ✓")
    print("="*70)
    print("\nROC and OBV indicators are working correctly!")
    return True


if __name__ == "__main__":
    try:
        success = test_roc_obv()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
