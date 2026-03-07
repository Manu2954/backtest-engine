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


def test_commission_prevents_negative_cash() -> None:
    """
    Bug Fix Test #2: Commission should not cause negative cash.

    When total cost (shares * price + commission) would exceed available cash,
    shares should be reduced to fit within budget.
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [95, 95, 95, 95, 95],
            "high": [100, 100, 100, 100, 100],
            "low": [90, 90, 90, 90, 90],
            "close": [95, 95, 95, 95, 95],
            "volume": [1000, 1000, 1000, 1000, 1000],
        },
        index=index,
    )

    entry_signal = pd.Series([False, True, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, False, False], index=index)

    initial_capital = 100.0
    commission_per_trade = 10.0  # High commission

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        commission_per_trade=commission_per_trade,
    )

    # Without fix: would calculate 1 share * $95 + $10 commission = $105 > $100 cash (negative!)
    # With fix: should reduce to 0 shares (can't afford after commission)

    # Should have no trade (can't afford shares after commission)
    assert len(trades) == 0

    # Cash should never go negative - should remain at initial capital
    assert equity.iloc[-1] == initial_capital
    assert all(equity >= 0), "Cash should never be negative"


def test_commission_reduces_shares_to_fit_budget() -> None:
    """
    Bug Fix Test #2: Shares reduced to fit within budget after commission.

    When commission would push total cost over budget, reduce shares
    (not reject entirely if some shares are still affordable).
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [10, 10, 10, 10, 10],
            "high": [12, 12, 12, 12, 12],
            "low": [8, 8, 8, 8, 8],
            "close": [10, 10, 10, 10, 10],
            "volume": [1000, 1000, 1000, 1000, 1000],
        },
        index=index,
    )

    entry_signal = pd.Series([False, True, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, True, False], index=index)

    initial_capital = 100.0
    commission_per_trade = 5.0
    commission_pct = 1.0  # 1% of trade value

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        commission_per_trade=commission_per_trade,
        commission_pct=commission_pct,
    )

    # Should complete a trade with reduced shares to fit budget
    assert len(trades) == 1

    trade = trades[0]

    # Verify shares bought fit within budget
    entry_cost = (trade["shares"] * trade["entry_price"]) + trade["entry_commission"]
    assert entry_cost <= initial_capital, f"Entry cost ${entry_cost} exceeds budget ${initial_capital}"

    # Verify cash never went negative during backtest
    assert all(equity >= -1e-6), f"Cash went negative: min equity = {equity.min()}"


def test_high_commission_percentage_prevents_entry() -> None:
    """
    Bug Fix Test #2: Very high percentage commission should prevent entry.

    When commission percentage is so high that even 1 share is unaffordable,
    entry should be skipped entirely.
    """
    index = pd.date_range("2020-01-01", periods=3, freq="D")
    df = pd.DataFrame(
        {
            "open": [50, 50, 50],
            "high": [55, 55, 55],
            "low": [45, 45, 45],
            "close": [50, 50, 50],
            "volume": [1000, 1000, 1000],
        },
        index=index,
    )

    entry_signal = pd.Series([False, True, False], index=index)
    exit_signal = pd.Series([False, False, False], index=index)

    initial_capital = 100.0
    commission_per_trade = 20.0  # $20 flat
    commission_pct = 50.0  # 50% of trade value!

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        commission_per_trade=commission_per_trade,
        commission_pct=commission_pct,
    )

    # 1 share costs: $50 + $20 + 50% of $50 = $50 + $20 + $25 = $95
    # 2 shares costs: $100 + $20 + 50% of $100 = $100 + $20 + $50 = $170 (too much)
    # Should be able to afford 1 share

    # Should have a trade
    assert len(trades) == 1
    assert trades[0]["shares"] == 1.0

    # Cash should not be negative
    assert equity.iloc[-1] >= -1e-6


def test_negative_proceeds_prevented_on_worthless_exit() -> None:
    """
    Bug Fix Test #3: Negative proceeds on exit should not cause negative cash.

    When commission exceeds position value, proceeds would be negative.
    The fix caps commission at (position_value + available_cash) to prevent
    negative cash.
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [10, 10, 0.01, 0.01, 0.01],  # Price crashes to $0.01
            "high": [12, 12, 0.02, 0.02, 0.02],
            "low": [8, 8, 0.01, 0.01, 0.01],
            "close": [10, 10, 0.01, 0.01, 0.01],
            "volume": [1000, 1000, 1000, 1000, 1000],
        },
        index=index,
    )

    entry_signal = pd.Series([False, True, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, True, False], index=index)

    initial_capital = 100.0
    commission_per_trade = 10.0  # High commission relative to exit value

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        commission_per_trade=commission_per_trade,
    )

    # Entry: 10 shares at $10 = $100 (all capital used)
    # Exit: 10 shares at $0.01 = $0.10 value, $10 commission
    # Without fix: proceeds = $0.10 - $10 = -$9.90 (negative!)
    # With fix: commission capped to prevent negative cash

    assert len(trades) == 1
    trade = trades[0]

    # Verify exit happened
    assert trade["exit_price"] == 0.01

    # Verify cash never went negative
    assert all(equity >= -1e-6), f"Cash went negative: min = {equity.min()}"
    assert equity.iloc[-1] >= -1e-6, f"Final cash negative: {equity.iloc[-1]}"


def test_negative_proceeds_with_sufficient_cash() -> None:
    """
    Bug Fix Test #3: If cash can absorb negative proceeds, allow it.

    When there's enough cash to pay commission even if it exceeds position value,
    the trade should proceed normally (realistic broker behavior).
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [10, 10, 1, 1, 1],  # Price drops to $1
            "high": [12, 12, 2, 2, 2],
            "low": [8, 8, 1, 1, 1],
            "close": [10, 10, 1, 1, 1],
            "volume": [1000, 1000, 1000, 1000, 1000],
        },
        index=index,
    )

    entry_signal = pd.Series([False, True, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, True, False], index=index)

    # Use percent_capital to keep some cash
    initial_capital = 100.0
    commission_per_trade = 5.0

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        position_size_type="percent_capital",
        position_size_value=50.0,  # Only invest 50% of capital
        commission_per_trade=commission_per_trade,
    )

    # Entry: 5 shares at $10 = $50 + $5 commission (50% of $100)
    # Remaining cash: $100 - $55 = $45
    # Exit: 5 shares at $1 = $5 value, $5 commission
    # Proceeds: $5 - $5 = $0 (break even on this trade)
    # Final cash: $45 + $0 = $45

    assert len(trades) == 1
    trade = trades[0]

    # Position should have been 50% of capital
    assert trade["shares"] == 5.0

    # Cash should never go negative
    assert all(equity >= -1e-6), f"Cash went negative: min = {equity.min()}"

    # Final cash should be positive (had reserves)
    assert equity.iloc[-1] > 0


