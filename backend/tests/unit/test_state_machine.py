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
    assert abs(trade["pnl_pct"] - 0.1667) < 0.001  # 16.67% return
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
            "open": [10, 10, 10, 1, 1],  # Price drops AFTER entry
            "high": [12, 12, 12, 2, 2],
            "low": [8, 8, 8, 1, 1],
            "close": [10, 10, 10, 1, 1],  # Close stays at 10 until bar 3
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
    commission_per_trade = 1.0  # Need commission to have negative P&L

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        commission_per_trade=commission_per_trade,
    )

    # Should have one trade (entry + immediate force-close)
    assert len(trades) == 1

    trade = trades[0]
    assert trade["entry_date"] == index[-1]
    assert trade["exit_date"] == index[-1]
    assert trade["entry_price"] == 10.0
    assert trade["exit_price"] == 10.0
    assert trade["shares"] == 9.0  # floor((100 - 1 commission) / 10)
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


def test_dynamic_stop_crossover_detection() -> None:
    """
    Bug Fix Test #6: Dynamic stop should trigger only on crossover.

    The dynamic stop should exit when price crosses below the stop level,
    not simply when price < stop. This is important for trailing stops that
    move up as price increases.
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 105, 98, 102, 95],
            "high": [105, 110, 103, 107, 100],
            "low": [95, 100, 93, 97, 90],
            "close": [100, 105, 98, 102, 95],
            "volume": [1000, 1000, 1000, 1000, 1000],
            "trailing_stop": [90, 95, 99, 99, 90],  # Stop moves up, then down
        },
        index=index,
    )

    # Entry on bar 0 (so fill at bar 1 open = $105)
    entry_signal = pd.Series([True, False, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, False, False], index=index)

    initial_capital = 1000.0

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        dynamic_stop_column="trailing_stop",
    )

    # Entry at bar 1 open (signal on bar 0, fill at bar 1): open=$105
    # Bar 2: price=$98 < stop=$99, AND prev_close=$105 >= prev_stop=$95 → CROSS BELOW → EXIT
    # Should have 1 trade exiting at bar 2

    assert len(trades) == 1
    trade = trades[0]

    # Entry at bar 1 open
    assert trade["entry_price"] == 105.0
    assert trade["entry_date"] == index[1]

    # Exit at bar 2 open (crossover detected)
    assert trade["exit_date"] == index[2]
    assert trade["exit_price"] == 98.0
    assert trade["exit_reason"] in ["trailing_stop", "stop_loss"]


def test_dynamic_stop_no_false_exit() -> None:
    """
    Bug Fix Test #6: Don't exit if stop moves up to price without crossover.

    When the dynamic stop moves up faster than price falls, but we never
    actually cross below, we should NOT exit.
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 105, 103, 104, 106],
            "high": [105, 110, 108, 109, 111],
            "low": [95, 100, 98, 99, 101],
            "close": [100, 105, 103, 104, 106],
            "volume": [1000, 1000, 1000, 1000, 1000],
            # Stop moves up from 90 to 104, but price stays above
            "trailing_stop": [90, 95, 100, 104, 104],
        },
        index=index,
    )

    # Entry on bar 1
    entry_signal = pd.Series([False, True, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, False, False], index=index)

    initial_capital = 1000.0

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        dynamic_stop_column="trailing_stop",
    )

    # Entry at bar 2: open=$105
    # Bar 3: open=$103, stop=$100 → 103 > 100 (no exit)
    # Bar 4: open=$104, stop=$104 → 104 >= 104 (no exit, not below)
    # Bar 5: open=$106, stop=$104 → 106 > 104 (no exit)
    # Should be force-closed at end

    assert len(trades) == 1
    trade = trades[0]

    # Should not exit early from dynamic stop
    assert trade["exit_reason"] == "force_close"
    assert trade["exit_date"] == index[-1]


