"""
Data quality validation module.

Validates OHLCV data before backtesting to catch data issues early.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class ValidationResult:
    """Result of data validation check."""
    is_valid: bool
    warnings: list[str]
    errors: list[str]

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """Add an error message and mark as invalid."""
        self.errors.append(message)
        self.is_valid = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def validate_ohlcv_data(
    df: pd.DataFrame,
    ticker: str,
    min_bars: int = 30,
    max_price_jump_pct: float = 50.0,
) -> ValidationResult:
    """
    Validate OHLCV data quality before backtesting.

    Args:
        df: OHLCV DataFrame with columns: open, high, low, close, volume
        ticker: Ticker symbol for error messages
        min_bars: Minimum number of bars required
        max_price_jump_pct: Maximum allowed price jump in one bar (percent)

    Returns:
        ValidationResult with is_valid flag and lists of warnings/errors
    """
    result = ValidationResult(is_valid=True, warnings=[], errors=[])

    # Check 1: Empty DataFrame
    if df.empty:
        result.add_error(f"No data found for ticker {ticker}")
        return result

    # Check 2: Required columns exist
    required_cols = {"open", "high", "low", "close", "volume"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        result.add_error(f"Missing required columns: {missing_cols}")
        return result

    # Check 3: Sufficient data points
    if len(df) < min_bars:
        result.add_error(
            f"Insufficient data: {len(df)} bars found, minimum {min_bars} required"
        )
        return result

    # Check 4: Check for NaN values
    nan_counts = df[["open", "high", "low", "close", "volume"]].isna().sum()
    for col, count in nan_counts.items():
        if count > 0:
            pct = (count / len(df)) * 100
            if pct > 10:
                result.add_error(f"Column '{col}' has {count} NaN values ({pct:.1f}% of data)")
            else:
                result.add_warning(f"Column '{col}' has {count} NaN values ({pct:.1f}% of data)")

    # Check 5: Check for zero or negative prices
    price_cols = ["open", "high", "low", "close"]
    for col in price_cols:
        zero_count = (df[col] <= 0).sum()
        if zero_count > 0:
            result.add_error(f"Column '{col}' has {zero_count} zero or negative values")

    # Check 6: OHLC relationship validation (High >= Low, etc.)
    invalid_hl = (df["high"] < df["low"]).sum()
    if invalid_hl > 0:
        result.add_error(f"Found {invalid_hl} bars where high < low (invalid data)")

    invalid_hoc = ((df["high"] < df["open"]) | (df["high"] < df["close"])).sum()
    if invalid_hoc > 0:
        result.add_error(f"Found {invalid_hoc} bars where high < open or high < close")

    invalid_loc = ((df["low"] > df["open"]) | (df["low"] > df["close"])).sum()
    if invalid_loc > 0:
        result.add_error(f"Found {invalid_loc} bars where low > open or low > close")

    # Check 7: Extreme price jumps (potential data errors)
    df_sorted = df.sort_index()
    close_pct_change = df_sorted["close"].pct_change().abs() * 100
    extreme_jumps = close_pct_change[close_pct_change > max_price_jump_pct]

    if len(extreme_jumps) > 0:
        for idx, jump in extreme_jumps.head(5).items():
            result.add_warning(
                f"Extreme price jump detected: {jump:.1f}% on {idx} "
                f"(may indicate data error or stock split)"
            )

    # Check 8: Check for duplicate timestamps
    duplicate_count = df.index.duplicated().sum()
    if duplicate_count > 0:
        result.add_error(f"Found {duplicate_count} duplicate timestamps")

    # Check 9: Volume validation
    zero_volume_count = (df["volume"] == 0).sum()
    if zero_volume_count > 0:
        pct = (zero_volume_count / len(df)) * 100
        if pct > 5:
            result.add_warning(
                f"Volume is zero for {zero_volume_count} bars ({pct:.1f}% of data) - "
                f"may indicate low liquidity"
            )

    # Check 10: Check for data gaps (missing trading days)
    # Only for daily or longer timeframes
    if len(df) >= 2:
        df_sorted = df.sort_index()
        time_diffs = df_sorted.index.to_series().diff()

        # For daily data, expect 1-3 days between bars (weekends)
        # For intraday, this varies too much to check reliably
        if len(df) > 5:
            median_diff = time_diffs.median()
            # If median is around 1 day (daily data), check for large gaps
            if pd.Timedelta(hours=12) < median_diff < pd.Timedelta(days=7):
                large_gaps = time_diffs[time_diffs > pd.Timedelta(days=14)]
                if len(large_gaps) > 0:
                    for idx, gap in large_gaps.head(3).items():
                        result.add_warning(
                            f"Data gap detected: {gap.days} days at {idx}"
                        )

    return result


def validate_or_raise(df: pd.DataFrame, ticker: str, min_bars: int = 30) -> ValidationResult:
    """
    Validate OHLCV data and raise exception if validation fails.

    Args:
        df: OHLCV DataFrame
        ticker: Ticker symbol
        min_bars: Minimum required bars

    Returns:
        ValidationResult if valid

    Raises:
        ValueError: If validation fails with errors
    """
    result = validate_ohlcv_data(df, ticker, min_bars=min_bars)

    if not result.is_valid:
        error_msg = f"Data validation failed for {ticker}:\n"
        for error in result.errors:
            error_msg += f"  - {error}\n"
        raise ValueError(error_msg)

    return result