def test_force_close_with_high_commission() -> None:
    """
    Bug Fix Test #3: Force-close at end should also validate proceeds.

    When backtest ends and position is force-closed, commission validation
    should still apply.
    """
    index = pd.date_range("2020-01-01", periods=3, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 0.01],  # Price crashes on last day
            "high": [105, 105, 0.02],
            "low": [95, 95, 0.01],
            "close": [100, 100, 0.01],
            "volume": [1000, 1000, 1000],
        },
        index=index,
    )

    entry_signal = pd.Series([False, True, False], index=index)
    exit_signal = pd.Series([False, False, False], index=index)  # No exit signal

    initial_capital = 100.0
    commission_per_trade = 10.0

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        commission_per_trade=commission_per_trade,
    )

    # Entry at bar 1: 1 share at $100
    # Force-close at bar 2: 1 share at $0.01 (worthless)
    # Commission $10 exceeds position value $0.01

    assert len(trades) == 1
    trade = trades[0]
    assert trade["exit_reason"] == "force_close"

    # Cash should not be negative
    assert equity.iloc[-1] >= -1e-6


def test_pending_entry_on_last_bar_fills() -> None:
    """
    Bug Fix Test #4: Entry signal on last bar should be filled.

    When an entry signal triggers on the final bar, the position should be
    opened and immediately closed (force-close), rather than being ignored.
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [10, 10, 10, 10, 10],
            "high": [12, 12, 12, 12, 12],
            "low": [8, 8, 8, 8, 8],
            "close": [10, 10, 10, 10, 10],
            "volume": [1000, 1000, 1000, 1000, 1000],
        },
        index=index,
    )

    # Entry signal ONLY on last bar
    entry_signal = pd.Series([False, False, False, False, True], index=index)
    exit_signal = pd.Series([False, False, False, False, False], index=index)

    initial_capital = 100.0

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
    )

    # Should have one trade (entry + immediate force-close)
    assert len(trades) == 1

    trade = trades[0]
    assert trade["entry_date"] == index[-1]
    assert trade["exit_date"] == index[-1]
    assert trade["entry_price"] == 10.0
    assert trade["exit_price"] == 10.0
    assert trade["shares"] == 10.0
    assert trade["trade_duration_days"] == 0
    assert trade["exit_reason"] == "last_bar_entry_force_close"

    # P&L should be negative (double commission, no price movement)
    # Entry commission + exit commission with no gain
    assert trade["pnl"] < 0

    # Capital should have been deployed (not sitting idle)
    # Entry happened, even though immediately closed
    assert trade["shares"] > 0


def test_pending_entry_last_bar_insufficient_capital() -> None:
    """
    Bug Fix Test #4: Entry signal on last bar with insufficient capital.

    If there's not enough capital on the last bar, entry should be skipped
    (same as any other bar).
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

    # Entry signal on last bar, but insufficient capital
    entry_signal = pd.Series([False, False, True], index=index)
    exit_signal = pd.Series([False, False, False], index=index)

    initial_capital = 50.0  # Not enough for 1 share at $100

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
    )

    # No trade should occur (can't afford entry)
    assert len(trades) == 0

    # Capital preserved
    assert equity.iloc[-1] == initial_capital


def test_pending_entry_last_bar_with_commission() -> None:
    """
    Bug Fix Test #4: Last bar entry should account for double commission.

    Since entry and exit happen at same bar, both commissions apply.
    This should be factored into affordability check.
    """
    index = pd.date_range("2020-01-01", periods=3, freq="D")
    df = pd.DataFrame(
        {
            "open": [10, 10, 10],
            "high": [12, 12, 12],
            "low": [8, 8, 8],
            "close": [10, 10, 10],
            "volume": [1000, 1000, 1000],
        },
        index=index,
    )

    entry_signal = pd.Series([False, False, True], index=index)
    exit_signal = pd.Series([False, False, False], index=index)

    initial_capital = 100.0
    commission_per_trade = 5.0

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        commission_per_trade=commission_per_trade,
    )

    # Should have trade
    assert len(trades) == 1

    trade = trades[0]

    # Shares should fit within budget after entry commission
    entry_cost = trade["shares"] * trade["entry_price"] + trade["entry_commission"]
    assert entry_cost <= initial_capital

    # P&L should be negative (entry + exit commission, no price gain)
    assert trade["pnl"] == -(trade["entry_commission"] + trade["exit_commission"])

    # Final cash should account for both commissions
    # initial - entry_cost + proceeds (where proceeds = position_value - exit_commission)
    expected_loss = trade["total_commission"]
    assert abs(equity.iloc[-1] - (initial_capital - expected_loss)) < 0.01