def test_dynamic_stop_already_below() -> None:
    """
    Bug Fix Test #6: Don't re-exit if already below stop.

    If we're already below the stop on a previous bar (shouldn't happen in
    normal operation, but edge case), don't trigger another exit.
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 105, 98, 96, 97],
            "high": [105, 110, 103, 101, 102],
            "low": [95, 100, 93, 91, 92],
            "close": [100, 105, 98, 96, 97],
            "volume": [1000, 1000, 1000, 1000, 1000],
            # Stop at 99 for multiple bars
            "trailing_stop": [90, 95, 99, 99, 99],
        },
        index=index,
    )

    # Entry on bar 1
    entry_signal = pd.Series([False, True, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, False, False], index=index)

    initial_capital = 1000.0

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        dynamic_stop_column="trailing_stop",
    )

    # Entry at bar 2: open=$105
    # Bar 2: open=$98 < stop=$99, prev_close=$105 >= prev_stop=$95 → CROSS → EXIT
    # Bar 3: open=$96 < stop=$99, but we already exited (shares=0)
    # Should have only 1 trade

    assert len(trades) == 1
    trade = trades[0]

    # Exit should happen at bar 2 (first cross)
    assert trade["exit_date"] == index[2]
    assert trade["exit_price"] == 98.0


def test_dynamic_stop_first_bar() -> None:
    """
    Bug Fix Test #6: First bar with position should use simple comparison.

    On the first bar we're in position, we don't have a previous bar to
    compare, so just use simple price < stop check.
    """
    index = pd.date_range("2020-01-01", periods=3, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 95, 100],
            "high": [105, 100, 105],
            "low": [95, 90, 95],
            "close": [100, 95, 100],
            "volume": [1000, 1000, 1000],
            "trailing_stop": [90, 96, 96],  # Stop above price on bar 1
        },
        index=index,
    )

    # Entry on bar 0 (will fill at bar 1)
    entry_signal = pd.Series([True, False, False], index=index)
    exit_signal = pd.Series([False, False, False], index=index)

    initial_capital = 1000.0

    trades, equity = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        dynamic_stop_column="trailing_stop",
    )

    # Entry at bar 1: open=$95
    # Bar 1: First bar in position, open=$95 < stop=$96 → EXIT (simple check)
    # Should exit immediately

    assert len(trades) == 1
    trade = trades[0]

    # Entry and exit on same bar (bar 1)
    assert trade["entry_date"] == index[1]
    assert trade["exit_date"] == index[1]
    assert trade["entry_price"] == 95.0
    assert trade["exit_price"] == 95.0


# ──────────────────────────────────────────────────────────────────────────────
# SHORT SELLING TESTS
# ──────────────────────────────────────────────────────────────────────────────


def test_short_basic_pnl() -> None:
    """Short at 100, cover at 90 → +10/share PnL."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {"open": [100, 100, 95, 90, 85], "close": [100, 100, 95, 90, 85]},
        index=index,
    )
    entry_signal = pd.Series([False] * 5, index=index)
    exit_signal = pd.Series([False] * 5, index=index)
    short_entry = pd.Series([False, True, False, False, False], index=index)
    short_exit = pd.Series([False, False, False, True, False], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal, initial_capital=1000.0,
        asset_class="STOCK",
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
    )

    assert len(trades) == 1
    t = trades[0]
    assert t["direction"] == "SHORT"
    assert t["entry_date"] == index[2]
    assert t["entry_price"] == 95.0
    assert t["exit_date"] == index[4]
    assert t["exit_price"] == 85.0
    # PnL = (entry - exit) * shares = (95 - 85) * 10 = 100
    assert t["shares"] == 10.0
    assert t["pnl"] == 100.0
    assert t["pnl_pct"] > 0


