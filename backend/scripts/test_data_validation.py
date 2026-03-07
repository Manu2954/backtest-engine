"""
Smoke test for Data Quality Validation.

Tests:
1. Valid data - should pass
2. Empty DataFrame - should fail
3. Missing columns - should fail
4. Insufficient data - should fail
5. NaN values - should fail/warn
6. Zero/negative prices - should fail
7. Invalid OHLC relationships - should fail
8. Extreme price jumps - should warn
9. Duplicate timestamps - should fail
10. Zero volume - should warn
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_validator import validate_ohlcv_data, validate_or_raise  # noqa: E402


def test_valid_data():
    """Test with valid OHLCV data."""
    print("\n" + "="*80)
    print("TEST 1: Valid Data")
    print("="*80)

    # Create valid OHLCV data
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "open": np.linspace(100, 110, 100),
        "high": np.linspace(102, 112, 100),
        "low": np.linspace(98, 108, 100),
        "close": np.linspace(101, 111, 100),
        "volume": np.random.randint(1000000, 5000000, 100),
    }, index=dates)

    result = validate_ohlcv_data(df, "AAPL")

    print(f"Valid: {result.is_valid}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")

    assert result.is_valid, "Valid data should pass validation"
    assert len(result.errors) == 0, "Should have no errors"
    print("\n✅ TEST 1 PASSED\n")


def test_empty_dataframe():
    """Test with empty DataFrame."""
    print("\n" + "="*80)
    print("TEST 2: Empty DataFrame")
    print("="*80)

    df = pd.DataFrame()
    result = validate_ohlcv_data(df, "INVALID")

    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    assert not result.is_valid, "Empty DataFrame should fail"
    assert len(result.errors) > 0, "Should have errors"
    assert any("No data found" in err for err in result.errors)
    print("\n✅ TEST 2 PASSED\n")


def test_missing_columns():
    """Test with missing required columns."""
    print("\n" + "="*80)
    print("TEST 3: Missing Required Columns")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=50, freq="D")
    df = pd.DataFrame({
        "open": [100] * 50,
        "close": [101] * 50,
        # Missing: high, low, volume
    }, index=dates)

    result = validate_ohlcv_data(df, "AAPL")

    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    assert not result.is_valid, "Missing columns should fail"
    assert any("Missing required columns" in err for err in result.errors)
    print("\n✅ TEST 3 PASSED\n")


def test_insufficient_data():
    """Test with insufficient data points."""
    print("\n" + "="*80)
    print("TEST 4: Insufficient Data Points")
    print("="*80)

    # Only 10 bars, but min_bars=30
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    df = pd.DataFrame({
        "open": [100] * 10,
        "high": [102] * 10,
        "low": [98] * 10,
        "close": [101] * 10,
        "volume": [1000000] * 10,
    }, index=dates)

    result = validate_ohlcv_data(df, "AAPL", min_bars=30)

    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    assert not result.is_valid, "Insufficient data should fail"
    assert any("Insufficient data" in err for err in result.errors)
    print("\n✅ TEST 4 PASSED\n")


def test_nan_values():
    """Test with NaN values."""
    print("\n" + "="*80)
    print("TEST 5: NaN Values")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=50, freq="D")
    df = pd.DataFrame({
        "open": [100] * 50,
        "high": [102] * 50,
        "low": [98] * 50,
        "close": [101] * 50,
        "volume": [1000000] * 50,
    }, index=dates)

    # Add some NaN values (15% of data)
    df.loc[df.index[:8], "close"] = np.nan

    result = validate_ohlcv_data(df, "AAPL")

    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    assert not result.is_valid, "Too many NaN values should fail"
    assert any("NaN values" in err for err in result.errors)
    print("\n✅ TEST 5 PASSED\n")


def test_zero_negative_prices():
    """Test with zero or negative prices."""
    print("\n" + "="*80)
    print("TEST 6: Zero/Negative Prices")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=50, freq="D")
    df = pd.DataFrame({
        "open": [100] * 50,
        "high": [102] * 50,
        "low": [98] * 50,
        "close": [101] * 50,
        "volume": [1000000] * 50,
    }, index=dates)

    # Add some zero/negative prices
    df.loc[df.index[5], "close"] = 0
    df.loc[df.index[10], "open"] = -5

    result = validate_ohlcv_data(df, "AAPL")

    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    assert not result.is_valid, "Zero/negative prices should fail"
    assert any("zero or negative" in err for err in result.errors)
    print("\n✅ TEST 6 PASSED\n")


def test_invalid_ohlc_relationships():
    """Test with invalid OHLC relationships."""
    print("\n" + "="*80)
    print("TEST 7: Invalid OHLC Relationships")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=50, freq="D")
    df = pd.DataFrame({
        "open": [100] * 50,
        "high": [102] * 50,
        "low": [98] * 50,
        "close": [101] * 50,
        "volume": [1000000] * 50,
    }, index=dates)

    # Make high < low (invalid)
    df.loc[df.index[5], "high"] = 95
    df.loc[df.index[5], "low"] = 98

    result = validate_ohlcv_data(df, "AAPL")

    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    assert not result.is_valid, "Invalid OHLC relationships should fail"
    assert any("high < low" in err for err in result.errors)
    print("\n✅ TEST 7 PASSED\n")


def test_extreme_price_jumps():
    """Test with extreme price jumps (should warn, not fail)."""
    print("\n" + "="*80)
    print("TEST 8: Extreme Price Jumps")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=50, freq="D")
    df = pd.DataFrame({
        "open": [100] * 50,
        "high": [102] * 50,
        "low": [98] * 50,
        "close": [101] * 50,
        "volume": [1000000] * 50,
    }, index=dates)

    # Add extreme price jump (200% in one day - stock split or error)
    # Must also adjust high/low to maintain valid OHLC relationships
    df.loc[df.index[25], "open"] = 300
    df.loc[df.index[25], "high"] = 305
    df.loc[df.index[25], "low"] = 295
    df.loc[df.index[25], "close"] = 300

    result = validate_ohlcv_data(df, "AAPL", max_price_jump_pct=50.0)

    print(f"Valid: {result.is_valid}")
    print(f"Warnings: {result.warnings}")
    print(f"Errors: {result.errors}")

    # Should still be valid but have warnings
    assert result.is_valid, f"Extreme jumps should warn, not fail. Errors: {result.errors}"
    assert len(result.warnings) > 0, "Should have warnings"
    assert any("Extreme price jump" in warn for warn in result.warnings)
    print("\n✅ TEST 8 PASSED\n")


def test_duplicate_timestamps():
    """Test with duplicate timestamps."""
    print("\n" + "="*80)
    print("TEST 9: Duplicate Timestamps")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=50, freq="D")
    df = pd.DataFrame({
        "open": [100] * 50,
        "high": [102] * 50,
        "low": [98] * 50,
        "close": [101] * 50,
        "volume": [1000000] * 50,
    }, index=dates)

    # Add duplicate timestamp
    df = pd.concat([df, df.iloc[:1]])

    result = validate_ohlcv_data(df, "AAPL")

    print(f"Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")

    assert not result.is_valid, "Duplicate timestamps should fail"
    assert any("duplicate timestamps" in err for err in result.errors)
    print("\n✅ TEST 9 PASSED\n")


def test_zero_volume():
    """Test with zero volume (should warn)."""
    print("\n" + "="*80)
    print("TEST 10: Zero Volume")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=50, freq="D")
    df = pd.DataFrame({
        "open": [100] * 50,
        "high": [102] * 50,
        "low": [98] * 50,
        "close": [101] * 50,
        "volume": [1000000] * 50,
    }, index=dates)

    # Set 10% of volume to zero
    df.loc[df.index[:5], "volume"] = 0

    result = validate_ohlcv_data(df, "AAPL")

    print(f"Valid: {result.is_valid}")
    print(f"Warnings: {result.warnings}")

    # Should still be valid but have warnings
    assert result.is_valid, "Zero volume should warn, not fail"
    assert len(result.warnings) > 0, "Should have warnings"
    assert any("Volume is zero" in warn for warn in result.warnings)
    print("\n✅ TEST 10 PASSED\n")


def test_validate_or_raise():
    """Test validate_or_raise function."""
    print("\n" + "="*80)
    print("TEST 11: validate_or_raise Function")
    print("="*80)

    # Valid data should not raise
    dates = pd.date_range("2023-01-01", periods=50, freq="D")
    df_valid = pd.DataFrame({
        "open": [100] * 50,
        "high": [102] * 50,
        "low": [98] * 50,
        "close": [101] * 50,
        "volume": [1000000] * 50,
    }, index=dates)

    try:
        validate_or_raise(df_valid, "AAPL")
        print("Valid data: No exception raised ✓")
    except ValueError:
        raise AssertionError("Valid data should not raise exception")

    # Invalid data should raise
    df_invalid = pd.DataFrame({
        "open": [0] * 50,  # Zero prices
        "high": [102] * 50,
        "low": [98] * 50,
        "close": [101] * 50,
        "volume": [1000000] * 50,
    }, index=dates)

    try:
        validate_or_raise(df_invalid, "INVALID")
        raise AssertionError("Invalid data should raise exception")
    except ValueError as e:
        print(f"Invalid data raised ValueError: {str(e)[:100]}... ✓")

    print("\n✅ TEST 11 PASSED\n")


def main() -> None:
    print("\n" + "="*80)
    print("SMOKE TEST: Data Quality Validation")
    print("="*80)

    try:
        test_valid_data()
        test_empty_dataframe()
        test_missing_columns()
        test_insufficient_data()
        test_nan_values()
        test_zero_negative_prices()
        test_invalid_ohlc_relationships()
        test_extreme_price_jumps()
        test_duplicate_timestamps()
        test_zero_volume()
        test_validate_or_raise()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nValidation Coverage:")
        print("  ✓ Empty DataFrame detection")
        print("  ✓ Missing columns detection")
        print("  ✓ Insufficient data detection")
        print("  ✓ NaN value detection")
        print("  ✓ Zero/negative price detection")
        print("  ✓ Invalid OHLC relationship detection")
        print("  ✓ Extreme price jump warnings")
        print("  ✓ Duplicate timestamp detection")
        print("  ✓ Zero volume warnings")
        print("  ✓ validate_or_raise exception handling")
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
