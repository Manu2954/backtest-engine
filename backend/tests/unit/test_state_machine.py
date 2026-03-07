from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.state_machine import run_backtest  # noqa: E402


def test_next_bar_fills_and_pnl() -> None:
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [10, 11, 12, 13, 14],
            "close": [10, 11, 12, 13, 14],
        },
        index=index,
    )
    entry_signal = pd.Series([False, True, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, True, False], index=index)

    trades, equity = run_backtest(df, entry_signal, exit_signal, initial_capital=100.0)

    assert len(trades) == 1
    trade = trades[0]
    assert trade["entry_date"] == index[2]
    assert trade["entry_price"] == 12.0
    assert trade["exit_date"] == index[4]
    assert trade["exit_price"] == 14.0
    assert trade["shares"] == 8.0  # floor(100/12)
    assert trade["pnl"] == 16.0
    assert trade["pnl_pct"] == 0.16
    assert trade["trade_duration_days"] == 2

    assert equity.iloc[-1] == 116.0


def test_monthly_contribution_applies_on_period_change() -> None:
    index = pd.date_range("2020-01-20", periods=20, freq="D")
    df = pd.DataFrame(
        {
            "open": [10.0] * len(index),
            "close": [10.0] * len(index),
        },
        index=index,
    )
    entry_signal = pd.Series([False] * len(index), index=index)
    exit_signal = pd.Series([False] * len(index), index=index)

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=100.0,
        periodic_contribution={"amount": 2000, "frequency": "monthly"},
    )

    assert trades == []
    # Contribution applies when month changes (Jan -> Feb) once.
    assert equity.iloc[-1] == 2100.0


def test_zero_shares_entry_skipped_no_commission_deducted() -> None:
    """
    Bug Fix Test: Zero-share entry should not deduct commission.

    When position sizing returns 0 shares (insufficient capital or fractional
    rounding to 0), the entry should be skipped entirely without deducting
    commission or modifying cash.
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 100, 100, 100],
            "high": [105, 105, 105, 105, 105],
            "low": [95, 95, 95, 95, 95],
            "close": [100, 100, 100, 100, 100],
            "volume": [1000, 1000, 1000, 1000, 1000],
        },
        index=index,
    )

    # Entry signal on bar 1, but only have $50 (can't buy even 1 share at $100)
    entry_signal = pd.Series([False, True, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, False, False], index=index)

    initial_capital = 50.0
    commission_per_trade = 5.0

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",  # Integer shares only
        commission_per_trade=commission_per_trade,
    )

    # Should have no trades (0 shares, so entry skipped)
    assert len(trades) == 0

    # Cash should be unchanged (commission not deducted)
    assert equity.iloc[-1] == initial_capital

    # All equity values should equal initial capital (no activity)
    assert all(equity == initial_capital)


def test_zero_shares_from_fractional_rounding() -> None:
    """
    Bug Fix Test: Fractional shares rounding to 0 should skip entry.

    For STOCK asset class, fractional shares are floored to integers.
    If this results in 0 shares, entry should be skipped.
    """
    index = pd.date_range("2020-01-01", periods=3, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 100],
            "high": [105, 105, 105],
            "low": [95, 95, 95],
            "close": [100, 100, 100],
            "volume": [1000, 1000, 1000],
        },
        index=index,
    )

    # Entry signal, but only $80 available (0.8 shares -> rounds to 0)
    entry_signal = pd.Series([False, True, False], index=index)
    exit_signal = pd.Series([False, False, False], index=index)

    initial_capital = 80.0

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",  # Integer shares only (0.8 -> 0)
    )

    # No trades should occur
    assert len(trades) == 0

    # Capital preserved
    assert equity.iloc[-1] == initial_capital

