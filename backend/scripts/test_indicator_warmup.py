"""
Smoke test for Indicator Warmup Period Handling.

Tests:
1. No indicators - no warmup
2. Single indicator (RSI) - warmup period detected
3. Multiple indicators - longest warmup wins
4. Indicators with NaN - proper trimming
5. Insufficient data after warmup - error
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.indicator_layer import (  # noqa: E402
    compute_indicators,
    get_warmup_period,
    trim_warmup_period,
)


def test_no_indicators():
    """Test with no indicators - no warmup needed."""
    print("\n" + "="*80)
    print("TEST 1: No Indicators (No Warmup)")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "open": np.linspace(100, 110, 100),
        "high": np.linspace(102, 112, 100),
        "low": np.linspace(98, 108, 100),
        "close": np.linspace(101, 111, 100),
        "volume": np.random.randint(1000000, 5000000, 100),
    }, index=dates)

    # No indicators
    df_with_indicators = compute_indicators(df, [])

    warmup = get_warmup_period(df_with_indicators)
    print(f"Warmup period: {warmup} bars")

    assert warmup == 0, "No indicators should mean no warmup"
    print("\n✅ TEST 1 PASSED\n")


def test_single_indicator():
    """Test with single indicator (RSI-14)."""
    print("\n" + "="*80)
    print("TEST 2: Single Indicator (RSI-14)")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "open": np.linspace(100, 110, 100),
        "high": np.linspace(102, 112, 100),
        "low": np.linspace(98, 108, 100),
        "close": np.linspace(101, 111, 100),
        "volume": np.random.randint(1000000, 5000000, 100),
    }, index=dates)

    indicators = [
        {"indicator_type": "RSI", "alias": "rsi_14", "params": {"period": 14, "source": "close"}},
    ]

    df_with_indicators = compute_indicators(df, indicators)

    # Check for NaN in early bars
    print(f"RSI NaN count: {df_with_indicators['rsi_14'].isna().sum()}")
    print(f"First valid RSI at bar: {df_with_indicators['rsi_14'].first_valid_index()}")

    warmup = get_warmup_period(df_with_indicators)
    print(f"Warmup period: {warmup} bars")

    # RSI(14) typically needs 13-14 bars
    assert warmup > 0, "RSI should have warmup period"
    assert warmup < 20, "RSI(14) warmup should be less than 20 bars"

    # Test trimming
    trimmed_df, skipped = trim_warmup_period(df_with_indicators)
    print(f"Original bars: {len(df_with_indicators)}, After trim: {len(trimmed_df)}, Skipped: {skipped}")

    assert len(trimmed_df) == len(df_with_indicators) - skipped
    assert trimmed_df['rsi_14'].isna().sum() == 0, "Trimmed data should have no NaN in indicators"

    print("\n✅ TEST 2 PASSED\n")


def test_multiple_indicators():
    """Test with multiple indicators - longest warmup wins."""
    print("\n" + "="*80)
    print("TEST 3: Multiple Indicators (RSI-14 + SMA-50)")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "open": np.linspace(100, 110, 100),
        "high": np.linspace(102, 112, 100),
        "low": np.linspace(98, 108, 100),
        "close": np.linspace(101, 111, 100),
        "volume": np.random.randint(1000000, 5000000, 100),
    }, index=dates)

    indicators = [
        {"indicator_type": "RSI", "alias": "rsi_14", "params": {"period": 14, "source": "close"}},
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    ]

    df_with_indicators = compute_indicators(df, indicators)

    print(f"RSI NaN count: {df_with_indicators['rsi_14'].isna().sum()}")
    print(f"SMA NaN count: {df_with_indicators['sma_50'].isna().sum()}")

    warmup = get_warmup_period(df_with_indicators)
    print(f"Warmup period: {warmup} bars")

    # SMA(50) needs 49 bars, should be the longest
    assert warmup >= 49, "SMA(50) should need at least 49 bars warmup"

    # Test trimming
    trimmed_df, skipped = trim_warmup_period(df_with_indicators)
    print(f"Original bars: {len(df_with_indicators)}, After trim: {len(trimmed_df)}, Skipped: {skipped}")

    assert trimmed_df['rsi_14'].isna().sum() == 0, "No NaN in RSI"
    assert trimmed_df['sma_50'].isna().sum() == 0, "No NaN in SMA"

    print("\n✅ TEST 3 PASSED\n")


def test_macd_multi_column():
    """Test with MACD (multi-column indicator)."""
    print("\n" + "="*80)
    print("TEST 4: Multi-column Indicator (MACD)")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "open": np.linspace(100, 110, 100),
        "high": np.linspace(102, 112, 100),
        "low": np.linspace(98, 108, 100),
        "close": np.linspace(101, 111, 100),
        "volume": np.random.randint(1000000, 5000000, 100),
    }, index=dates)

    indicators = [
        {"indicator_type": "MACD", "alias": "macd", "params": {"fast": 12, "slow": 26, "signal": 9, "source": "close"}},
    ]

    df_with_indicators = compute_indicators(df, indicators)

    # MACD creates 3 columns
    assert "macd_macd" in df_with_indicators.columns
    assert "macd_signal" in df_with_indicators.columns
    assert "macd_hist" in df_with_indicators.columns

    warmup = get_warmup_period(df_with_indicators)
    print(f"Warmup period: {warmup} bars")

    # MACD(12,26,9) needs at least 26+9=35 bars
    assert warmup > 20, "MACD should have significant warmup"

    # Test trimming
    trimmed_df, skipped = trim_warmup_period(df_with_indicators)

    # All 3 MACD columns should have no NaN
    assert trimmed_df['macd_macd'].isna().sum() == 0
    assert trimmed_df['macd_signal'].isna().sum() == 0
    assert trimmed_df['macd_hist'].isna().sum() == 0

    print("\n✅ TEST 4 PASSED\n")


def test_insufficient_data_after_warmup():
    """Test error when insufficient data remains after warmup."""
    print("\n" + "="*80)
    print("TEST 5: Insufficient Data After Warmup")
    print("="*80)

    # Only 60 bars total
    dates = pd.date_range("2023-01-01", periods=60, freq="D")
    df = pd.DataFrame({
        "open": np.linspace(100, 110, 60),
        "high": np.linspace(102, 112, 60),
        "low": np.linspace(98, 108, 60),
        "close": np.linspace(101, 111, 60),
        "volume": np.random.randint(1000000, 5000000, 60),
    }, index=dates)

    # SMA(50) will leave only 11 bars
    indicators = [
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    ]

    df_with_indicators = compute_indicators(df, indicators)

    warmup = get_warmup_period(df_with_indicators)
    print(f"Warmup period: {warmup} bars")
    print(f"Remaining bars: {len(df_with_indicators) - warmup}")

    trimmed_df, skipped = trim_warmup_period(df_with_indicators)

    # Should have very few bars left
    assert len(trimmed_df) < 30, "Should have insufficient data after warmup"
    print(f"Only {len(trimmed_df)} bars remain - would trigger error in backtest task")

    print("\n✅ TEST 5 PASSED\n")


def test_all_nan_error():
    """Test error when all bars have NaN."""
    print("\n" + "="*80)
    print("TEST 6: All NaN Error")
    print("="*80)

    # Only 20 bars, but SMA(50) needs 50
    dates = pd.date_range("2023-01-01", periods=20, freq="D")
    df = pd.DataFrame({
        "open": np.linspace(100, 110, 20),
        "high": np.linspace(102, 112, 20),
        "low": np.linspace(98, 108, 20),
        "close": np.linspace(101, 111, 20),
        "volume": np.random.randint(1000000, 5000000, 20),
    }, index=dates)

    indicators = [
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    ]

    df_with_indicators = compute_indicators(df, indicators)

    # All bars should have NaN
    assert df_with_indicators['sma_50'].isna().all(), "All SMA values should be NaN"

    try:
        warmup = get_warmup_period(df_with_indicators)
        raise AssertionError("Should have raised ValueError for all-NaN data")
    except ValueError as e:
        print(f"Correctly raised error: {str(e)[:80]}...")
        assert "All bars contain NaN" in str(e)

    print("\n✅ TEST 6 PASSED\n")


def main() -> None:
    print("\n" + "="*80)
    print("SMOKE TEST: Indicator Warmup Period Handling")
    print("="*80)

    try:
        test_no_indicators()
        test_single_indicator()
        test_multiple_indicators()
        test_macd_multi_column()
        test_insufficient_data_after_warmup()
        test_all_nan_error()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nWarmup Handling Coverage:")
        print("  ✓ No indicators = no warmup")
        print("  ✓ Single indicator warmup detection")
        print("  ✓ Multiple indicators (longest warmup wins)")
        print("  ✓ Multi-column indicators (MACD)")
        print("  ✓ Insufficient data detection")
        print("  ✓ All-NaN error handling")
        print("\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
