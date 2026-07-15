"""
Heikin Ashi + Donchian Channel + SMA50 Long/Short Strategy with Dynamic TP (FIXED)

FIXED: Proper boolean handling in crossover detection.
The original script had a bug where ~series.shift(1).fillna(False) returned
-1/-2 instead of True/False due to object dtype from fillna().

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
  python scripts/smoke_ha_donchian_sma_fixed.py
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
from app.engine.report_generator import generate_report
from app.engine.robustness.regime_detection import (
    detect_regimes,
    analyze_trades_by_regime,
    calculate_regime_distribution,
    assess_regime_dependency,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TICKER = "BTCUSDT"
START = "2026-01-01"
END = "2026-12-31"
RESOLUTION = "1h"
ASSET_CLASS = "CRYPTO"
INITIAL_CAPITAL = 100.0
LEVERAGE = 5.0  # 5x leverage (set to 1.0 for no leverage)

# Position sizing
POSITION_SIZE_TYPE = "percent_capital"
POSITION_SIZE_VALUE = 95.0  # 95% of capital per trade

# Risk management
COMMISSION_PCT = 0.1  # 0.1% commission

# Periodic contribution
PERIODIC_CONTRIBUTION = {
    "amount": 0.0,          # Add $100 per contribution
    "frequency": "monthly",   # Options: "daily", "weekly", "monthly"
}
# Set to None to disable: PERIODIC_CONTRIBUTION = None


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print(f"Heikin Ashi + Donchian + SMA50 (Custom Backtest with Dynamic TP)")
    print("=" * 80)
    print(f"Ticker: {TICKER}")
    print(f"Period: {START} to {END}")
    print(f"Resolution: {RESOLUTION}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    if PERIODIC_CONTRIBUTION:
        print(f"Periodic Contrib: ${PERIODIC_CONTRIBUTION['amount']:,.2f} {PERIODIC_CONTRIBUTION['frequency']}")
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

    # Crossover detection (FIXED: proper boolean handling)
    # Cross above: was not above (<=), now is above (>)
    prev_not_above = ~dc_above_sma.shift(1).fillna(False).astype(bool)
    dc_cross_above = dc_above_sma & prev_not_above

    # Cross below: was not below (>=), now is below (<)
    prev_not_below = ~dc_below_sma.shift(1).fillna(False).astype(bool)
    dc_cross_below = dc_below_sma & prev_not_below

    # LONG signals: DC crosses above SMA
    long_entry_signal = dc_cross_above
    long_exit_signal = dc_cross_below

    # SHORT signals: DC crosses below SMA
    short_entry_signal = dc_cross_below
    short_exit_signal = dc_cross_above

    print(f"   ✓ Long entry signals: {long_entry_signal.sum()}")
    print(f"   ✓ Long exit signals: {long_exit_signal.sum()}")
    print(f"   ✓ Short entry signals: {short_entry_signal.sum()}")
    print(f"   ✓ Short exit signals: {short_exit_signal.sum()}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 6. CUSTOM BACKTEST WITH DYNAMIC TP LOGIC
    # ──────────────────────────────────────────────────────────────────────────
    print("🔄 Running custom backtest with failed-trade counter logic...")
    print("   Note: Failed long → SHORT at next bar with TP = abs(loss%) × 1.5")
    print("   Note: Failed short → LONG at next bar with TP = abs(loss%) × 1.5")
    print()

    # Restore original OHLC for backtest execution
    df_original = fetch_ohlcv(TICKER, START, END, RESOLUTION, ASSET_CLASS)
    df_original = df_original.loc[df.index]  # Match indices after warmup trim
    df["open"] = df_original["open"]
    df["high"] = df_original["high"]
    df["low"] = df_original["low"]
    df["close"] = df_original["close"]

    # Custom backtest state
    capital = INITIAL_CAPITAL
    position = None  # {"direction": str, "entry_price": float, "entry_idx": int, "shares": float, "dynamic_tp_pct": float|None}
    trades = []
    equity_series = []
    counter_trade_pending = None  # {"direction": str, "tp_pct": float}

    # Periodic contribution tracking
    last_contribution_date = None
    total_contributions = 0.0

    if PERIODIC_CONTRIBUTION:
        contrib_amount = PERIODIC_CONTRIBUTION["amount"]
        contrib_freq = PERIODIC_CONTRIBUTION["frequency"]
        print(f"   💰 Periodic contribution enabled: ${contrib_amount:,.2f} {contrib_freq}")

        # Calculate contribution interval
        if contrib_freq == "daily":
            contrib_interval_days = 1
        elif contrib_freq == "weekly":
            contrib_interval_days = 7
        elif contrib_freq == "monthly":
            contrib_interval_days = 30
        else:
            contrib_interval_days = 30  # Default to monthly
    else:
        print(f"   💰 Periodic contribution disabled")

    for i in range(len(df)):
        bar = df.iloc[i]
        date = df.index[i]

        # ──────────────────────────────────────────────────────────────────
        # PERIODIC CONTRIBUTION
        # ──────────────────────────────────────────────────────────────────
        if PERIODIC_CONTRIBUTION:
            if last_contribution_date is None:
                # First contribution at start
                last_contribution_date = date
            else:
                days_since_last = (date - last_contribution_date).days
                if days_since_last >= contrib_interval_days:
                    capital += contrib_amount
                    total_contributions += contrib_amount
                    last_contribution_date = date

        # Track equity (mark to market)
        if position is None:
            current_equity = capital
        else:
            # Calculate unrealized P&L
            if position["direction"] == "LONG":
                unrealized_pnl = (bar["close"] - position["entry_price"]) * position["shares"]
            else:  # SHORT
                unrealized_pnl = (position["entry_price"] - bar["close"]) * position["shares"]

            # Equity = available capital + margin tied up in position + unrealized P&L
            margin = position.get("margin", position["entry_price"] * position["shares"])
            current_equity = capital + margin + unrealized_pnl

        equity_series.append(current_equity)

        # ──────────────────────────────────────────────────────────────────
        # EXIT LOGIC
        # ──────────────────────────────────────────────────────────────────
        if position is not None:
            exit_triggered = False
            exit_reason = None
            exit_price = None

            # Check liquidation (if leveraged)
            if position.get("liquidation_price") is not None:
                if position["direction"] == "LONG":
                    if bar["low"] <= position["liquidation_price"]:
                        exit_triggered = True
                        exit_price = position["liquidation_price"]
                        exit_reason = "liquidation"
                else:  # SHORT
                    if bar["high"] >= position["liquidation_price"]:
                        exit_triggered = True
                        exit_price = position["liquidation_price"]
                        exit_reason = "liquidation"

            # Check dynamic TP (if set and not liquidated)
            if not exit_triggered and position.get("dynamic_tp_pct") is not None:
                tp_pct = position["dynamic_tp_pct"]
                if position["direction"] == "LONG":
                    tp_price = position["entry_price"] * (1 + tp_pct / 100)
                    if bar["high"] >= tp_price:
                        exit_triggered = True
                        exit_price = tp_price
                        exit_reason = "take_profit_dynamic"
                else:  # SHORT
                    tp_price = position["entry_price"] * (1 - tp_pct / 100)
                    if bar["low"] <= tp_price:
                        exit_triggered = True
                        exit_price = tp_price
                        exit_reason = "take_profit_dynamic"

            # Check signal exit (only if TP/liquidation hasn't triggered)
            if not exit_triggered:
                if position["direction"] == "LONG" and long_exit_signal.iloc[i]:
                    exit_triggered = True
                    exit_price = bar["open"]
                    exit_reason = "signal"
                elif position["direction"] == "SHORT" and short_exit_signal.iloc[i]:
                    exit_triggered = True
                    exit_price = bar["open"]
                    exit_reason = "signal"

            # Force close on last bar
            if not exit_triggered and i == len(df) - 1:
                exit_triggered = True
                exit_price = bar["close"]
                exit_reason = "force_close"

            # Execute exit
            if exit_triggered:
                # Calculate P&L
                if position["direction"] == "LONG":
                    gross_pnl = (exit_price - position["entry_price"]) * position["shares"]
                    pnl_pct = ((exit_price - position["entry_price"]) / position["entry_price"]) * 100
                else:  # SHORT
                    gross_pnl = (position["entry_price"] - exit_price) * position["shares"]
                    pnl_pct = ((position["entry_price"] - exit_price) / position["entry_price"]) * 100

                # Apply commission (entry + exit)
                notional = position["entry_price"] * position["shares"]
                exit_notional = exit_price * position["shares"]
                commission = (COMMISSION_PCT / 100) * (notional + exit_notional)
                net_pnl = gross_pnl - commission

                # Return margin + P&L to capital
                margin = position.get("margin", notional)
                capital += margin + net_pnl

                # Record trade
                entry_date = df.index[position["entry_idx"]]
                trade_duration = (date - entry_date).total_seconds() / 86400

                trades.append({
                    "direction": position["direction"],
                    "entry_date": entry_date,
                    "entry_price": position["entry_price"],
                    "exit_date": date,
                    "exit_price": exit_price,
                    "shares": position["shares"],
                    "pnl": net_pnl,
                    "pnl_pct": pnl_pct,
                    "exit_reason": exit_reason,
                    "trade_duration_days": trade_duration,
                })

                # Check if we should trigger counter-trade
                counter_trade_pending = None
                if net_pnl < 0 and exit_reason == "signal":  # Failed on signal exit
                    counter_direction = "SHORT" if position["direction"] == "LONG" else "LONG"
                    counter_tp_pct = abs(pnl_pct) * 1.5
                    counter_trade_pending = {
                        "direction": counter_direction,
                        "tp_pct": counter_tp_pct,
                    }
                    # print(f"   ⚡ Counter-trade triggered: {counter_direction} with TP={counter_tp_pct:.2f}% (loss was {pnl_pct:.2f}%)")

                position = None

        # ──────────────────────────────────────────────────────────────────
        # ENTRY LOGIC
        # ──────────────────────────────────────────────────────────────────
        if position is None and i < len(df) - 1:  # Don't enter on last bar
            # Priority 1: Counter-trade (if pending)
            if counter_trade_pending is not None:
                next_bar = df.iloc[i + 1]
                entry_price = next_bar["open"]
                position_value = capital * (POSITION_SIZE_VALUE / 100)

                # Apply leverage
                if LEVERAGE and LEVERAGE > 1.0:
                    shares = (position_value * LEVERAGE) / entry_price
                    margin = position_value  # Only margin is deducted from capital
                    # Calculate liquidation price
                    if counter_trade_pending["direction"] == "LONG":
                        liquidation_price = entry_price * (1 - 1 / LEVERAGE)
                    else:  # SHORT
                        liquidation_price = entry_price * (1 + 1 / LEVERAGE)
                else:
                    shares = position_value / entry_price
                    margin = position_value
                    liquidation_price = None

                position = {
                    "direction": counter_trade_pending["direction"],
                    "entry_price": entry_price,
                    "entry_idx": i + 1,
                    "shares": shares,
                    "dynamic_tp_pct": counter_trade_pending["tp_pct"],
                    "margin": margin,
                    "liquidation_price": liquidation_price,
                }
                capital -= margin  # Deduct margin from capital
                counter_trade_pending = None

            # Priority 2: Regular signals
            elif long_entry_signal.iloc[i]:
                entry_price = bar["open"]
                position_value = capital * (POSITION_SIZE_VALUE / 100)

                # Apply leverage
                if LEVERAGE and LEVERAGE > 1.0:
                    shares = (position_value * LEVERAGE) / entry_price
                    margin = position_value
                    liquidation_price = entry_price * (1 - 1 / LEVERAGE)
                else:
                    shares = position_value / entry_price
                    margin = position_value
                    liquidation_price = None

                position = {
                    "direction": "LONG",
                    "entry_price": entry_price,
                    "entry_idx": i,
                    "shares": shares,
                    "dynamic_tp_pct": None,
                    "margin": margin,
                    "liquidation_price": liquidation_price,
                }
                capital -= margin

            elif short_entry_signal.iloc[i]:
                entry_price = bar["open"]
                position_value = capital * (POSITION_SIZE_VALUE / 100)

                # Apply leverage
                if LEVERAGE and LEVERAGE > 1.0:
                    shares = (position_value * LEVERAGE) / entry_price
                    margin = position_value
                    liquidation_price = entry_price * (1 + 1 / LEVERAGE)
                else:
                    shares = position_value / entry_price
                    margin = position_value
                    liquidation_price = None

                position = {
                    "direction": "SHORT",
                    "entry_price": entry_price,
                    "entry_idx": i,
                    "shares": shares,
                    "dynamic_tp_pct": None,
                    "margin": margin,
                    "liquidation_price": liquidation_price,
                }
                capital -= margin

    # Convert equity to Series
    equity = pd.Series(equity_series, index=df.index)

    print(f"   ✓ Backtest complete")
    print(f"   ✓ Total trades: {len(trades)}")
    if PERIODIC_CONTRIBUTION:
        print(f"   💰 Total contributions: ${total_contributions:,.2f}")
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

    if PERIODIC_CONTRIBUTION:
        trading_profit = report['final_capital'] - INITIAL_CAPITAL - total_contributions
        print(f"\nCapital Breakdown:")
        print(f"  Initial Capital:   ${INITIAL_CAPITAL:,.2f}")
        print(f"  Contributions:     ${total_contributions:,.2f}")
        print(f"  Trading Profit:    ${trading_profit:+,.2f}")
        print(f"  Final Capital:     ${report['final_capital']:,.2f}")
    print()

    # Count exit reasons
    signal_exits = sum(1 for t in trades if t["exit_reason"] == "signal")
    tp_exits = sum(1 for t in trades if "take_profit" in t["exit_reason"])
    print(f"Exit Breakdown:")
    print(f"  Signal exits: {signal_exits}")
    print(f"  Take profit (dynamic): {tp_exits}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 8. ATTRIBUTION ANALYSIS
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("📊 ATTRIBUTION ANALYSIS")
    print("=" * 80)
    print()

    # Separate regular trades from counter-trades
    regular_trades = [t for t in trades if t.get("exit_reason") != "take_profit_dynamic"]
    counter_trades = [t for t in trades if t.get("exit_reason") == "take_profit_dynamic"]

    print(f"Strategy Attribution:")
    print(f"─" * 80)
    print(f"Total Trades:        {len(trades)}")
    print(f"  Regular signals:   {len(regular_trades)} ({len(regular_trades)/len(trades)*100:.1f}%)")
    print(f"  Counter-trades:    {len(counter_trades)} ({len(counter_trades)/len(trades)*100:.1f}%)")
    print()

    # Regular trades stats
    if regular_trades:
        reg_wins = [t for t in regular_trades if t["pnl"] > 0]
        reg_losses = [t for t in regular_trades if t["pnl"] < 0]
        reg_pnl = sum(t["pnl"] for t in regular_trades)
        reg_win_rate = len(reg_wins) / len(regular_trades) * 100

        print(f"Regular Trades Performance:")
        print(f"  Total P&L:       ${reg_pnl:+,.2f}")
        print(f"  Win Rate:        {reg_win_rate:.2f}%")
        print(f"  Avg Win:         ${sum(t['pnl'] for t in reg_wins)/len(reg_wins):,.2f}" if reg_wins else "  Avg Win:         N/A")
        print(f"  Avg Loss:        ${sum(t['pnl'] for t in reg_losses)/len(reg_losses):,.2f}" if reg_losses else "  Avg Loss:        N/A")
        print()

    # Counter-trades stats
    if counter_trades:
        ct_wins = [t for t in counter_trades if t["pnl"] > 0]
        ct_losses = [t for t in counter_trades if t["pnl"] < 0]
        ct_pnl = sum(t["pnl"] for t in counter_trades)
        ct_win_rate = len(ct_wins) / len(counter_trades) * 100

        print(f"Counter-Trades Performance:")
        print(f"  Total P&L:       ${ct_pnl:+,.2f}")
        print(f"  Win Rate:        {ct_win_rate:.2f}%")
        print(f"  Avg Win:         ${sum(t['pnl'] for t in ct_wins)/len(ct_wins):,.2f}" if ct_wins else "  Avg Win:         N/A")
        print(f"  Avg Loss:        ${sum(t['pnl'] for t in ct_losses)/len(ct_losses):,.2f}" if ct_losses else "  Avg Loss:        N/A")
        print()

    # Direction breakdown
    long_trades = [t for t in trades if t["direction"] == "LONG"]
    short_trades = [t for t in trades if t["direction"] == "SHORT"]

    print(f"Direction Attribution:")
    print(f"─" * 80)

    if long_trades:
        long_pnl = sum(t["pnl"] for t in long_trades)
        long_wins = sum(1 for t in long_trades if t["pnl"] > 0)
        long_wr = long_wins / len(long_trades) * 100
        print(f"LONG Trades:     {len(long_trades)} trades | ${long_pnl:+,.2f} | WR: {long_wr:.1f}%")

    if short_trades:
        short_pnl = sum(t["pnl"] for t in short_trades)
        short_wins = sum(1 for t in short_trades if t["pnl"] > 0)
        short_wr = short_wins / len(short_trades) * 100
        print(f"SHORT Trades:    {len(short_trades)} trades | ${short_pnl:+,.2f} | WR: {short_wr:.1f}%")

    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 8.5. EXIT REASON BREAKDOWN
    # ──────────────────────────────────────────────────────────────────────────
    print(f"Exit Reason Attribution:")
    print(f"─" * 80)

    exit_reasons = {}
    for trade in trades:
        reason = trade.get("exit_reason", "unknown")
        if reason not in exit_reasons:
            exit_reasons[reason] = {"count": 0, "pnl": 0.0, "wins": 0}
        exit_reasons[reason]["count"] += 1
        exit_reasons[reason]["pnl"] += trade["pnl"]
        if trade["pnl"] > 0:
            exit_reasons[reason]["wins"] += 1

    # Sort by count descending
    sorted_reasons = sorted(exit_reasons.items(), key=lambda x: x[1]["count"], reverse=True)

    for reason, stats in sorted_reasons:
        count = stats["count"]
        pnl = stats["pnl"]
        wr = (stats["wins"] / count * 100) if count > 0 else 0.0
        pct_of_total = (count / len(trades) * 100) if trades else 0.0

        print(f"{reason:<20} {count:>5} trades ({pct_of_total:>5.1f}%) | ${pnl:>10,.2f} | WR: {wr:>5.1f}%")

    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 9. REGIME ANALYSIS
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("📊 REGIME ANALYSIS")
    print("=" * 80)
    print()

    # Use original OHLCV for regime detection (not HA)
    df_regime = df_original[["open", "high", "low", "close", "volume"]].copy()

    strategies = ["pelt_directional", "pelt_volatility", "l1_trend"]

    for strat_name in strategies:
        print(f"\n{'─' * 80}")
        print(f"Regime Strategy: {strat_name.upper()}")
        print(f"{'─' * 80}")

        segments, regime_labels = detect_regimes(df_regime, strategy=strat_name)
        regime_metrics = analyze_trades_by_regime(trades, regime_labels)
        distribution = calculate_regime_distribution(regime_labels)
        dependency_level, dependency_score = assess_regime_dependency(regime_metrics)

        print(f"\nOverview: {len(segments)} segments | Dependency: {dependency_level} (CV={dependency_score:.2f})")
        print()

        # Regime distribution and performance
        print(f"{'Regime':<15} {'Time%':>8} {'Trades':>8} {'Win Rate':>10} {'Total P&L':>12} {'Avg P&L':>12}")
        print(f"{'─' * 75}")

        for regime in sorted(distribution.keys()):
            time_pct = distribution[regime]
            m = regime_metrics.get(regime, {})
            t_count = m.get("total_trades", 0)
            wr = m.get("win_rate", 0)
            total_pnl = sum(t["pnl"] for t in trades if regime_labels.get(pd.Timestamp(t["entry_date"]), "UNKNOWN") == regime)
            avg_pnl = total_pnl / t_count if t_count > 0 else 0

            print(f"{regime:<15} {time_pct:>7.1f}% {t_count:>8} {wr:>9.1f}% ${total_pnl:>10,.2f} ${avg_pnl:>10,.2f}")

        print()

        # Best/worst regimes
        regime_pnls = {}
        for regime in distribution.keys():
            regime_pnls[regime] = sum(t["pnl"] for t in trades if regime_labels.get(pd.Timestamp(t["entry_date"]), "UNKNOWN") == regime)

        if regime_pnls:
            best_regime = max(regime_pnls, key=regime_pnls.get)
            worst_regime = min(regime_pnls, key=regime_pnls.get)
            print(f"💰 Best Regime:  {best_regime} (${regime_pnls[best_regime]:+,.2f})")
            print(f"⚠️  Worst Regime: {worst_regime} (${regime_pnls[worst_regime]:+,.2f})")

    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 10. MONTHLY TRADE CLASSIFICATION
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("📅 MONTHLY TRADE BREAKDOWN")
    print("=" * 80)

    # Group trades by month
    from collections import defaultdict
    monthly_stats = defaultdict(lambda: {
        "total_trades": 0,
        "long_trades": 0,
        "short_trades": 0,
        "counter_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "total_pnl": 0.0,
        "signal_exits": 0,
        "tp_exits": 0,
        "liquidations": 0,
        "force_closes": 0,
    })

    for trade in trades:
        entry_date = pd.to_datetime(trade["entry_date"])
        month_key = entry_date.strftime("%Y-%m")

        stats = monthly_stats[month_key]
        stats["total_trades"] += 1

        # Direction
        if trade["direction"] == "LONG":
            stats["long_trades"] += 1
        else:
            stats["short_trades"] += 1

        # Win/Loss
        if trade["pnl"] > 0:
            stats["winning_trades"] += 1
        else:
            stats["losing_trades"] += 1

        # P&L
        stats["total_pnl"] += trade["pnl"]

        # Exit reason
        exit_reason = trade["exit_reason"]
        if exit_reason == "signal":
            stats["signal_exits"] += 1
        elif exit_reason == "take_profit_dynamic":
            stats["counter_trades"] += 1
            stats["tp_exits"] += 1
        elif exit_reason == "liquidation":
            stats["liquidations"] += 1
        elif exit_reason == "force_close":
            stats["force_closes"] += 1

    # Print monthly table
    print()
    print(f"{'Month':<10} {'Trades':>7} {'Long':>5} {'Short':>6} {'Counter':>8} {'Win':>5} {'Loss':>5} {'P&L':>12} {'Exits':<25}")
    print("─" * 100)

    cumulative_pnl = INITIAL_CAPITAL
    for month in sorted(monthly_stats.keys()):
        stats = monthly_stats[month]
        cumulative_pnl += stats["total_pnl"]

        # Exit breakdown
        exit_details = []
        if stats["signal_exits"] > 0:
            exit_details.append(f"Sig:{stats['signal_exits']}")
        if stats["tp_exits"] > 0:
            exit_details.append(f"TP:{stats['tp_exits']}")
        if stats["liquidations"] > 0:
            exit_details.append(f"Liq:{stats['liquidations']}")
        if stats["force_closes"] > 0:
            exit_details.append(f"FC:{stats['force_closes']}")
        exit_str = ", ".join(exit_details) if exit_details else "None"

        pnl_symbol = "+" if stats["total_pnl"] >= 0 else ""

        print(f"{month:<10} {stats['total_trades']:>7} {stats['long_trades']:>5} {stats['short_trades']:>6} "
              f"{stats['counter_trades']:>8} {stats['winning_trades']:>5} {stats['losing_trades']:>5} "
              f"{pnl_symbol}${stats['total_pnl']:>10,.2f} {exit_str:<25}")

    print("─" * 100)
    print(f"{'TOTAL':<10} {sum(s['total_trades'] for s in monthly_stats.values()):>7} "
          f"{sum(s['long_trades'] for s in monthly_stats.values()):>5} "
          f"{sum(s['short_trades'] for s in monthly_stats.values()):>6} "
          f"{sum(s['counter_trades'] for s in monthly_stats.values()):>8} "
          f"{sum(s['winning_trades'] for s in monthly_stats.values()):>5} "
          f"{sum(s['losing_trades'] for s in monthly_stats.values()):>5} "
          f"+${sum(s['total_pnl'] for s in monthly_stats.values()):>10,.2f}")

    print()
    print(f"Final Equity: ${cumulative_pnl:,.2f}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 11. TRADE LOG
    # ──────────────────────────────────────────────────────────────────────────
    # print("=" * 80)
    # print("📋 TRADE LOG (Last 15 Trades)")
    # print("=" * 80)

    for i, trade in enumerate(trades[-15:], 1):
        direction = trade.get("direction", "LONG")
        entry_date = pd.to_datetime(trade["entry_date"]).strftime("%Y-%m-%d")
        exit_date = pd.to_datetime(trade["exit_date"]).strftime("%Y-%m-%d")
        pnl_pct = trade["pnl_pct"]
        exit_reason = trade["exit_reason"]

        pnl_symbol = "📈" if pnl_pct > 0 else "📉"

        # print(f"{pnl_symbol} Trade #{len(trades)-15+i} ({direction})")
        # print(f"   Entry:  {entry_date} @ ${trade['entry_price']:,.2f}")
        # print(f"   Exit:   {exit_date} @ ${trade['exit_price']:,.2f}")
        # print(f"   P&L:    {pnl_pct:+.2f}% (${trade['pnl']:+,.2f})")
        # print(f"   Reason: {exit_reason}")
        # print()

    print("=" * 80)
    print("✅ Smoke test complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
