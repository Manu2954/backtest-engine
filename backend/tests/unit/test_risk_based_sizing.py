from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.state_machine import run_backtest  # noqa: E402


def make_df(rows: int = 100) -> pd.DataFrame:
    """Create test DataFrame with OHLCV data."""
    index = pd.date_range("2020-01-01", periods=rows, freq="D")
    close = pd.Series(range(rows), index=index, dtype="float") + 100.0
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
    return df


def test_risk_based_with_percentage_stop() -> None:
    """Test risk-based position sizing with percentage stop loss."""
    df = make_df(50)

    # Entry signal on bar 10
    entry_signal = pd.Series([False] * len(df), index=df.index)
    entry_signal.iloc[10] = True

    # Exit signal on bar 20
    exit_signal = pd.Series([False] * len(df), index=df.index)
    exit_signal.iloc[20] = True

    initial_capital = 10000.0
    risk_percent = 1.0  # Risk 1% per trade = $100
    stop_loss_pct = 5.0  # Stop at -5%

    trades, equity = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=initial_capital,
        position_size_type="risk_based",
        position_size_value=risk_percent,
        stop_loss_pct=stop_loss_pct,
        asset_class="CRYPTO",  # Allow fractional shares
    )

    # Should have 1 trade
    assert len(trades) == 1

    trade = trades[0]

    # Entry at bar 11 (next bar after signal)
    entry_price = trade["entry_price"]
    stop_price = entry_price * (1.0 - stop_loss_pct / 100.0)
    stop_distance = entry_price - stop_price

    # Expected shares: risk_amount / stop_distance
    risk_amount = initial_capital * (risk_percent / 100.0)  # $100
    expected_shares = risk_amount / stop_distance

    # Verify shares are correct (within small tolerance for floating point)
    assert abs(trade["shares"] - expected_shares) < 0.01

    # Verify position value is reasonable
    position_value = trade["shares"] * entry_price
    assert position_value > 0
    assert position_value <= initial_capital


def test_risk_based_with_dynamic_stop() -> None:
    """Test risk-based position sizing with dynamic stop column (ATR-based)."""
    df = make_df(50)

    # Add ATR-like stop column (5 points below close)
    df["atr_stop"] = df["close"] - 5.0

    # Entry signal on bar 10
    entry_signal = pd.Series([False] * len(df), index=df.index)
    entry_signal.iloc[10] = True

    # Exit signal on bar 20
    exit_signal = pd.Series([False] * len(df), index=df.index)
    exit_signal.iloc[20] = True

    initial_capital = 10000.0
    risk_percent = 2.0  # Risk 2% per trade = $200

    trades, equity = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=initial_capital,
        position_size_type="risk_based",
        position_size_value=risk_percent,
        dynamic_stop_column="atr_stop",
        asset_class="CRYPTO",
    )

    # Should have 1 trade
    assert len(trades) == 1

    trade = trades[0]

    # Entry at bar 11 (next bar after signal)
    entry_price = trade["entry_price"]
    stop_price = df.iloc[11]["atr_stop"]
    stop_distance = entry_price - stop_price

    # Expected shares: risk_amount / stop_distance
    risk_amount = initial_capital * (risk_percent / 100.0)  # $200
    expected_shares = risk_amount / stop_distance

    # Verify shares are correct
    assert abs(trade["shares"] - expected_shares) < 0.01


def test_risk_based_requires_stop_configuration() -> None:
    """Test that risk_based sizing requires stop loss configuration."""
    df = make_df(50)

    entry_signal = pd.Series([False] * len(df), index=df.index)
    entry_signal.iloc[10] = True

    exit_signal = pd.Series([False] * len(df), index=df.index)
    exit_signal.iloc[20] = True

    # Should raise error without stop configuration
    with pytest.raises(ValueError, match="requires either stop_loss_pct or dynamic_stop_column"):
        run_backtest(
            df=df,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            initial_capital=10000.0,
            position_size_type="risk_based",
            position_size_value=1.0,
            # No stop_loss_pct or dynamic_stop_column!
        )


