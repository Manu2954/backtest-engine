"""
Heikin Ashi + Donchian Channel + SMA50 Multi-Timeframe Confirmation Strategy

Strategy Logic:
  ENTRY (one trade per 4h cross):
    1. 4h: DC(20) mid crosses above/below SMA(50) → ARM signal
    2. 1h: Wait for DC(20) mid to cross in SAME direction → ENTER at next bar's open
    3. After entry, disarm - wait for next 4h cross for new trade

  EXIT:
    - 1h: DC(20) mid crosses in OPPOSITE direction → EXIT at next bar's open

  LONG:
    - ARM: 4h DC mid crosses ABOVE SMA50
    - CONFIRM: 1h DC mid crosses ABOVE SMA50 (while armed)
    - EXIT: 1h DC mid crosses BELOW SMA50

  SHORT:
    - ARM: 4h DC mid crosses BELOW SMA50
    - CONFIRM: 1h DC mid crosses BELOW SMA50 (while armed)
    - EXIT: 1h DC mid crosses ABOVE SMA50

  DISARM (without entry):
    - 1h cross in OPPOSITE direction disarms without entry
    - Re-arm possible within same 4h bar period

Indicators (all calculated on Heikin Ashi candles):
  - Heikin Ashi candles (smoothed price action) on both timeframes
  - Donchian Channel 20-period
  - SMA 50-period

Features:
  - 5x leverage with liquidation
  - Uses run_backtest() engine function
  - Uses evaluate_conditions() for signal generation
  - Fills happen at real OHLC prices

Usage:
  python scripts/smoke_ha_donchian_mtf_confirm.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv
from app.engine.indicator_layer import compute_indicators, trim_warmup_period
from app.engine.condition_engine import evaluate_conditions
from app.engine.state_machine import run_backtest
from app.engine.report_generator import generate_report


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TICKER = "BTCUSDT"
START = "2026-01-01"
END = "2027-01-01"
ASSET_CLASS = "CRYPTO"
INITIAL_CAPITAL = 100.0
LEVERAGE = 5.0

# Timeframes
TF_SIGNAL = "4h"    # Timeframe for ARM signal
TF_ENTRY = "1h"     # Timeframe for CONFIRM and trade execution

# Position sizing
POSITION_SIZE_TYPE = "percent_capital"
POSITION_SIZE_VALUE = 95.0  # 95% of capital per trade

# Risk management
COMMISSION_PCT = 0.1  # 0.1% commission


# ═══════════════════════════════════════════════════════════════════════════════
# CONDITION DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

# 4h ARM conditions (crossovers)
ARM_LONG_CONDITION = {
    "logic": "AND",
    "conditions": [
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "dc_20_mid",
            "operator": "CROSSES_ABOVE",
            "right_operand_type": "INDICATOR",
            "right_operand_value": "sma_50",
        }
    ]
}

ARM_SHORT_CONDITION = {
    "logic": "AND",
    "conditions": [
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "dc_20_mid",
            "operator": "CROSSES_BELOW",
            "right_operand_type": "INDICATOR",
            "right_operand_value": "sma_50",
        }
    ]
}

# 1h CONFIRM/EXIT conditions (crossovers)
CONFIRM_LONG_CONDITION = {
    "logic": "AND",
    "conditions": [
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "dc_20_mid",
            "operator": "CROSSES_ABOVE",
            "right_operand_type": "INDICATOR",
            "right_operand_value": "sma_50",
        }
    ]
}

CONFIRM_SHORT_CONDITION = {
    "logic": "AND",
    "conditions": [
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "dc_20_mid",
            "operator": "CROSSES_BELOW",
            "right_operand_type": "INDICATOR",
            "right_operand_value": "sma_50",
        }
    ]
}

# Exit conditions (opposite crosses)
EXIT_LONG_CONDITION = CONFIRM_SHORT_CONDITION  # Exit long on cross below
EXIT_SHORT_CONDITION = CONFIRM_LONG_CONDITION  # Exit short on cross above


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_ha_and_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Heikin Ashi candles and indicators (Donchian, SMA50)."""
    # Compute Heikin Ashi
    df = compute_indicators(df, [{"indicator_type": "HEIKINASHI", "alias": "ha", "params": {}}])

    # Replace OHLC with Heikin Ashi for indicator calculations
    df["open"] = df["ha_open"]
    df["high"] = df["ha_high"]
    df["low"] = df["ha_low"]
    df["close"] = df["ha_close"]

    # Compute indicators on HA candles
    df = compute_indicators(df, [
        {"indicator_type": "DONCHIAN", "alias": "dc_20", "params": {"period": 20}},
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    ])

    return df


