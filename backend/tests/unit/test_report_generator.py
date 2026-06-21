from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.report_generator import generate_report  # noqa: E402


def test_report_basic_metrics() -> None:
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    equity = pd.Series([100, 110, 105, 115, 120], index=index)
    trade_log = [
        {
            "entry_date": index[0],
            "entry_price": 10.0,
            "exit_date": index[1],
            "exit_price": 11.0,
            "shares": 10.0,
            "pnl": 10.0,
            "pnl_pct": 0.10,
            "trade_duration_days": 1,
        },
        {
            "entry_date": index[2],
            "entry_price": 10.0,
            "exit_date": index[3],
            "exit_price": 9.0,
            "shares": 10.0,
            "pnl": -10.0,
            "pnl_pct": -0.10,
            "trade_duration_days": 1,
        },
    ]

    report = generate_report(trade_log, equity, initial_capital=100.0)

    assert report["total_trades"] == 2
    assert report["final_capital"] == 120.0
    assert report["total_return_pct"] == 20.0
    assert report["win_rate"] == 50.0
    assert report["profit_factor"] == 1.0
    assert report["avg_trade_duration_days"] == 1
    assert report["max_drawdown_pct"] <= 0


def test_report_empty() -> None:
    equity = pd.Series([], dtype=float)
    report = generate_report([], equity, initial_capital=100.0)

    assert report["total_trades"] == 0
    assert report["total_return_pct"] == 0.0
    assert report["win_rate"] == 0.0
    assert report["profit_factor"] == 0.0
    assert report["avg_trade_duration_days"] == 0.0


def test_perfect_strategy_avg_win_loss() -> None:
    """
    Bug Fix Test #7: Perfect strategy (no losses) should return 999999.0 for avg_win_loss.

    When a strategy has 100% win rate (no losses), the avg_win_loss ratio
    should be very large (999999.0), not 0.0 or infinity.
    Note: We use 999999.0 instead of infinity because PostgreSQL JSONB doesn't support inf.
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    equity = pd.Series([100, 110, 120, 130, 140], index=index)
    trade_log = [
        {
            "entry_date": index[0],
            "entry_price": 10.0,
            "exit_date": index[1],
            "exit_price": 11.0,
            "shares": 10.0,
            "pnl": 10.0,
            "pnl_pct": 0.10,
            "trade_duration_days": 1,
        },
        {
            "entry_date": index[2],
            "entry_price": 10.0,
            "exit_date": index[3],
            "exit_price": 12.0,
            "shares": 10.0,
            "pnl": 20.0,
            "pnl_pct": 0.20,
            "trade_duration_days": 1,
        },
    ]

    report = generate_report(trade_log, equity, initial_capital=100.0)

    # Should have 100% win rate
    assert report["win_rate"] == 100.0

    # avg_win_loss should be 999999.0 (no losses to divide by)
    # We use finite number instead of infinity for PostgreSQL JSONB compatibility
    assert report["avg_win_loss"] == 999999.0

    # avg_win should be calculated
    assert report["avg_win"] == 15.0  # (10 + 20) / 2

    # avg_loss should be 0 (no losses)
    assert report["avg_loss"] == 0.0


def test_no_trades_avg_win_loss() -> None:
    """
    Bug Fix Test #7: No trades should return 0.0 for avg_win_loss.
    """
    index = pd.date_range("2020-01-01", periods=3, freq="D")
    equity = pd.Series([100, 100, 100], index=index)
    trade_log = []

    report = generate_report(trade_log, equity, initial_capital=100.0)

    # No trades - should be 0
    assert report["avg_win_loss"] == 0.0
    assert report["avg_win"] == 0.0
    assert report["avg_loss"] == 0.0


def test_sortino_ratio_with_downside_volatility() -> None:
    """
    Test Sortino ratio calculation with both positive and negative returns.

    Sortino ratio should only penalize downside volatility, unlike Sharpe
    which penalizes all volatility equally.
    """
    # Create an equity curve with both up and down days
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    # Equity: 100 -> 102 -> 101 -> 103 -> 100 -> 105 -> 104 -> 108 -> 106 -> 110
    # This creates a mix of positive and negative daily returns
    equity = pd.Series([100, 102, 101, 103, 100, 105, 104, 108, 106, 110], index=index)
    trade_log = []

    report = generate_report(trade_log, equity, initial_capital=100.0)

    # Sortino ratio should be calculated (we have negative returns)
    assert report["sortino_ratio"] is not None
    assert isinstance(report["sortino_ratio"], float)
    # Should be a reasonable annualized value (positive given overall upward trend)
    assert report["sortino_ratio"] > 0


def test_sortino_ratio_no_negative_returns() -> None:
    """
    Test Sortino ratio when there are no negative daily returns.

    When a strategy never has a down day, downside deviation is zero,
    and Sortino should be None (undefined).
    """
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    # Monotonically increasing equity - no negative returns
    equity = pd.Series([100, 105, 110, 115, 120], index=index)
    trade_log = []

    report = generate_report(trade_log, equity, initial_capital=100.0)

    # No negative returns means sortino is undefined
    assert report["sortino_ratio"] is None


def test_sortino_ratio_empty_equity() -> None:
    """
    Test Sortino ratio with empty equity curve.
    """
    equity = pd.Series([], dtype=float)
    report = generate_report([], equity, initial_capital=100.0)

    # Empty equity means no returns to calculate
    assert report["sortino_ratio"] is None


def test_sortino_vs_sharpe_relationship() -> None:
    """
    Test that Sortino >= Sharpe when there is downside volatility.

    Sortino should typically be higher than Sharpe because it doesn't
    penalize upside volatility.
    """
    index = pd.date_range("2020-01-01", periods=20, freq="D")
    # Asymmetric returns: big gains, small losses
    # This should result in Sortino > Sharpe
    equity_values = [100]
    for i in range(19):
        if i % 3 == 0:
            # Small loss
            equity_values.append(equity_values[-1] * 0.99)
        else:
            # Bigger gain
            equity_values.append(equity_values[-1] * 1.03)

    equity = pd.Series(equity_values, index=index)
    trade_log = []

    report = generate_report(trade_log, equity, initial_capital=100.0)

    # Both should be calculable
    assert report["sharpe_ratio"] != 0.0
    assert report["sortino_ratio"] is not None

    # Sortino should be >= Sharpe for asymmetric positive returns
    # (upside vol doesn't penalize Sortino)
    assert report["sortino_ratio"] >= report["sharpe_ratio"]