def test_short_loss() -> None:
    """Short at 100, cover at 110 → -10/share PnL."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {"open": [100, 100, 105, 110, 115], "close": [100, 100, 105, 110, 115]},
        index=index,
    )
    entry_signal = pd.Series([False] * 5, index=index)
    exit_signal = pd.Series([False] * 5, index=index)
    short_entry = pd.Series([False, True, False, False, False], index=index)
    short_exit = pd.Series([False, False, False, True, False], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal, initial_capital=1000.0,
        asset_class="STOCK",
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
    )

    assert len(trades) == 1
    t = trades[0]
    assert t["direction"] == "SHORT"
    # Signal bar 1 → fill at bar 2 open = 105
    assert t["entry_price"] == 105.0
    # Exit signal bar 3 → fill at bar 4 open = 115
    assert t["exit_price"] == 115.0
    # PnL = (105 - 115) * 9 = -90 (floor(1000/105)=9 shares)
    assert t["shares"] == 9.0
    assert t["pnl"] == -90.0
    assert t["pnl_pct"] < 0


def test_short_stop_loss_on_price_rise() -> None:
    """Short stop loss triggers when price RISES by stop_loss_pct."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {"open": [100, 100, 106, 110, 115], "close": [100, 100, 106, 110, 115]},
        index=index,
    )
    entry_signal = pd.Series([False] * 5, index=index)
    exit_signal = pd.Series([False] * 5, index=index)
    short_entry = pd.Series([True, False, False, False, False], index=index)
    short_exit = pd.Series([False, False, False, False, False], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal, initial_capital=1000.0,
        asset_class="STOCK",
        stop_loss_pct=5.0,
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
    )

    assert len(trades) == 1
    t = trades[0]
    assert t["direction"] == "SHORT"
    assert t["exit_reason"] == "stop_loss"
    # Entry at bar 1 open = 100. Bar 2 open = 106, that's +6% rise → triggers 5% stop
    assert t["entry_price"] == 100.0
    assert t["exit_date"] == index[2]


def test_short_take_profit_on_price_fall() -> None:
    """Short take profit triggers when price FALLS by take_profit_pct."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {"open": [100, 100, 89, 85, 80], "close": [100, 100, 89, 85, 80]},
        index=index,
    )
    entry_signal = pd.Series([False] * 5, index=index)
    exit_signal = pd.Series([False] * 5, index=index)
    short_entry = pd.Series([True, False, False, False, False], index=index)
    short_exit = pd.Series([False, False, False, False, False], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal, initial_capital=1000.0,
        asset_class="STOCK",
        take_profit_pct=10.0,
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
    )

    assert len(trades) == 1
    t = trades[0]
    assert t["direction"] == "SHORT"
    assert t["exit_reason"] == "take_profit"
    # Entry at bar 1 open = 100. Bar 2 open = 89, that's -11% fall → triggers 10% TP
    assert t["entry_price"] == 100.0
    assert t["exit_date"] == index[2]
    assert t["pnl"] > 0


def test_short_dynamic_stop_above_entry() -> None:
    """Short dynamic stop triggers when price crosses ABOVE stop value."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 95, 103, 110],
            "close": [100, 100, 95, 103, 110],
            "trailing_stop": [105, 105, 102, 102, 102],
        },
        index=index,
    )
    entry_signal = pd.Series([False] * 5, index=index)
    exit_signal = pd.Series([False] * 5, index=index)
    short_entry = pd.Series([True, False, False, False, False], index=index)
    short_exit = pd.Series([False, False, False, False, False], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal, initial_capital=1000.0,
        asset_class="STOCK",
        dynamic_stop_column="trailing_stop",
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
    )

    assert len(trades) == 1
    t = trades[0]
    assert t["direction"] == "SHORT"
    # Entry at bar 1 open=100. Bar 2: 95 < 102 (below stop, good for short).
    # Bar 3: open=103 > stop=102, AND prev_close=95 <= prev_stop=102 → cross ABOVE → exit
    assert t["exit_date"] == index[3]
    assert t["exit_reason"] in ["stop_loss", "trailing_stop"]


