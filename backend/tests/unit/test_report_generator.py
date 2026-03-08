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
    assert report["avg_trade_duration"] == 1
    assert report["max_drawdown_pct"] <= 0


def test_report_empty() -> None:
    equity = pd.Series([], dtype=float)
    report = generate_report([], equity, initial_capital=100.0)

    assert report["total_trades"] == 0
    assert report["total_return_pct"] == 0.0
    assert report["win_rate"] == 0.0
    assert report["profit_factor"] == 0.0
    assert report["avg_trade_duration"] == 0.0


def test_perfect_strategy_avg_win_loss() -> None:
    """
    Bug Fix Test #7: Perfect strategy (no losses) should return inf for avg_win_loss.

    When a strategy has 100% win rate (no losses), the avg_win_loss ratio
    should be infinity, not 0.0.
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

    # avg_win_loss should be infinity (no losses to divide by)
    assert report["avg_win_loss"] == float('inf')

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
