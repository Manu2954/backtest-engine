"""
Copper Futures (HG=F) - Supertrend Strategy

Indicator: Supertrend(7, 3) on 2h timeframe
Entry: Buy when price crosses above Supertrend line (trend turns bullish)
Exit: Sell when price crosses below Supertrend line (trend turns bearish)

Supertrend Parameters:
- ATR Period: 7
- Multiplier: 3

Note: Fetches 1h data and resamples to 2h (Yahoo Finance doesn't support 2h natively)

Usage:
  python backend/scripts/smoke_copper_supertrend.py
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

TICKER = "HG=F"
START = "2026-04-18"
END = "2026-06-17"
RESOLUTION = "1h"  # Closest to 2h (Yahoo Finance limitation: 2h not supported, 60-day max for intraday)
ASSET_CLASS = "STOCK"

INITIAL_CAPITAL = 10000.0
POSITION_SIZE_TYPE = "full_capital"
POSITION_SIZE_VALUE = 100.0

# Supertrend parameters
ATR_PERIOD = 7
MULTIPLIER = 3

# Risk management
STOP_LOSS_PCT = None  # Supertrend acts as dynamic stop
TAKE_PROFIT_PCT = None


def main():
    print("="*80)
    print("COPPER FUTURES (HG=F) - SUPERTREND STRATEGY")
    print("="*80)
    print(f"Ticker: {TICKER}")
    print(f"Period: {START} to {END}")
    print(f"Resolution: {RESOLUTION}")
    print(f"Supertrend: ATR({ATR_PERIOD}), Multiplier={MULTIPLIER}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print("="*80)

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. FETCH DATA
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n[1/5] Fetching OHLCV data...")
    df = fetch_ohlcv(TICKER, START, END, RESOLUTION, ASSET_CLASS)

    if df.empty:
        print("❌ No data returned")
        return

    print(f"✅ Fetched {len(df)} 1h candles")

    # Resample 1h to 2h
    print("    Resampling 1h → 2h...")
    df = df.resample('2h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    print(f"✅ Resampled to {len(df)} 2h candles")
    print(f"    Date range: {df.index[0]} to {df.index[-1]}")

    # Debug: check for NaNs before indicator computation
    print(f"    NaN check - Open: {df['open'].isna().sum()}, Close: {df['close'].isna().sum()}")

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. COMPUTE INDICATORS
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n[2/5] Computing indicators...")

    indicators = [
        {"indicator_type": "SUPERTREND", "alias": "supertrend", "params": {"period": ATR_PERIOD, "multiplier": MULTIPLIER}}
    ]

    df = compute_indicators(df, indicators)

    print(f"✅ Computed indicators: {[i['alias'] for i in indicators]}")
    print(f"    Supertrend NaN count: {df['supertrend'].isna().sum()} / {len(df)}")

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. TRIM WARMUP
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n[3/5] Trimming warmup period...")
    original_len = len(df)
    df, trimmed = trim_warmup_period(df)
    print(f"✅ Trimmed {trimmed} warmup bars, {len(df)} bars remain")

    if df.empty:
        print("❌ No data after warmup trim")
        return

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. GENERATE SIGNALS
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n[4/5] Generating trading signals...")

    # Supertrend direction column (aliased as 'supertrend')
    # supertrend = direction (1 = uptrend, -1 = downtrend)
    # supertrend_trend = supertrend line value

    supertrend_direction_col = "supertrend"

    if supertrend_direction_col not in df.columns:
        print(f"❌ Supertrend direction column not found: {supertrend_direction_col}")
        print(f"Available columns: {df.columns.tolist()}")
        return

    # Entry: Direction changes from -1 to 1 (bearish to bullish)
    # Exit: Direction changes from 1 to -1 (bullish to bearish)

    df["prev_direction"] = df[supertrend_direction_col].shift(1)

    entry_signal = (df[supertrend_direction_col] == 1) & (df["prev_direction"] == -1)
    exit_signal = (df[supertrend_direction_col] == -1) & (df["prev_direction"] == 1)

    print(f"✅ Entry signals: {entry_signal.sum()}")
    print(f"✅ Exit signals: {exit_signal.sum()}")

    if entry_signal.sum() == 0:
        print("❌ No entry signals generated")
        return

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. RUN BACKTEST
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n[5/5] Running backtest...")

    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=INITIAL_CAPITAL,
        asset_class=ASSET_CLASS,
        position_size_type=POSITION_SIZE_TYPE,
        position_size_value=POSITION_SIZE_VALUE,
        stop_loss_pct=STOP_LOSS_PCT,
        take_profit_pct=TAKE_PROFIT_PCT,
    )

    if not trades:
        print("❌ No trades executed")
        return

    print(f"✅ Executed {len(trades)} trades")

    # ═══════════════════════════════════════════════════════════════════════════
    # GENERATE REPORT
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n" + "="*80)
    print("BACKTEST RESULTS")
    print("="*80)

    report = generate_report(
        trade_log=trades,
        equity_curve=equity_curve,
        initial_capital=INITIAL_CAPITAL,
        benchmark_equity=None,
    )

    print(f"\n📊 Performance Metrics:")
    print(f"   Total Return: {report['total_return_pct']:.2f}%")
    print(f"   CAGR: {report['cagr']:.2f}%")
    print(f"   Sharpe Ratio: {report['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown: {report['max_drawdown_pct']:.2f}%")
    print(f"   Win Rate: {report['win_rate']:.2f}%")
    print(f"   Profit Factor: {report['profit_factor']:.2f}")
    print(f"   Total Trades: {report['total_trades']}")

    # Calculate winning/losing trades from trade log
    winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
    losing_trades = sum(1 for t in trades if t.get('pnl', 0) < 0)

    print(f"   Winning Trades: {winning_trades}")
    print(f"   Losing Trades: {losing_trades}")
    print(f"   Avg Win: ${report['avg_win']:.2f}")
    print(f"   Avg Loss: ${report['avg_loss']:.2f}")
    print(f"   Largest Win: ${report['largest_win']:.2f}")
    print(f"   Largest Loss: ${report['largest_loss']:.2f}")
    print(f"   Final Capital: ${report['final_capital']:.2f}")

    # ═══════════════════════════════════════════════════════════════════════════
    # TRADE LOG
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n" + "="*80)
    print("TRADE LOG (Last 10 trades)")
    print("="*80)

    trades_df = pd.DataFrame(trades)
    display_cols = ["entry_date", "exit_date", "entry_price", "exit_price", "pnl", "pnl_pct", "exit_reason"]

    if len(trades_df) > 0:
        print(trades_df[display_cols].tail(10).to_string(index=False))

    print("\n✅ Backtest complete")


if __name__ == "__main__":
    main()