def test_risk_based_invalid_risk_percent() -> None:
    """Test that risk_based sizing validates risk percentage."""
    df = make_df(50)

    entry_signal = pd.Series([False] * len(df), index=df.index)
    exit_signal = pd.Series([False] * len(df), index=df.index)

    # Risk percent too high
    with pytest.raises(ValueError, match="must be between 0 and 10"):
        run_backtest(
            df=df,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            initial_capital=10000.0,
            position_size_type="risk_based",
            position_size_value=15.0,  # 15% is too high
            stop_loss_pct=5.0,
        )

    # Risk percent negative
    with pytest.raises(ValueError, match="must be between 0 and 10"):
        run_backtest(
            df=df,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            initial_capital=10000.0,
            position_size_type="risk_based",
            position_size_value=-1.0,  # Negative
            stop_loss_pct=5.0,
        )


def test_risk_based_vs_percent_capital_comparison() -> None:
    """
    Compare risk-based sizing vs percent_capital in two volatility scenarios.

    Risk-based should maintain constant dollar risk, while percent_capital
    results in varying dollar risk based on stop distance.
    """
    initial_capital = 10000.0
    risk_percent = 1.0  # Risk 1% = $100

    # Scenario 1: Low volatility (tight stop at 3%)
    df1 = make_df(30)
    entry1 = pd.Series([False] * len(df1), index=df1.index)
    entry1.iloc[10] = True
    exit1 = pd.Series([False] * len(df1), index=df1.index)
    exit1.iloc[20] = True

    trades1, _ = run_backtest(
        df=df1,
        entry_signal=entry1,
        exit_signal=exit1,
        initial_capital=initial_capital,
        position_size_type="risk_based",
        position_size_value=risk_percent,
        stop_loss_pct=3.0,  # Tight stop
        asset_class="CRYPTO",
    )

    # Scenario 2: High volatility (wide stop at 10%)
    df2 = make_df(30)
    entry2 = pd.Series([False] * len(df2), index=df2.index)
    entry2.iloc[10] = True
    exit2 = pd.Series([False] * len(df2), index=df2.index)
    exit2.iloc[20] = True

    trades2, _ = run_backtest(
        df=df2,
        entry_signal=entry2,
        exit_signal=exit2,
        initial_capital=initial_capital,
        position_size_type="risk_based",
        position_size_value=risk_percent,
        stop_loss_pct=10.0,  # Wide stop
        asset_class="CRYPTO",
    )

    # Both trades should exist
    assert len(trades1) == 1
    assert len(trades2) == 1

    # Calculate actual risk (stop distance × shares)
    entry_price1 = trades1[0]["entry_price"]
    stop_price1 = entry_price1 * (1.0 - 3.0 / 100.0)
    risk1 = (entry_price1 - stop_price1) * trades1[0]["shares"]

    entry_price2 = trades2[0]["entry_price"]
    stop_price2 = entry_price2 * (1.0 - 10.0 / 100.0)
    risk2 = (entry_price2 - stop_price2) * trades2[0]["shares"]

    # Both should risk approximately $100 (1% of $10k)
    target_risk = initial_capital * (risk_percent / 100.0)
    assert abs(risk1 - target_risk) < 1.0  # Within $1
    assert abs(risk2 - target_risk) < 1.0  # Within $1

    # Position sizes should be different (larger for tight stop, smaller for wide stop)
    position_value1 = trades1[0]["shares"] * entry_price1
    position_value2 = trades2[0]["shares"] * entry_price2

    # Tight stop = larger position (more shares to maintain same risk)
    # Wide stop = smaller position (fewer shares to maintain same risk)
    assert position_value1 > position_value2


def test_risk_based_with_insufficient_capital() -> None:
    """Test risk-based sizing when calculated position exceeds available cash."""
    df = make_df(50)

    # Entry signal on bar 10
    entry_signal = pd.Series([False] * len(df), index=df.index)
    entry_signal.iloc[10] = True

    # Exit signal on bar 20
    exit_signal = pd.Series([False] * len(df), index=df.index)
    exit_signal.iloc[20] = True

    # Small capital with high risk percent and tight stop
    # This should result in calculated position > available cash
    initial_capital = 1000.0
    risk_percent = 5.0  # Risk 5% = $50
    stop_loss_pct = 0.5  # Very tight stop (0.5%)

    trades, equity = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=initial_capital,
        position_size_type="risk_based",
        position_size_value=risk_percent,
        stop_loss_pct=stop_loss_pct,
        asset_class="CRYPTO",
    )

    # Should still execute trade, but limited by available cash
    assert len(trades) == 1

    trade = trades[0]
    position_value = trade["shares"] * trade["entry_price"]

    # Position should not exceed initial capital
    assert position_value <= initial_capital
