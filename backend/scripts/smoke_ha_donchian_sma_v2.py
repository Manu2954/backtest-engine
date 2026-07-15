"""
Heikin Ashi + Donchian Channel + SMA50 Strategy (V2 - Uses Engine)

This version uses run_backtest() directly instead of a custom loop,
ensuring proper next-bar fills without lookahead bias.
"""
from __future__ import annotations

import sys
from pathlib import Path
from collections import Counter

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv
from app.engine.indicator_layer import compute_indicators, trim_warmup_period
from app.engine.condition_engine import evaluate_conditions
from app.engine.state_machine import run_backtest
from app.engine.report_generator import generate_report


TICKER = "BTCUSDT"
START = "2026-01-01"
END = "2026-12-31"
RESOLUTION = "1h"
ASSET_CLASS = "CRYPTO"
INITIAL_CAPITAL = 100.0
LEVERAGE = 5.0
COMMISSION_PCT = 0.1


def main():
    print("=" * 80)
    print("HA + Donchian + SMA50 (V2 - Engine-based)")
    print("=" * 80)
    print(f"Ticker: {TICKER} | Period: {START} to {END} | Leverage: {LEVERAGE}x")
    print()

    # Fetch and prepare data
    df = fetch_ohlcv(TICKER, START, END, RESOLUTION, ASSET_CLASS)
    print(f"Loaded {len(df)} bars")

    indicators = [
        {"indicator_type": "DONCHIAN", "alias": "dc_20", "params": {"period": 20}},
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    ]
    df = compute_indicators(df, indicators, strategy_chart_type="heikinashi")

    # Restore raw prices for fills
    df["open"] = df["raw_open"]
    df["high"] = df["raw_high"]
    df["low"] = df["raw_low"]
    df["close"] = df["raw_close"]

    df, warmup = trim_warmup_period(df)
    print(f"After warmup trim: {len(df)} bars")

    # Evaluate signals via condition engine
    entry_group = {
        "logic": "AND",
        "conditions": [{
            "left_operand_type": "INDICATOR",
            "left_operand_value": "dc_20_mid",
            "operator": "CROSSES_ABOVE",
            "right_operand_type": "INDICATOR",
            "right_operand_value": "sma_50",
        }],
    }
    exit_group = {
        "logic": "AND",
        "conditions": [{
            "left_operand_type": "INDICATOR",
            "left_operand_value": "dc_20_mid",
            "operator": "CROSSES_BELOW",
            "right_operand_type": "INDICATOR",
            "right_operand_value": "sma_50",
        }],
    }

    entry_signal = evaluate_conditions(df, entry_group)
    exit_signal = evaluate_conditions(df, exit_group)
    short_entry_signal = exit_signal.copy()
    short_exit_signal = entry_signal.copy()

    print(f"Entry signals: {entry_signal.sum()} | Exit signals: {exit_signal.sum()}")
    print()

    # Run backtest using engine
    trades, equity = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=INITIAL_CAPITAL,
        asset_class=ASSET_CLASS,
        leverage=LEVERAGE,
        commission_pct=COMMISSION_PCT,
        enable_counter_trades=True,
        counter_tp_multiplier=1.5,
        short_entry_signal=short_entry_signal,
        short_exit_signal=short_exit_signal,
    )

    # Results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total trades: {len(trades)}")

    reasons = Counter(t["exit_reason"] for t in trades)
    directions = Counter(t["direction"] for t in trades)
    print(f"Exit reasons: {dict(reasons)}")
    print(f"Directions: {dict(directions)}")

    report = generate_report(trades, equity, INITIAL_CAPITAL)
    print(f"Total return: {report['total_return_pct']:.2f}%")
    print(f"Final equity: ${equity.iloc[-1]:.2f}")
    print(f"Win rate: {report['win_rate']:.1f}%")
    print(f"Sharpe: {report['sharpe_ratio']:.2f}")

    # Show first 20 trades
    print()
    print("First 20 trades:")
    for i, t in enumerate(trades[:20]):
        tp = "**TP**" if "take_profit" in t["exit_reason"] else ""
        print(f'{i+1:2}. {t["direction"]:5} {str(t["entry_date"])[5:16]} -> {str(t["exit_date"])[5:16]} | {t["pnl"]:8.2f} | {t["exit_reason"]} {tp}')


if __name__ == "__main__":
    main()