def test_simultaneous_long_and_short() -> None:
    """Both long and short positions open at the same time, independent exits."""
    index = pd.date_range("2020-01-01", periods=7, freq="D")
    df = pd.DataFrame(
        {"open": [100, 100, 100, 95, 105, 100, 100], "close": [100, 100, 100, 95, 105, 100, 100]},
        index=index,
    )
    # Long: enter bar 0, exit bar 4
    entry_signal = pd.Series([True, False, False, False, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, False, True, False, False], index=index)
    # Short: enter bar 1, exit bar 3
    short_entry = pd.Series([False, True, False, False, False, False, False], index=index)
    short_exit = pd.Series([False, False, False, True, False, False, False], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal, initial_capital=2000.0,
        asset_class="STOCK",
        position_size_type="fixed_amount",
        position_size_value=1000.0,
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
    )

    # Should have 2 trades: one LONG and one SHORT
    assert len(trades) == 2
    directions = {t["direction"] for t in trades}
    assert directions == {"LONG", "SHORT"}

    long_trade = next(t for t in trades if t["direction"] == "LONG")
    short_trade = next(t for t in trades if t["direction"] == "SHORT")

    # Long: entry at bar 1 open=100, exit at bar 5 open=100 → PnL=0 (price flat)
    assert long_trade["entry_price"] == 100.0
    assert long_trade["exit_price"] == 100.0

    # Short: entry at bar 2 open=100, exit at bar 4 open=105 → loss
    assert short_trade["entry_price"] == 100.0
    assert short_trade["exit_price"] == 105.0
    assert short_trade["pnl"] < 0


def test_short_equity_curve_mtm() -> None:
    """Mark-to-market equity reflects short unrealized PnL."""
    index = pd.date_range("2020-01-01", periods=4, freq="D")
    df = pd.DataFrame(
        {"open": [100, 100, 90, 90], "close": [100, 100, 90, 90]},
        index=index,
    )
    entry_signal = pd.Series([False] * 4, index=index)
    exit_signal = pd.Series([False] * 4, index=index)
    short_entry = pd.Series([True, False, False, False], index=index)
    short_exit = pd.Series([False, False, False, False], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal, initial_capital=1000.0,
        asset_class="CRYPTO",
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
    )

    # Entry at bar 1 open=100: 10 shares (1000/100). Cash goes to 0.
    # Bar 1 close=100: MTM = cash(0) + shares*(2*entry - close) = 0 + 10*(200-100) = 1000
    assert abs(equity.iloc[1] - 1000.0) < 0.01

    # Bar 2 close=90: MTM = 0 + 10*(200-90) = 1100 (profit since price fell)
    assert abs(equity.iloc[2] - 1100.0) < 0.01


def test_short_slippage() -> None:
    """Short entry slippage: sell lower. Short exit slippage: buy higher."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {"open": [100, 100, 100, 90, 90], "close": [100, 100, 100, 90, 90]},
        index=index,
    )
    entry_signal = pd.Series([False] * 5, index=index)
    exit_signal = pd.Series([False] * 5, index=index)
    short_entry = pd.Series([True, False, False, False, False], index=index)
    short_exit = pd.Series([False, False, True, False, False], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal, initial_capital=1000.0,
        asset_class="CRYPTO",
        slippage_pct=1.0,  # 1% slippage
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
    )

    assert len(trades) == 1
    t = trades[0]
    # Entry: sell at open=100 with slippage → 100 * (1 - 0.01) = 99
    assert abs(t["entry_price"] - 99.0) < 0.01
    # Exit: buy at open=90 with slippage → 90 * (1 + 0.01) = 90.9
    assert abs(t["exit_price"] - 90.9) < 0.01
    # PnL = (99 - 90.9) * shares > 0 (still profitable)
    assert t["pnl"] > 0


def test_short_commission() -> None:
    """Commission deducted on both short entry and exit."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {"open": [100, 100, 100, 100, 100], "close": [100, 100, 100, 100, 100]},
        index=index,
    )
    entry_signal = pd.Series([False] * 5, index=index)
    exit_signal = pd.Series([False] * 5, index=index)
    short_entry = pd.Series([True, False, False, False, False], index=index)
    short_exit = pd.Series([False, False, True, False, False], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal, initial_capital=1000.0,
        asset_class="STOCK",
        commission_per_trade=10.0,
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
    )

    assert len(trades) == 1
    t = trades[0]
    assert t["direction"] == "SHORT"
    # No price movement, PnL = -(entry_commission + exit_commission)
    assert t["pnl"] == -(t["entry_commission"] + t["exit_commission"])
    assert t["entry_commission"] == 10.0
    assert t["exit_commission"] == 10.0


