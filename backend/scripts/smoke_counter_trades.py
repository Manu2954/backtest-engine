"""
Counter-Trade Feature Smoke Test

Demonstrates both approaches for counter-trade implementation:
1. Native engine: enable_counter_trades=True (recommended)
2. Pre-processor: apply_counter_trade_signals() (advanced)

Strategy: Simple SMA crossover with counter-trades
- LONG: SMA10 crosses above SMA50
- SHORT: SMA10 crosses below SMA50
- Counter-trade: Failed trades trigger opposite direction with TP = loss% × 1.5

Usage:
  python scripts/smoke_counter_trades.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv
from app.engine.indicator_layer import compute_indicators, trim_warmup_period
from app.engine.state_machine import run_backtest
from app.engine.report_generator import generate_report
from app.engine.signal_transformers import apply_counter_trade_signals


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TICKER = "BTCUSDT"
START = "2023-01-01"
END = "2024-01-01"
RESOLUTION = "1d"
ASSET_CLASS = "CRYPTO"
INITIAL_CAPITAL = 10000.0
COUNTER_TP_MULTIPLIER = 1.5


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("COUNTER-TRADE FEATURE SMOKE TEST")
    print("=" * 80)
    print(f"Ticker: {TICKER}")
    print(f"Period: {START} to {END}")
    print(f"Resolution: {RESOLUTION}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print(f"Counter TP Multiplier: {COUNTER_TP_MULTIPLIER}x")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. FETCH DATA & COMPUTE INDICATORS
    # ──────────────────────────────────────────────────────────────────────────
    print("📊 Fetching OHLCV data...")
    df = fetch_ohlcv(TICKER, START, END, RESOLUTION, ASSET_CLASS)
    print(f"   ✓ Loaded {len(df)} bars")

    print("📈 Computing indicators (SMA10, SMA50)...")
    indicators = [
        {"indicator_type": "SMA", "alias": "sma_10", "params": {"period": 10, "source": "close"}},
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)

    original_len = len(df)
    df, warmup = trim_warmup_period(df)
    print(f"   ✓ Warmup: {warmup} bars trimmed, {len(df)} bars remaining")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. GENERATE SIGNALS
    # ──────────────────────────────────────────────────────────────────────────
    print("🎯 Generating entry/exit signals...")

    # SMA crossover signals
    sma10_above_sma50 = df["sma_10"] > df["sma_50"]
    sma10_below_sma50 = df["sma_10"] < df["sma_50"]

    # Crossover detection
    sma10_cross_above = sma10_above_sma50 & (~sma10_above_sma50.shift(1).fillna(False))
    sma10_cross_below = sma10_below_sma50 & (~sma10_below_sma50.shift(1).fillna(False))

    # LONG signals
    long_entry = sma10_cross_above
    long_exit = sma10_cross_below

    # SHORT signals
    short_entry = sma10_cross_below
    short_exit = sma10_cross_above

    print(f"   ✓ Long entry signals: {long_entry.sum()}")
    print(f"   ✓ Long exit signals: {long_exit.sum()}")
    print(f"   ✓ Short entry signals: {short_entry.sum()}")
    print(f"   ✓ Short exit signals: {short_exit.sum()}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 3. APPROACH 1: NATIVE ENGINE (RECOMMENDED)
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("APPROACH 1: NATIVE ENGINE (enable_counter_trades=True)")
    print("=" * 80)

    trades_native, equity_native = run_backtest(
        df=df,
        entry_signal=long_entry,
        exit_signal=long_exit,
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
        initial_capital=INITIAL_CAPITAL,
        asset_class=ASSET_CLASS,
        enable_counter_trades=True,
        counter_tp_multiplier=COUNTER_TP_MULTIPLIER,
    )

    print(f"✅ Total Trades: {len(trades_native)}")
    print()

    # Count counter-trades (those with dynamic TP from counter-trade logic)
    # Note: We can't directly distinguish counter-trades in the native approach
    # They're seamlessly integrated into the trade log

    report_native = generate_report(
        trade_log=trades_native,
        equity_curve=equity_native,
        initial_capital=INITIAL_CAPITAL,
    )

    print("📊 Performance Metrics")
    print("─" * 80)
    print(f"Total Return:        {report_native['total_return_pct']:.2f}%")
    print(f"CAGR:                {report_native['cagr']:.2f}%")
    print(f"Sharpe Ratio:        {report_native['sharpe_ratio']:.2f}")
    print(f"Max Drawdown:        {report_native['max_drawdown_pct']:.2f}%")
    print(f"Win Rate:            {report_native['win_rate']:.2f}%")
    print(f"Profit Factor:       {report_native['profit_factor']:.2f}")
    print(f"Avg Win:             ${report_native['avg_win']:,.2f}")
    print(f"Avg Loss:            ${report_native['avg_loss']:,.2f}")
    print(f"Final Capital:       ${report_native['final_capital']:,.2f}")
    print()

    # Show recent trades
    print("📋 Recent Trades (last 5)")
    print("─" * 80)
    for trade in trades_native[-5:]:
        direction = trade["direction"]
        entry_date = pd.to_datetime(trade["entry_date"]).strftime("%Y-%m-%d")
        exit_date = pd.to_datetime(trade["exit_date"]).strftime("%Y-%m-%d")
        pnl_pct = trade["pnl_pct"] * 100  # Convert to percentage
        exit_reason = trade["exit_reason"]
        symbol = "📈" if pnl_pct > 0 else "📉"

        print(f"{symbol} {direction:5} {entry_date} → {exit_date} | {pnl_pct:+6.2f}% | {exit_reason}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. APPROACH 2: PRE-PROCESSOR (ADVANCED)
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("APPROACH 2: PRE-PROCESSOR (apply_counter_trade_signals)")
    print("=" * 80)

    # Apply signal transformer
    long_e_pre, long_x_pre, short_e_pre, short_x_pre = apply_counter_trade_signals(
        df=df,
        long_entry=long_entry,
        long_exit=long_exit,
        short_entry=short_entry,
        short_exit=short_exit,
        tp_multiplier=COUNTER_TP_MULTIPLIER,
    )

    print(f"   ✓ Original long entries: {long_entry.sum()}")
    print(f"   ✓ Modified long entries: {long_e_pre.sum()} (+{long_e_pre.sum() - long_entry.sum()} counter-trades)")
    print(f"   ✓ Original short entries: {short_entry.sum()}")
    print(f"   ✓ Modified short entries: {short_e_pre.sum()} (+{short_e_pre.sum() - short_entry.sum()} counter-trades)")
    print()

    # Run backtest with modified signals (without native counter-trades)
    trades_pre, equity_pre = run_backtest(
        df=df,
        entry_signal=long_e_pre,
        exit_signal=long_x_pre,
        short_entry_signal=short_e_pre,
        short_exit_signal=short_x_pre,
        initial_capital=INITIAL_CAPITAL,
        asset_class=ASSET_CLASS,
        enable_counter_trades=False,  # Already applied via pre-processor
    )

    print(f"✅ Total Trades: {len(trades_pre)}")
    print()

    report_pre = generate_report(
        trade_log=trades_pre,
        equity_curve=equity_pre,
        initial_capital=INITIAL_CAPITAL,
    )

    print("📊 Performance Metrics")
    print("─" * 80)
    print(f"Total Return:        {report_pre['total_return_pct']:.2f}%")
    print(f"CAGR:                {report_pre['cagr']:.2f}%")
    print(f"Sharpe Ratio:        {report_pre['sharpe_ratio']:.2f}")
    print(f"Max Drawdown:        {report_pre['max_drawdown_pct']:.2f}%")
    print(f"Win Rate:            {report_pre['win_rate']:.2f}%")
    print(f"Profit Factor:       {report_pre['profit_factor']:.2f}")
    print(f"Avg Win:             ${report_pre['avg_win']:,.2f}")
    print(f"Avg Loss:            ${report_pre['avg_loss']:,.2f}")
    print(f"Final Capital:       ${report_pre['final_capital']:,.2f}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. COMPARISON
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("COMPARISON: Native vs Pre-processor")
    print("=" * 80)
    print(f"{'Metric':<25} {'Native':>15} {'Pre-processor':>15} {'Diff':>10}")
    print("─" * 80)
    print(f"{'Total Trades':<25} {len(trades_native):>15} {len(trades_pre):>15} {len(trades_pre) - len(trades_native):>10}")
    print(f"{'Total Return %':<25} {report_native['total_return_pct']:>15.2f} {report_pre['total_return_pct']:>15.2f} {report_pre['total_return_pct'] - report_native['total_return_pct']:>10.2f}")
    print(f"{'CAGR %':<25} {report_native['cagr']:>15.2f} {report_pre['cagr']:>15.2f} {report_pre['cagr'] - report_native['cagr']:>10.2f}")
    print(f"{'Win Rate %':<25} {report_native['win_rate']:>15.2f} {report_pre['win_rate']:>15.2f} {report_pre['win_rate'] - report_native['win_rate']:>10.2f}")
    print(f"{'Final Capital $':<25} {report_native['final_capital']:>15,.2f} {report_pre['final_capital']:>15,.2f} {report_pre['final_capital'] - report_native['final_capital']:>10,.2f}")
    print()

    print("=" * 80)
    print("✅ Smoke test complete!")
    print("=" * 80)
    print()
    print("NOTES:")
    print("  • Both approaches should produce similar results")
    print("  • Native approach is simpler and recommended for most use cases")
    print("  • Pre-processor approach allows signal inspection and custom logic")
    print("  • Small differences may occur due to simulation assumptions")
    print()


if __name__ == "__main__":
    main()
