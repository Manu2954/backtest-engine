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