def generate_mtf_signals(
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame,
    cross_above_1h: pd.Series,
    cross_below_1h: pd.Series,
    cross_above_4h: pd.Series,
    cross_below_4h: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Generate MTF-confirmed entry signals.

    Logic:
      - 4h cross ARMS a signal (checked on every 1h bar within that 4h period)
      - 1h cross in SAME direction CONFIRMS entry and disarms
      - 1h cross in OPPOSITE direction disarms without entry
      - This allows re-arming from the same 4h bar if disarmed by opposite 1h cross

    Returns:
      (long_entry, long_exit, short_entry, short_exit) signals on 1h timeframe
    """
    # Build 1h → 4h mapping
    df_4h_sorted = df_4h.sort_index()
    ts_1h_to_4h = {}
    for ts_1h in df_1h.index:
        valid_4h = df_4h_sorted.index[df_4h_sorted.index <= ts_1h]
        if len(valid_4h) > 0:
            ts_1h_to_4h[ts_1h] = valid_4h[-1]

    # Initialize signals
    long_entry = pd.Series(False, index=df_1h.index)
    short_entry = pd.Series(False, index=df_1h.index)
    long_exit = cross_below_1h.copy()   # Exit on 1h cross below
    short_exit = cross_above_1h.copy()  # Exit on 1h cross above

    # State
    armed_long = False
    armed_short = False

    for i, ts in enumerate(df_1h.index):
        ts_4h = ts_1h_to_4h.get(ts)

        # Check 4h crossovers - RE-ARM on every 1h bar within a 4h bar that has a cross
        # This allows re-arming after being disarmed by opposite 1h cross
        if ts_4h is not None and ts_4h in cross_above_4h.index:
            if cross_above_4h.loc[ts_4h]:
                armed_long = True
                armed_short = False
            elif cross_below_4h.loc[ts_4h]:
                armed_short = True
                armed_long = False

        # Check 1h confirmation
        if armed_long and cross_above_1h.iloc[i]:
            long_entry.iloc[i] = True
            armed_long = False  # Disarm after confirmation
        elif armed_short and cross_below_1h.iloc[i]:
            short_entry.iloc[i] = True
            armed_short = False  # Disarm after confirmation

        # Disarm on opposite 1h cross (without entry)
        if armed_long and cross_below_1h.iloc[i]:
            armed_long = False
        if armed_short and cross_above_1h.iloc[i]:
            armed_short = False

    return long_entry, long_exit, short_entry, short_exit


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print(f"HA + Donchian + SMA50 MTF Confirmation Strategy")
    print("=" * 80)
    print(f"Ticker: {TICKER}")
    print(f"Period: {START} to {END}")
    print(f"Signal TF: {TF_SIGNAL} | Entry TF: {TF_ENTRY}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print(f"Leverage: {LEVERAGE}x")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. FETCH DATA
    # ──────────────────────────────────────────────────────────────────────────
    print("📊 Fetching OHLCV data...")
    df_1h_raw = fetch_ohlcv(TICKER, START, END, TF_ENTRY, ASSET_CLASS)
    df_4h_raw = fetch_ohlcv(TICKER, START, END, TF_SIGNAL, ASSET_CLASS)
    print(f"   ✓ Loaded {len(df_1h_raw)} 1h bars, {len(df_4h_raw)} 4h bars")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. COMPUTE HA + INDICATORS
    # ──────────────────────────────────────────────────────────────────────────
    print("📈 Computing Heikin Ashi + indicators...")
    df_4h = compute_ha_and_indicators(df_4h_raw.copy())
    df_4h, warmup_4h = trim_warmup_period(df_4h)
    print(f"   ✓ 4h: {len(df_4h)} bars (warmup: {warmup_4h})")

    df_1h = compute_ha_and_indicators(df_1h_raw.copy())
    df_1h, warmup_1h = trim_warmup_period(df_1h)
    print(f"   ✓ 1h: {len(df_1h)} bars (warmup: {warmup_1h})")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 3. EVALUATE CONDITIONS USING ENGINE
    # ──────────────────────────────────────────────────────────────────────────
    print("🎯 Evaluating conditions via engine...")

    # 4h ARM conditions
    cross_above_4h = evaluate_conditions(df_4h, ARM_LONG_CONDITION)
    cross_below_4h = evaluate_conditions(df_4h, ARM_SHORT_CONDITION)
    print(f"   ✓ 4h ARM LONG: {cross_above_4h.sum()}, ARM SHORT: {cross_below_4h.sum()}")

    # 1h CONFIRM/EXIT conditions
    cross_above_1h = evaluate_conditions(df_1h, CONFIRM_LONG_CONDITION)
    cross_below_1h = evaluate_conditions(df_1h, CONFIRM_SHORT_CONDITION)
    print(f"   ✓ 1h CONFIRM LONG: {cross_above_1h.sum()}, CONFIRM SHORT: {cross_below_1h.sum()}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. GENERATE MTF-CONFIRMED SIGNALS
    # ──────────────────────────────────────────────────────────────────────────
    print("🔗 Generating MTF-confirmed signals...")
    long_entry, long_exit, short_entry, short_exit = generate_mtf_signals(
        df_1h, df_4h,
        cross_above_1h, cross_below_1h,
        cross_above_4h, cross_below_4h,
    )
    print(f"   ✓ Long entries: {long_entry.sum()}, exits: {long_exit.sum()}")
    print(f"   ✓ Short entries: {short_entry.sum()}, exits: {short_exit.sum()}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. RESTORE REAL OHLC FOR EXECUTION
    # ──────────────────────────────────────────────────────────────────────────
    print("🔄 Restoring real OHLC for execution...")
    df_1h_real = df_1h_raw.loc[df_1h.index].copy()
    df_1h["open"] = df_1h_real["open"]
    df_1h["high"] = df_1h_real["high"]
    df_1h["low"] = df_1h_real["low"]
    df_1h["close"] = df_1h_real["close"]
    print(f"   ✓ Done")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 6. RUN BACKTEST USING ENGINE
    # ──────────────────────────────────────────────────────────────────────────
    print("🔄 Running backtest via engine...")

    trades, equity = run_backtest(
        df=df_1h,
        entry_signal=long_entry,
        exit_signal=long_exit,
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
        initial_capital=INITIAL_CAPITAL,
        asset_class=ASSET_CLASS,
        position_size_type=POSITION_SIZE_TYPE,
        position_size_value=POSITION_SIZE_VALUE,
        leverage=LEVERAGE,
        commission_pct=COMMISSION_PCT,
        slippage_pct=0.0,
        stop_loss_pct=None,
        take_profit_pct=None,
        enable_attribution=False,
    )

    print(f"   ✓ Backtest complete: {len(trades)} trades")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 7. GENERATE REPORT
    # ──────────────────────────────────────────────────────────────────────────
    print("📊 Performance Metrics")
    print("─" * 80)

    if not trades:
        print("   ⚠️  No trades executed")
        return

    report = generate_report(
        trade_log=trades,
        equity_curve=equity,
        initial_capital=INITIAL_CAPITAL,
    )

    print(f"Total Return:        {report['total_return_pct']:.2f}%")
    print(f"CAGR:                {report['cagr']:.2f}%")
    print(f"Sharpe Ratio:        {report['sharpe_ratio']:.2f}")
    print(f"Max Drawdown:        {report['max_drawdown_pct']:.2f}%")
    print(f"Win Rate:            {report['win_rate']:.2f}%")
    print(f"Profit Factor:       {report['profit_factor']:.2f}")
    print(f"Total Trades:        {report['total_trades']}")
    print(f"Avg Win:             ${report['avg_win']:,.2f}")
    print(f"Avg Loss:            ${report['avg_loss']:,.2f}")
    print(f"Largest Win:         ${report['largest_win']:,.2f}")
    print(f"Largest Loss:        ${report['largest_loss']:,.2f}")
    print(f"Avg Trade Duration:  {report['avg_trade_duration_days']:.1f} days")
    print(f"Final Capital:       ${report['final_capital']:,.2f}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 8. DIRECTION BREAKDOWN
    # ──────────────────────────────────────────────────────────────────────────
    print("📊 Direction Breakdown")
    print("─" * 80)

    long_trades = [t for t in trades if t["direction"] == "LONG"]
    short_trades = [t for t in trades if t["direction"] == "SHORT"]

    if long_trades:
        long_pnl = sum(t["pnl"] for t in long_trades)
        long_wins = sum(1 for t in long_trades if t["pnl"] > 0)
        long_wr = long_wins / len(long_trades) * 100
        print(f"LONG:   {len(long_trades):>3} trades | ${long_pnl:>+10,.2f} | WR: {long_wr:.1f}%")

    if short_trades:
        short_pnl = sum(t["pnl"] for t in short_trades)
        short_wins = sum(1 for t in short_trades if t["pnl"] > 0)
        short_wr = short_wins / len(short_trades) * 100
        print(f"SHORT:  {len(short_trades):>3} trades | ${short_pnl:>+10,.2f} | WR: {short_wr:.1f}%")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 9. EXIT REASON BREAKDOWN
    # ──────────────────────────────────────────────────────────────────────────
    print("📊 Exit Reason Breakdown")
    print("─" * 80)

    exit_reasons = {}
    for trade in trades:
        reason = trade.get("exit_reason", "unknown")
        if reason not in exit_reasons:
            exit_reasons[reason] = {"count": 0, "pnl": 0.0, "wins": 0}
        exit_reasons[reason]["count"] += 1
        exit_reasons[reason]["pnl"] += trade["pnl"]
        if trade["pnl"] > 0:
            exit_reasons[reason]["wins"] += 1

    for reason, stats in sorted(exit_reasons.items(), key=lambda x: x[1]["count"], reverse=True):
        count = stats["count"]
        pnl = stats["pnl"]
        wr = (stats["wins"] / count * 100) if count > 0 else 0.0
        print(f"{reason:<15} {count:>5} trades | ${pnl:>+10,.2f} | WR: {wr:.1f}%")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 10. TRADE LOG (Last 15)
    # ──────────────────────────────────────────────────────────────────────────
    print("📋 Recent Trades (last 15)")
    print("─" * 80)

    for i, trade in enumerate(trades[-15:], 1):
        direction = trade["direction"]
        entry_date = pd.to_datetime(trade["entry_date"]).strftime("%Y-%m-%d %H:%M")
        exit_date = pd.to_datetime(trade["exit_date"]).strftime("%Y-%m-%d %H:%M")
        pnl_pct = trade["pnl_pct"]
        exit_reason = trade["exit_reason"]

        pnl_symbol = "📈" if trade["pnl"] > 0 else "📉"

        print(f"{pnl_symbol} #{len(trades)-15+i:>3} {direction:<5} | "
              f"{entry_date} → {exit_date} | "
              f"${trade['entry_price']:>8,.2f} → ${trade['exit_price']:>8,.2f} | "
              f"{pnl_pct:>+6.2f}% | {exit_reason}")

    print()
    print("=" * 80)
    print("✅ MTF Confirmation backtest complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