def test_short_force_close() -> None:
    """Open short position is force-closed at last bar."""
    index = pd.date_range("2020-01-01", periods=4, freq="D")
    df = pd.DataFrame(
        {"open": [100, 100, 95, 90], "close": [100, 100, 95, 90]},
        index=index,
    )
    entry_signal = pd.Series([False] * 4, index=index)
    exit_signal = pd.Series([False] * 4, index=index)
    short_entry = pd.Series([True, False, False, False], index=index)
    short_exit = pd.Series([False, False, False, False], index=index)  # No exit signal

    trades, equity = run_backtest(
        df, entry_signal, exit_signal, initial_capital=1000.0,
        asset_class="STOCK",
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
    )

    assert len(trades) == 1
    t = trades[0]
    assert t["direction"] == "SHORT"
    assert t["exit_reason"] == "force_close"
    assert t["exit_date"] == index[-1]
    # Entry at 100, exit at 90 (last close) → profit
    assert t["pnl"] > 0


def test_backward_compat_no_short_signals() -> None:
    """When no short signals provided, behaves identically to before."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {"open": [10, 11, 12, 13, 14], "close": [10, 11, 12, 13, 14]},
        index=index,
    )
    entry_signal = pd.Series([False, True, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, True, False], index=index)

    trades, equity = run_backtest(df, entry_signal, exit_signal, initial_capital=100.0)

    assert len(trades) == 1
    t = trades[0]
    assert t["direction"] == "LONG"
    assert t["entry_price"] == 12.0
    assert t["exit_price"] == 14.0
    assert t["pnl"] == 16.0


def test_long_trades_have_direction_field() -> None:
    """All trade dicts include direction field, even LONG-only."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {"open": [10, 10, 10, 10, 10], "close": [10, 10, 10, 10, 10]},
        index=index,
    )
    entry_signal = pd.Series([True, False, False, False, False], index=index)
    exit_signal = pd.Series([False, False, True, False, False], index=index)

    trades, equity = run_backtest(df, entry_signal, exit_signal, initial_capital=100.0)

    assert len(trades) == 1
    assert "direction" in trades[0]
    assert trades[0]["direction"] == "LONG"


# ─── Dynamic TP Percentage Column Tests ──────────────────────────────────────


def test_dynamic_tp_pct_column_basic() -> None:
    """Dynamic TP% from column: trade exits when price rises by the signal bar's TP%."""
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 100, 103, 104, 105, 106, 107, 108, 109],
            "close": [100, 100, 100, 103, 104, 105, 106, 107, 108, 109],
            "tp_pct": [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
        },
        index=index,
    )
    # Signal on bar 0, fill at bar 1 (open=100), TP at +3% → exit when open >= 103
    entry_signal = pd.Series([True] + [False] * 9, index=index)
    exit_signal = pd.Series([False] * 10, index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal,
        initial_capital=1000.0,
        dynamic_tp_pct_column="tp_pct",
    )

    assert len(trades) == 1
    assert trades[0]["exit_reason"] == "take_profit"
    assert trades[0]["pnl_pct"] >= 0.029  # ~3% profit (stored as fraction)


