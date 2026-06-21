"""
Silver Supertrend Strategy Backtest

Strategy: Supertrend(7, 3) on Heikin Ashi candles, 1d timeframe
- Indicators computed on Heikin Ashi smoothed candles
- Entry/exit fills use real OHLC prices
- LONG: HA Supertrend crosses from bearish to bullish
- SHORT: HA Supertrend crosses from bullish to bearish
- Exit: Opposite signal

Ticker: SI=F (Silver Futures)
Timeframe: 1d
Period: 2016-2026
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


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TICKER = "SI=F"
START = "2016-01-01"
END = "2026-01-01"
RESOLUTION = "1d"
ASSET_CLASS = "STOCK"
INITIAL_CAPITAL = 1000000.0

# Strategy parameters
SUPERTREND_PERIOD = 7
SUPERTREND_MULTIPLIER = 3.0


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("SILVER SUPERTREND STRATEGY BACKTEST")
    print("=" * 80)
    print(f"Ticker: {TICKER}")
    print(f"Period: {START} to {END}")
    print(f"Resolution: {RESOLUTION}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print(f"Supertrend: ({SUPERTREND_PERIOD}, {SUPERTREND_MULTIPLIER})")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. FETCH DATA
    # ──────────────────────────────────────────────────────────────────────────
    print("📊 Fetching OHLCV data...")
    df = fetch_ohlcv(TICKER, START, END, RESOLUTION, ASSET_CLASS)
    print(f"   ✓ Loaded {len(df)} bars")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. COMPUTE HEIKIN ASHI CANDLES
    # ──────────────────────────────────────────────────────────────────────────
    print("📈 Computing Heikin Ashi candles...")
    ha_indicators = [
        {
            "indicator_type": "HEIKINASHI",
            "alias": "ha",
            "params": {},
        },
    ]
    df = compute_indicators(df, ha_indicators)

    # Store real OHLC for fills
    df["real_open"] = df["open"]
    df["real_high"] = df["high"]
    df["real_low"] = df["low"]
    df["real_close"] = df["close"]

    # Replace OHLC with HA for indicator computation
    df["open"] = df["ha_open"]
    df["high"] = df["ha_high"]
    df["low"] = df["ha_low"]
    df["close"] = df["ha_close"]

    print("   ✓ Heikin Ashi candles computed")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 3. COMPUTE INDICATORS (on HA data)
    # ──────────────────────────────────────────────────────────────────────────
    print("📈 Computing Supertrend indicator on HA data...")
    indicators = [
        {
            "indicator_type": "SUPERTREND",
            "alias": "supertrend",
            "params": {
                "period": SUPERTREND_PERIOD,
                "multiplier": SUPERTREND_MULTIPLIER,
            },
        },
    ]
    df = compute_indicators(df, indicators)

    # Restore real OHLC for backtest fills
    df["open"] = df["real_open"]
    df["high"] = df["real_high"]
    df["low"] = df["real_low"]
    df["close"] = df["real_close"]

    original_len = len(df)
    df, warmup = trim_warmup_period(df)
    print(f"   ✓ Warmup: {warmup} bars trimmed, {len(df)} bars remaining")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. GENERATE SIGNALS (on HA-based indicators)
    # ──────────────────────────────────────────────────────────────────────────
    print("🎯 Generating entry/exit signals...")

    # Supertrend indicator returns 1 (bullish) or -1 (bearish)
    # LONG: Supertrend crosses from -1 to 1
    # SHORT: Supertrend crosses from 1 to -1
    supertrend_bullish = df["supertrend"] == 1
    supertrend_bearish = df["supertrend"] == -1

    # Detect crossovers
    bullish_cross = supertrend_bullish & (~supertrend_bullish.shift(1).fillna(False))
    bearish_cross = supertrend_bearish & (~supertrend_bearish.shift(1).fillna(False))

    # LONG signals
    long_entry = bullish_cross
    long_exit = bearish_cross

    # SHORT signals
    short_entry = bearish_cross
    short_exit = bullish_cross

    print(f"   ✓ Long entry signals: {long_entry.sum()}")
    print(f"   ✓ Long exit signals: {long_exit.sum()}")
    print(f"   ✓ Short entry signals: {short_entry.sum()}")
    print(f"   ✓ Short exit signals: {short_exit.sum()}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. RUN BACKTEST (using real OHLC for fills)
    # ──────────────────────────────────────────────────────────────────────────
    print("⚙️  Running backtest...")
    trades, equity = run_backtest(
        df=df,
        entry_signal=long_entry,
        exit_signal=long_exit,
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
        initial_capital=INITIAL_CAPITAL,
        asset_class=ASSET_CLASS,
    )

    print(f"   ✓ Backtest complete: {len(trades)} trades")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 6. GENERATE REPORT
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("PERFORMANCE REPORT")
    print("=" * 80)

    report = generate_report(
        trade_log=trades,
        equity_curve=equity,
        initial_capital=INITIAL_CAPITAL,
    )

    winning_trades = int(report['total_trades'] * report['win_rate'] / 100)
    losing_trades = report['total_trades'] - winning_trades

    print(f"Total Return:        {report['total_return_pct']:>8.2f}%")
    print(f"CAGR:                {report['cagr']:>8.2f}%")
    print(f"Sharpe Ratio:        {report['sharpe_ratio']:>8.2f}")
    print(f"Max Drawdown:        {report['max_drawdown_pct']:>8.2f}%")
    print(f"Win Rate:            {report['win_rate']:>8.2f}%")
    print(f"Profit Factor:       {report['profit_factor']:>8.2f}")
    print(f"Total Trades:        {report['total_trades']:>8}")
    print(f"Winning Trades:      {winning_trades:>8}")
    print(f"Losing Trades:       {losing_trades:>8}")
    print(f"Avg Win:             ${report['avg_win']:>8,.2f}")
    print(f"Avg Loss:            ${report['avg_loss']:>8,.2f}")
    print(f"Largest Win:         ${report['largest_win']:>8,.2f}")
    print(f"Largest Loss:        ${report['largest_loss']:>8,.2f}")
    print(f"Avg Trade Duration:  {report['avg_trade_duration_days']:>8.1f} days")
    print(f"Final Capital:       ${report['final_capital']:>8,.2f}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 7. TRADE BREAKDOWN
    # ──────────────────────────────────────────────────────────────────────────
    if trades:
        print("=" * 80)
        print("TRADE BREAKDOWN")
        print("=" * 80)

        long_trades = [t for t in trades if t["direction"] == "LONG"]
        short_trades = [t for t in trades if t["direction"] == "SHORT"]

        if long_trades:
            long_wins = [t for t in long_trades if t["pnl"] > 0]
            long_losses = [t for t in long_trades if t["pnl"] <= 0]
            print(f"LONG Trades:         {len(long_trades):>8}")
            print(f"  Wins:              {len(long_wins):>8} ({len(long_wins)/len(long_trades)*100:.1f}%)")
            print(f"  Losses:            {len(long_losses):>8} ({len(long_losses)/len(long_trades)*100:.1f}%)")
            print(f"  Total P&L:         ${sum(t['pnl'] for t in long_trades):>8,.2f}")
            print()

        if short_trades:
            short_wins = [t for t in short_trades if t["pnl"] > 0]
            short_losses = [t for t in short_trades if t["pnl"] <= 0]
            print(f"SHORT Trades:        {len(short_trades):>8}")
            print(f"  Wins:              {len(short_wins):>8} ({len(short_wins)/len(short_trades)*100:.1f}%)")
            print(f"  Losses:            {len(short_losses):>8} ({len(short_losses)/len(short_trades)*100:.1f}%)")
            print(f"  Total P&L:         ${sum(t['pnl'] for t in short_trades):>8,.2f}")
            print()

    # ──────────────────────────────────────────────────────────────────────────
    # 8. RECENT TRADES
    # ──────────────────────────────────────────────────────────────────────────
    if trades:
        print("=" * 80)
        print("RECENT TRADES (Last 15)")
        print("=" * 80)
        print(f"{'Dir':<6} {'Entry Date':<12} {'Exit Date':<12} {'Entry $':<10} {'Exit $':<10} {'P&L %':<10} {'P&L $':<12} {'Exit':<20}")
        print("-" * 80)

        for trade in trades[-15:]:
            direction = trade["direction"]
            entry_date = pd.to_datetime(trade["entry_date"]).strftime("%Y-%m-%d")
            exit_date = pd.to_datetime(trade["exit_date"]).strftime("%Y-%m-%d")
            entry_price = trade["entry_price"]
            exit_price = trade["exit_price"]
            pnl_pct = trade["pnl_pct"] * 100
            pnl = trade["pnl"]
            exit_reason = trade["exit_reason"]

            symbol = "📈" if pnl > 0 else "📉"
            print(f"{direction:<6} {entry_date:<12} {exit_date:<12} ${entry_price:<9.2f} ${exit_price:<9.2f} {pnl_pct:>+7.2f}% {symbol}${pnl:>9.2f} {exit_reason:<20}")

        print()

    print("=" * 80)
    print("✅ Analysis complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
