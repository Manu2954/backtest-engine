"""
Heikin Ashi + Donchian Channel + SMA50 Long/Short Strategy

Strategy Logic:
  LONG:
    - Entry: DC mid crosses ABOVE SMA50
    - Exit: DC mid crosses BELOW SMA50 (or TP if triggered by failed short)
    - If exit with loss → Enter SHORT with TP = abs(loss_pct) × 1.5

  SHORT:
    - Entry: DC mid crosses BELOW SMA50
    - Exit: DC mid crosses ABOVE SMA50 (or TP if triggered by failed long)
    - If exit with loss → Enter LONG with TP = abs(loss_pct) × 1.5

Indicators (all calculated on Heikin Ashi candles):
  - Heikin Ashi candles (smoothed price action)
  - Donchian Channel 20-period (calculated on HA)
  - SMA 50-period (calculated on HA close)

Note: Signals use HA-based indicators, but fills happen at real OHLC prices

Usage:
  python scripts/smoke_ha_donchian_sma.py
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
from app.engine.condition_engine import evaluate_conditions
from app.engine.state_machine import run_backtest
from app.engine.report_generator import generate_report


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TICKER = "BTCUSDT"
START = "2025-10-20"
END = "2026-06-01"
RESOLUTION = "4h"
ASSET_CLASS = "CRYPTO"
INITIAL_CAPITAL = 100.0

# Position sizing
POSITION_SIZE_TYPE = "percent_capital"
POSITION_SIZE_VALUE = 95.0  # 95% of capital per trade

# Risk management
STOP_LOSS_PCT = None  # No stop loss
TAKE_PROFIT_PCT = None  # No take profit
COMMISSION_PCT = 0.1  # 0.1% commission
SLIPPAGE_PCT = 0.0  # No slippage


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print(f"Heikin Ashi + Donchian + SMA50 Crossover Strategy")
    print("=" * 80)
    print(f"Ticker: {TICKER}")
    print(f"Period: {START} to {END}")
    print(f"Resolution: {RESOLUTION}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. FETCH DATA
    # ──────────────────────────────────────────────────────────────────────────
    print("📊 Fetching OHLCV data...")
    df = fetch_ohlcv(
        ticker=TICKER,
        start=START,
        end=END,
        resolution=RESOLUTION,
        asset_class=ASSET_CLASS,
    )
    print(f"   ✓ Loaded {len(df)} bars")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. COMPUTE HEIKIN ASHI CANDLES FIRST
    # ──────────────────────────────────────────────────────────────────────────
    print("📈 Computing Heikin Ashi candles...")
    ha_indicator = [{"indicator_type": "HEIKINASHI", "alias": "ha", "params": {}}]
    df = compute_indicators(df, ha_indicator)
    print(f"   ✓ Heikin Ashi computed")

    # Replace OHLC with Heikin Ashi for subsequent indicator calculations
    df["open"] = df["ha_open"]
    df["high"] = df["ha_high"]
    df["low"] = df["ha_low"]
    df["close"] = df["ha_close"]
    print(f"   ✓ Replaced OHLC with Heikin Ashi candles")

    # ──────────────────────────────────────────────────────────────────────────
    # 3. COMPUTE INDICATORS ON HEIKIN ASHI
    # ──────────────────────────────────────────────────────────────────────────
    print("📈 Computing indicators on Heikin Ashi (Donchian, SMA50)...")
    ha_based_indicators = [
        {"indicator_type": "DONCHIAN", "alias": "dc_20", "params": {"period": 20}},
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    ]
    df = compute_indicators(df, ha_based_indicators)
    print(f"   ✓ Indicators computed on Heikin Ashi")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. TRIM WARMUP PERIOD
    # ──────────────────────────────────────────────────────────────────────────
    original_len = len(df)
    df, warmup = trim_warmup_period(df)
    print(f"🔥 Warmup period: {warmup} bars trimmed")
    print(f"   ✓ Remaining bars: {len(df)}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. GENERATE SIGNALS
    # ──────────────────────────────────────────────────────────────────────────
    print("🎯 Generating entry/exit signals...")

    # Basic crossover signals
    dc_above_sma = df["dc_20_mid"] > df["sma_50"]
    dc_below_sma = df["dc_20_mid"] < df["sma_50"]

    # Crossover detection
    dc_cross_above = dc_above_sma & (~dc_above_sma.shift(1).fillna(False))
    dc_cross_below = dc_below_sma & (~dc_below_sma.shift(1).fillna(False))

    # LONG signals: DC crosses above SMA
    # long_entry_signal = dc_cross_above
    # long_exit_signal = dc_cross_below

    long_entry_signal = None
    long_exit_signal = None

    # SHORT signals: DC crosses below SMA
    short_entry_signal = dc_cross_below
    short_exit_signal = dc_cross_above

    # short_entry_signal = None
    # short_exit_signal = None

    # print(f"   ✓ Long entry signals: {long_entry_signal.sum()}")
    # print(f"   ✓ Long exit signals: {long_exit_signal.sum()}")
    print(f"   ✓ Short entry signals: {short_entry_signal.sum()}")
    print(f"   ✓ Short exit signals: {short_exit_signal.sum()}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 6. RUN BACKTEST WITH SHORTS
    # ──────────────────────────────────────────────────────────────────────────
    print("🔄 Running backtest with long/short capability...")
    print("   Note: Failed long → SHORT with TP = loss × 1.5")
    print("   Note: Failed short → LONG with TP = loss × 1.5")

    # Restore original OHLC for backtest execution (fills happen at real prices)
    df_original = fetch_ohlcv(TICKER, START, END, RESOLUTION, ASSET_CLASS)
    df["open"] = df_original.loc[df.index, "open"]
    df["high"] = df_original.loc[df.index, "high"]
    df["low"] = df_original.loc[df.index, "low"]
    df["close"] = df_original.loc[df.index, "close"]

    trades, equity = run_backtest(
        df=df,
        entry_signal=long_entry_signal,
        exit_signal=long_exit_signal,
        short_entry_signal=short_entry_signal,
        short_exit_signal=short_exit_signal,
        initial_capital=INITIAL_CAPITAL,
        asset_class=ASSET_CLASS,
        position_size_type=POSITION_SIZE_TYPE,
        position_size_value=POSITION_SIZE_VALUE,
        stop_loss_pct=STOP_LOSS_PCT,
        take_profit_pct=TAKE_PROFIT_PCT,
        commission_pct=COMMISSION_PCT,
        slippage_pct=SLIPPAGE_PCT,
    )
    print(f"   ✓ Backtest complete")
    print(f"   ✓ Total trades: {len(trades)}")
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

    # Display key metrics
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
    # 8. TRADE LOG
    # ──────────────────────────────────────────────────────────────────────────
    print("📋 Recent Trades (last 10)")
    print("─" * 80)

    for i, trade in enumerate(trades[-10:], 1):
        direction = trade.get("direction", "LONG")
        entry_date = pd.to_datetime(trade["entry_date"]).strftime("%Y-%m-%d")
        exit_date = pd.to_datetime(trade["exit_date"]).strftime("%Y-%m-%d")
        pnl_pct = trade["pnl_pct"]
        exit_reason = trade["exit_reason"]

        pnl_symbol = "📈" if pnl_pct > 0 else "📉"

        print(f"{pnl_symbol} Trade #{len(trades)-10+i} ({direction})")
        print(f"   Entry:  {entry_date} @ ${trade['entry_price']:.2f}")
        print(f"   Exit:   {exit_date} @ ${trade['exit_price']:.2f}")
        print(f"   P&L:    {pnl_pct:+.2f}% (${trade['pnl']:+,.2f})")
        print(f"   Reason: {exit_reason}")
        print()

    print("=" * 80)
    print("✅ Smoke test complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