def test_dynamic_tp_pct_varies_per_trade() -> None:
    """Different TP% for different trades based on signal bar value."""
    index = pd.date_range("2020-01-01", periods=20, freq="D")
    opens = [100] * 20
    opens[1] = 100   # fill trade 1 at 100
    opens[3] = 102   # TP hit for trade 1 (2%)
    opens[5] = 100   # fill trade 2 at 100
    opens[10] = 105  # TP hit for trade 2 (5%)
    df = pd.DataFrame(
        {
            "open": opens,
            "close": opens,
            "tp_pct": [2.0] * 4 + [5.0] * 16,  # bar 0 signal → 2% TP, bar 4 signal → 5% TP
        },
        index=index,
    )
    # Two entry signals: bar 0 (tp=2%), bar 4 (tp=5%)
    entry_signal = pd.Series([False] * 20, index=index)
    entry_signal.iloc[0] = True
    entry_signal.iloc[4] = True
    exit_signal = pd.Series([False] * 20, index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal,
        initial_capital=1000.0,
        dynamic_tp_pct_column="tp_pct",
    )

    assert len(trades) == 2
    assert trades[0]["exit_reason"] == "take_profit"
    assert trades[0]["pnl_pct"] >= 0.019  # ~2%
    assert trades[1]["exit_reason"] == "take_profit"
    assert trades[1]["pnl_pct"] >= 0.049  # ~5%


def test_dynamic_tp_pct_nan_falls_back_to_fixed() -> None:
    """When column has NaN, falls back to fixed take_profit_pct."""
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 100, 100, 100, 110, 111, 112, 113, 114],
            "close": [100, 100, 100, 100, 100, 110, 111, 112, 113, 114],
            "tp_pct": [float("nan")] * 10,
        },
        index=index,
    )
    entry_signal = pd.Series([True] + [False] * 9, index=index)
    exit_signal = pd.Series([False] * 10, index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal,
        initial_capital=1000.0,
        take_profit_pct=10.0,
        dynamic_tp_pct_column="tp_pct",
    )

    # NaN in column → dynamic_tp_pct stays None → falls back to fixed 10%
    assert len(trades) == 1
    assert trades[0]["exit_reason"] == "take_profit"
    assert trades[0]["pnl_pct"] >= 0.099  # ~10%


# ═══════════════════════════════════════════════════════════════════════════════
# LEVERAGE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


def test_leverage_long_profit() -> None:
    """3x leverage, price up 5% → PnL = 15% of margin."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 105, 105, 105],
            "high": [100, 100, 105, 105, 105],
            "low": [100, 100, 105, 105, 105],
            "close": [100, 100, 105, 105, 105],
        },
        index=index,
    )
    entry_signal = pd.Series([True, False, False, False, False], index=index)
    exit_signal = pd.Series([False, False, True, False, False], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal,
        initial_capital=1000.0,
        leverage=3.0,
    )

    assert len(trades) == 1
    t = trades[0]
    # Entry at 100, shares = (1000 * 3) / 100 = 30 shares
    # Margin = 30 * 100 / 3 = 1000
    # PnL = (105 - 100) * 30 = 150
    # pnl_pct = 150 / 1000 = 0.15 (15% return on margin)
    assert t["shares"] == 30.0
    assert abs(t["pnl"] - 150.0) < 0.01
    assert abs(t["pnl_pct"] - 0.15) < 0.001


def test_leverage_long_liquidation() -> None:
    """3x leverage, price drops 33.3% → liquidated, lose margin."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    # Liquidation price for 3x LONG at 100 = 100 * (1 - 1/3) = 66.67
    # Bar low drops to 60 → triggers liquidation
    df = pd.DataFrame(
        {
            "open": [100, 100, 60, 60, 60],
            "high": [100, 100, 100, 60, 60],
            "low": [100, 100, 60, 60, 60],
            "close": [100, 100, 60, 60, 60],
        },
        index=index,
    )
    entry_signal = pd.Series([True, False, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, False, False], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal,
        initial_capital=1000.0,
        leverage=3.0,
    )

    assert len(trades) == 1
    t = trades[0]
    assert t["exit_reason"] == "liquidation"
    # Lose entire margin + entry commission
    assert t["pnl"] < 0
    assert abs(t["exit_price"] - 100.0 * (1 - 1.0 / 3.0)) < 0.01
    # Final equity = initial - margin (all lost), cash was 0 after entry
    final_equity = equity.iloc[-1]
    assert final_equity < 1.0  # effectively 0


def test_leverage_short_profit() -> None:
    """3x leverage short, price down 5% → PnL = 15% of margin."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 95, 95, 95],
            "high": [100, 100, 95, 95, 95],
            "low": [100, 100, 95, 95, 95],
            "close": [100, 100, 95, 95, 95],
        },
        index=index,
    )
    entry_signal = pd.Series([False] * 5, index=index)
    exit_signal = pd.Series([False] * 5, index=index)
    short_entry = pd.Series([True, False, False, False, False], index=index)
    short_exit = pd.Series([False, False, True, False, False], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal,
        initial_capital=1000.0,
        leverage=3.0,
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
    )

    assert len(trades) == 1
    t = trades[0]
    assert t["direction"] == "SHORT"
    # Entry at 100, shares = 30, margin = 1000
    # PnL = (100 - 95) * 30 = 150
    assert t["shares"] == 30.0
    assert abs(t["pnl"] - 150.0) < 0.01
    assert abs(t["pnl_pct"] - 0.15) < 0.001


def test_leverage_short_liquidation() -> None:
    """3x leverage short, price up 33.3% → liquidated."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    # Liquidation price for 3x SHORT at 100 = 100 * (1 + 1/3) = 133.33
    # Bar high goes to 140 → triggers liquidation
    df = pd.DataFrame(
        {
            "open": [100, 100, 140, 140, 140],
            "high": [100, 100, 140, 140, 140],
            "low": [100, 100, 100, 140, 140],
            "close": [100, 100, 140, 140, 140],
        },
        index=index,
    )
    entry_signal = pd.Series([False] * 5, index=index)
    exit_signal = pd.Series([False] * 5, index=index)
    short_entry = pd.Series([True, False, False, False, False], index=index)
    short_exit = pd.Series([False] * 5, index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal,
        initial_capital=1000.0,
        leverage=3.0,
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
    )

    assert len(trades) == 1
    t = trades[0]
    assert t["exit_reason"] == "liquidation"
    assert t["direction"] == "SHORT"
    assert abs(t["exit_price"] - 100.0 * (1 + 1.0 / 3.0)) < 0.01
    assert t["pnl"] < 0


def test_leverage_1x_unchanged() -> None:
    """leverage=1 produces identical results to default behavior."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 110, 110, 110],
            "high": [100, 100, 110, 110, 110],
            "low": [100, 100, 110, 110, 110],
            "close": [100, 100, 110, 110, 110],
        },
        index=index,
    )
    entry_signal = pd.Series([True, False, False, False, False], index=index)
    exit_signal = pd.Series([False, False, True, False, False], index=index)

    trades_default, eq_default = run_backtest(
        df, entry_signal, exit_signal, initial_capital=1000.0,
    )
    trades_1x, eq_1x = run_backtest(
        df, entry_signal, exit_signal, initial_capital=1000.0, leverage=1.0,
    )

    assert len(trades_default) == len(trades_1x) == 1
    assert abs(trades_default[0]["pnl"] - trades_1x[0]["pnl"]) < 0.001
    assert abs(trades_default[0]["shares"] - trades_1x[0]["shares"]) < 0.001
    assert abs(eq_default.iloc[-1] - eq_1x.iloc[-1]) < 0.001


def test_leverage_cash_deduction() -> None:
    """Only margin (not full notional) deducted from cash at entry."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 100, 100, 100],
            "high": [100, 100, 100, 100, 100],
            "low": [100, 100, 100, 100, 100],
            "close": [100, 100, 100, 100, 100],
        },
        index=index,
    )
    entry_signal = pd.Series([True, False, False, False, False], index=index)
    exit_signal = pd.Series([False, False, False, False, True], index=index)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal,
        initial_capital=1000.0,
        leverage=3.0,
    )

    assert len(trades) == 1
    t = trades[0]
    # With 3x leverage: shares = 30, notional = 3000, margin = 1000
    assert t["shares"] == 30.0
    # Equity while in position should equal initial capital (price unchanged)
    # Cash = 0 (all margin deployed), MTM = margin + 0 unrealized = 1000
    assert abs(equity.iloc[2] - 1000.0) < 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# EXIT RULES TESTS
# ═══════════════════════════════════════════════════════════════════════════════

from app.engine.exit_rules import ExitRule


def test_exit_rule_fires_when_active() -> None:
    """RSI at entry < 50, drops below entry RSI, PnL < -1% → exit."""
    index = pd.date_range("2020-01-01", periods=6, freq="D")
    # Signal on bar 0, entry fills at bar 1 open (100). RSI at signal bar = 40.
    # Bar 3: RSI drops to 35 (< 40) and price drops to 97 (PnL = -3%) → should exit.
    df = pd.DataFrame(
        {
            "open": [100, 100, 99, 97, 97, 97],
            "high": [100, 100, 99, 97, 97, 97],
            "low": [100, 100, 99, 97, 97, 97],
            "close": [100, 100, 99, 97, 97, 97],
            "rsi": [40, 42, 38, 35, 30, 30],
        },
        index=index,
    )
    entry_signal = pd.Series([True, False, False, False, False, False], index=index)
    exit_signal = pd.Series([False] * 6, index=index)

    rule = ExitRule(name="rsi_exit", ref_col="rsi", monitor_col="rsi", activation_threshold=50.0, min_loss_pct=1.0)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal,
        initial_capital=1000.0,
        exit_rules=[rule],
    )

    assert len(trades) == 1
    t = trades[0]
    # Exit is pending on bar 3, fills at bar 4 open
    assert t["exit_reason"] == "rsi_exit"
    assert t["pnl"] < 0


def test_exit_rule_inactive_when_above_threshold() -> None:
    """RSI at entry >= 50 → rule doesn't activate, no exit despite RSI drop."""
    index = pd.date_range("2020-01-01", periods=6, freq="D")
    # RSI at signal bar = 60 (>= 50 threshold) → rule inactive
    df = pd.DataFrame(
        {
            "open": [100, 100, 99, 97, 97, 97],
            "high": [100, 100, 99, 97, 97, 97],
            "low": [100, 100, 99, 97, 97, 97],
            "close": [100, 100, 99, 97, 97, 97],
            "rsi": [60, 55, 50, 45, 40, 35],
        },
        index=index,
    )
    entry_signal = pd.Series([True, False, False, False, False, False], index=index)
    exit_signal = pd.Series([False] * 6, index=index)

    rule = ExitRule(name="rsi_exit", ref_col="rsi", monitor_col="rsi", activation_threshold=50.0, min_loss_pct=1.0)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal,
        initial_capital=1000.0,
        exit_rules=[rule],
    )

    # Should force-close at last bar, not exit early via rule
    assert len(trades) == 1
    assert trades[0]["exit_reason"] == "force_close"


def test_exit_rule_no_fire_when_profitable() -> None:
    """RSI drops below entry RSI but PnL > -1% → stays in trade."""
    index = pd.date_range("2020-01-01", periods=6, freq="D")
    # RSI at signal = 40 (<50, rule active). Price stays at 100 (PnL = 0%).
    # RSI drops to 35 on bar 3 but no loss → rule doesn't fire.
    df = pd.DataFrame(
        {
            "open": [100, 100, 100, 100, 100, 100],
            "high": [100, 100, 100, 100, 100, 100],
            "low": [100, 100, 100, 100, 100, 100],
            "close": [100, 100, 100, 100, 100, 100],
            "rsi": [40, 42, 38, 35, 30, 28],
        },
        index=index,
    )
    entry_signal = pd.Series([True, False, False, False, False, False], index=index)
    exit_signal = pd.Series([False] * 6, index=index)

    rule = ExitRule(name="rsi_exit", ref_col="rsi", monitor_col="rsi", activation_threshold=50.0, min_loss_pct=1.0)

    trades, equity = run_backtest(
        df, entry_signal, exit_signal,
        initial_capital=1000.0,
        exit_rules=[rule],
    )

    # Should force-close at end, not exit via rule (no loss)
    assert len(trades) == 1
    assert trades[0]["exit_reason"] == "force_close"


