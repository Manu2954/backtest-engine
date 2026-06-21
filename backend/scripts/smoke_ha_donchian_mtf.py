"""
Heikin Ashi + Donchian Channel + SMA50 Multi-Timeframe Strategy

Strategy Logic:
  4H TIMEFRAME (Regime Detection):
    - DC mid crosses BELOW SMA50 → SHORT regime (take shorts on 5M)
    - DC mid crosses ABOVE SMA50 → LONG regime (take longs on 5M)
    - Regime flips when opposite cross occurs

  5M TIMEFRAME (Trade Execution):
    FIRST ENTRY (after 4H regime change):
      - Enter immediately on next 5M bar
      - SL = high/low of most recent 5M cross candle before the 4H signal
      - SHORT: SL = high of that candle
      - LONG: SL = low of that candle

    RE-ENTRIES (within same regime, after a trade closes):
      - SHORT regime: Wait for 5M DC mid CROSSES_BELOW 50MA
        - Condition: previous 5M cross-above candle's high > current candle's open
        - SL = that cross-above candle's high
      - LONG regime: Wait for 5M DC mid CROSSES_ABOVE 50MA
        - Condition: previous 5M cross-below candle's low < current candle's open
        - SL = that cross-below candle's low

    EXIT:
      - SHORT: 5M DC mid crosses ABOVE 50MA
      - LONG: 5M DC mid crosses BELOW 50MA
      - Or SL hit

All indicators calculated on Heikin Ashi candles for both timeframes.
Fills happen at real OHLC prices.

Usage:
  python scripts/smoke_ha_donchian_mtf.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv
from app.engine.indicator_layer import compute_indicators, trim_warmup_period
from app.engine.condition_engine import evaluate_conditions
from app.engine.report_generator import generate_report


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TICKER = "BTCUSDT"
# Last 6 months
END = datetime.now().strftime("%Y-%m-%d")
START = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

RESOLUTION_4H = "4h"
RESOLUTION_5M = "5m"
ASSET_CLASS = "CRYPTO"
INITIAL_CAPITAL = 100.0
LEVERAGE = 5.0

# Position sizing
POSITION_SIZE_TYPE = "percent_capital"
POSITION_SIZE_VALUE = 95.0  # 95% of capital per trade

# Risk management
COMMISSION_PCT = 0.1  # 0.1% commission

# Donchian period (same as existing script)
DONCHIAN_PERIOD = 20
SMA_PERIOD = 50


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def prepare_ha_data(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Heikin Ashi and indicators, replace OHLC with HA."""
    # Compute Heikin Ashi
    ha_indicator = [{"indicator_type": "HEIKINASHI", "alias": "ha", "params": {}}]
    df = compute_indicators(df, ha_indicator)

    # Store original OHLC for fills
    df["real_open"] = df["open"].copy()
    df["real_high"] = df["high"].copy()
    df["real_low"] = df["low"].copy()
    df["real_close"] = df["close"].copy()

    # Replace OHLC with Heikin Ashi for indicator calculations
    df["open"] = df["ha_open"]
    df["high"] = df["ha_high"]
    df["low"] = df["ha_low"]
    df["close"] = df["ha_close"]

    # Compute indicators on HA
    indicators = [
        {"indicator_type": "DONCHIAN", "alias": "dc_20", "params": {"period": DONCHIAN_PERIOD}},
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": SMA_PERIOD, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)

    return df


def add_cross_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Add cross signals using the engine's evaluate_conditions (correct crossover logic)."""

    # DC mid CROSSES_ABOVE SMA50
    cross_above_condition = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "dc_20_mid",
                "operator": "CROSSES_ABOVE",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_50",
            }
        ],
    }
    df["cross_above"] = evaluate_conditions(df, cross_above_condition)

    # DC mid CROSSES_BELOW SMA50
    cross_below_condition = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "dc_20_mid",
                "operator": "CROSSES_BELOW",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_50",
            }
        ],
    }
    df["cross_below"] = evaluate_conditions(df, cross_below_condition)

    return df


def find_most_recent_cross(df_5m: pd.DataFrame, before_timestamp: pd.Timestamp, cross_type: str = None) -> dict | None:
    """
    Find the most recent cross in 5M data before the given timestamp.
    Returns dict with candle info or None if not found.
    """
    mask = df_5m.index < before_timestamp

    if cross_type == "above":
        cross_mask = mask & df_5m["cross_above"]
    elif cross_type == "below":
        cross_mask = mask & df_5m["cross_below"]
    else:
        # Any cross
        cross_mask = mask & (df_5m["cross_above"] | df_5m["cross_below"])

    if not cross_mask.any():
        return None

    cross_idx = df_5m.index[cross_mask][-1]
    row = df_5m.loc[cross_idx]

    return {
        "timestamp": cross_idx,
        "high": row["real_high"],
        "low": row["real_low"],
        "is_cross_above": row["cross_above"],
        "is_cross_below": row["cross_below"],
    }


def find_previous_opposite_cross(df_5m: pd.DataFrame, current_idx: int, regime: str) -> dict | None:
    """
    Find the previous opposite cross for re-entry logic.
    For SHORT regime: find previous cross_above
    For LONG regime: find previous cross_below
    """
    current_timestamp = df_5m.index[current_idx]
    cross_type = "above" if regime == "SHORT" else "below"

    return find_most_recent_cross(df_5m, current_timestamp, cross_type)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("Heikin Ashi + Donchian + SMA50 Multi-Timeframe Strategy")
    print("=" * 80)
    print(f"Ticker: {TICKER}")
    print(f"Period: {START} to {END}")
    print(f"Timeframes: {RESOLUTION_4H} (regime) + {RESOLUTION_5M} (execution)")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print(f"Leverage: {LEVERAGE}x")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. FETCH DATA FOR BOTH TIMEFRAMES
    # ──────────────────────────────────────────────────────────────────────────
    print("📊 Fetching OHLCV data...")

    df_4h = fetch_ohlcv(
        ticker=TICKER,
        start=START,
        end=END,
        resolution=RESOLUTION_4H,
        asset_class=ASSET_CLASS,
    )
    print(f"   ✓ 4H data: {len(df_4h)} bars")

    df_5m = fetch_ohlcv(
        ticker=TICKER,
        start=START,
        end=END,
        resolution=RESOLUTION_5M,
        asset_class=ASSET_CLASS,
    )
    print(f"   ✓ 5M data: {len(df_5m)} bars")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. COMPUTE HEIKIN ASHI AND INDICATORS
    # ──────────────────────────────────────────────────────────────────────────
    print("📈 Computing Heikin Ashi and indicators...")

    df_4h = prepare_ha_data(df_4h)
    df_5m = prepare_ha_data(df_5m)

    # Trim warmup
    df_4h, warmup_4h = trim_warmup_period(df_4h)
    df_5m, warmup_5m = trim_warmup_period(df_5m)

    # Add cross signals AFTER warmup trim using engine's evaluate_conditions
    df_4h = add_cross_signals(df_4h)
    df_5m = add_cross_signals(df_5m)

    print(f"   ✓ 4H after warmup: {len(df_4h)} bars (trimmed {warmup_4h})")
    print(f"   ✓ 5M after warmup: {len(df_5m)} bars (trimmed {warmup_5m})")
    print(f"   ✓ 4H cross_above signals: {df_4h['cross_above'].sum()}")
    print(f"   ✓ 4H cross_below signals: {df_4h['cross_below'].sum()}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 3. IDENTIFY 4H REGIME CHANGES
    # ──────────────────────────────────────────────────────────────────────────
    print("🎯 Identifying 4H regime changes...")

    regime_changes = []
    for i in range(len(df_4h)):
        ts = df_4h.index[i]
        if df_4h["cross_below"].iloc[i]:
            regime_changes.append({"timestamp": ts, "regime": "SHORT"})
        elif df_4h["cross_above"].iloc[i]:
            regime_changes.append({"timestamp": ts, "regime": "LONG"})

    print(f"   ✓ Found {len(regime_changes)} regime changes")
    for rc in regime_changes[:5]:
        print(f"      {rc['timestamp']} → {rc['regime']}")
    if len(regime_changes) > 5:
        print(f"      ... and {len(regime_changes) - 5} more")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. CUSTOM BACKTEST ON 5M DATA
    # ──────────────────────────────────────────────────────────────────────────
    print("🔄 Running multi-timeframe backtest...")

    capital = INITIAL_CAPITAL
    position = None  # {"direction", "entry_price", "entry_idx", "shares", "sl_price", "margin", "liquidation_price"}
    trades = []
    equity_series = []

    current_regime = None  # "LONG" or "SHORT"
    regime_start_idx = None  # 5M index where regime started
    first_entry_taken = False  # Track if first entry of regime is done
    regime_change_queue = list(regime_changes)  # Queue of pending regime changes

    for i in range(len(df_5m)):
        bar = df_5m.iloc[i]
        ts = df_5m.index[i]

        # ──────────────────────────────────────────────────────────────────
        # CHECK FOR REGIME CHANGE
        # ──────────────────────────────────────────────────────────────────
        while regime_change_queue and regime_change_queue[0]["timestamp"] <= ts:
            new_regime = regime_change_queue.pop(0)

            # Close any open position on regime change
            if position is not None:
                exit_price = bar["real_open"]
                exit_reason = "regime_change"

                # Calculate P&L
                if position["direction"] == "LONG":
                    gross_pnl = (exit_price - position["entry_price"]) * position["shares"]
                    pnl_pct = ((exit_price - position["entry_price"]) / position["entry_price"]) * 100
                else:
                    gross_pnl = (position["entry_price"] - exit_price) * position["shares"]
                    pnl_pct = ((position["entry_price"] - exit_price) / position["entry_price"]) * 100

                # Commission
                notional = position["entry_price"] * position["shares"]
                exit_notional = exit_price * position["shares"]
                commission = (COMMISSION_PCT / 100) * (notional + exit_notional)
                net_pnl = gross_pnl - commission

                # Return margin + P&L
                capital += position["margin"] + net_pnl

                entry_date = df_5m.index[position["entry_idx"]]
                trade_duration = (ts - entry_date).total_seconds() / 86400

                trades.append({
                    "direction": position["direction"],
                    "entry_date": entry_date,
                    "entry_price": position["entry_price"],
                    "exit_date": ts,
                    "exit_price": exit_price,
                    "shares": position["shares"],
                    "pnl": net_pnl,
                    "pnl_pct": pnl_pct,
                    "exit_reason": exit_reason,
                    "trade_duration_days": trade_duration,
                    "sl_price": position["sl_price"],
                })

                position = None

            current_regime = new_regime["regime"]
            regime_start_idx = i
            first_entry_taken = False

        # ──────────────────────────────────────────────────────────────────
        # TRACK EQUITY
        # ──────────────────────────────────────────────────────────────────
        if position is None:
            current_equity = capital
        else:
            if position["direction"] == "LONG":
                unrealized_pnl = (bar["real_close"] - position["entry_price"]) * position["shares"]
            else:
                unrealized_pnl = (position["entry_price"] - bar["real_close"]) * position["shares"]
            current_equity = capital + position["margin"] + unrealized_pnl

        equity_series.append(current_equity)

        # Skip if no regime active
        if current_regime is None:
            continue

        # ──────────────────────────────────────────────────────────────────
        # EXIT LOGIC (check before entry)
        # ──────────────────────────────────────────────────────────────────
        if position is not None:
            exit_triggered = False
            exit_reason = None
            exit_price = None

            # Check liquidation
            if position.get("liquidation_price") is not None:
                if position["direction"] == "LONG":
                    if bar["real_low"] <= position["liquidation_price"]:
                        exit_triggered = True
                        exit_price = position["liquidation_price"]
                        exit_reason = "liquidation"
                else:
                    if bar["real_high"] >= position["liquidation_price"]:
                        exit_triggered = True
                        exit_price = position["liquidation_price"]
                        exit_reason = "liquidation"

            # Check stop loss
            if not exit_triggered and position.get("sl_price") is not None:
                if position["direction"] == "LONG":
                    if bar["real_low"] <= position["sl_price"]:
                        exit_triggered = True
                        exit_price = position["sl_price"]
                        exit_reason = "stop_loss"
                else:  # SHORT
                    if bar["real_high"] >= position["sl_price"]:
                        exit_triggered = True
                        exit_price = position["sl_price"]
                        exit_reason = "stop_loss"

            # Check signal exit (opposite cross on 5M)
            if not exit_triggered:
                if position["direction"] == "LONG" and df_5m["cross_below"].iloc[i]:
                    exit_triggered = True
                    exit_price = bar["real_open"]
                    exit_reason = "signal"
                elif position["direction"] == "SHORT" and df_5m["cross_above"].iloc[i]:
                    exit_triggered = True
                    exit_price = bar["real_open"]
                    exit_reason = "signal"

            # Force close on last bar
            if not exit_triggered and i == len(df_5m) - 1:
                exit_triggered = True
                exit_price = bar["real_close"]
                exit_reason = "force_close"

            # Execute exit
            if exit_triggered:
                if position["direction"] == "LONG":
                    gross_pnl = (exit_price - position["entry_price"]) * position["shares"]
                    pnl_pct = ((exit_price - position["entry_price"]) / position["entry_price"]) * 100
                else:
                    gross_pnl = (position["entry_price"] - exit_price) * position["shares"]
                    pnl_pct = ((position["entry_price"] - exit_price) / position["entry_price"]) * 100

                notional = position["entry_price"] * position["shares"]
                exit_notional = exit_price * position["shares"]
                commission = (COMMISSION_PCT / 100) * (notional + exit_notional)
                net_pnl = gross_pnl - commission

                capital += position["margin"] + net_pnl

                entry_date = df_5m.index[position["entry_idx"]]
                trade_duration = (ts - entry_date).total_seconds() / 86400

                trades.append({
                    "direction": position["direction"],
                    "entry_date": entry_date,
                    "entry_price": position["entry_price"],
                    "exit_date": ts,
                    "exit_price": exit_price,
                    "shares": position["shares"],
                    "pnl": net_pnl,
                    "pnl_pct": pnl_pct,
                    "exit_reason": exit_reason,
                    "trade_duration_days": trade_duration,
                    "sl_price": position["sl_price"],
                })

                position = None

        # ──────────────────────────────────────────────────────────────────
        # ENTRY LOGIC
        # ──────────────────────────────────────────────────────────────────
        if position is None and i < len(df_5m) - 1 and capital > 0:
            entry_triggered = False
            sl_price = None
            direction = current_regime

            # FIRST ENTRY: immediately after regime change
            if not first_entry_taken and i == regime_start_idx:
                # Find most recent cross in 5M before the 4H regime change
                regime_change_ts = None
                for rc in regime_changes:
                    if rc["regime"] == current_regime:
                        # Find the 4H timestamp that triggered this regime
                        for rc2 in regime_changes:
                            if rc2["regime"] == current_regime and df_5m.index[regime_start_idx] >= rc2["timestamp"]:
                                regime_change_ts = rc2["timestamp"]
                                break
                        break

                if regime_change_ts is None:
                    regime_change_ts = ts

                prev_cross = find_most_recent_cross(df_5m, regime_change_ts)

                if prev_cross is not None:
                    if direction == "SHORT":
                        sl_price = prev_cross["high"]
                    else:
                        sl_price = prev_cross["low"]
                    entry_triggered = True
                    first_entry_taken = True

            # RE-ENTRY: after a trade closes, wait for appropriate cross
            elif first_entry_taken:
                if direction == "SHORT" and df_5m["cross_below"].iloc[i]:
                    # Check condition: previous cross-above high > current open
                    prev_cross = find_previous_opposite_cross(df_5m, i, "SHORT")
                    if prev_cross is not None and prev_cross["high"] > bar["real_open"]:
                        sl_price = prev_cross["high"]
                        entry_triggered = True

                elif direction == "LONG" and df_5m["cross_above"].iloc[i]:
                    # Check condition: previous cross-below low < current open
                    prev_cross = find_previous_opposite_cross(df_5m, i, "LONG")
                    if prev_cross is not None and prev_cross["low"] < bar["real_open"]:
                        sl_price = prev_cross["low"]
                        entry_triggered = True

            # Execute entry
            if entry_triggered and sl_price is not None:
                entry_price = bar["real_open"]
                position_value = capital * (POSITION_SIZE_VALUE / 100)

                # Apply leverage
                if LEVERAGE > 1.0:
                    shares = (position_value * LEVERAGE) / entry_price
                    margin = position_value
                    if direction == "LONG":
                        liquidation_price = entry_price * (1 - 1 / LEVERAGE)
                    else:
                        liquidation_price = entry_price * (1 + 1 / LEVERAGE)
                else:
                    shares = position_value / entry_price
                    margin = position_value
                    liquidation_price = None

                position = {
                    "direction": direction,
                    "entry_price": entry_price,
                    "entry_idx": i,
                    "shares": shares,
                    "sl_price": sl_price,
                    "margin": margin,
                    "liquidation_price": liquidation_price,
                }
                capital -= margin

    # Convert equity to Series
    equity = pd.Series(equity_series, index=df_5m.index)

    print(f"   ✓ Backtest complete")
    print(f"   ✓ Total trades: {len(trades)}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. GENERATE REPORT
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
    # 6. ATTRIBUTION ANALYSIS
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("📊 ATTRIBUTION ANALYSIS")
    print("=" * 80)
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

    # Exit reason breakdown
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

    sorted_reasons = sorted(exit_reasons.items(), key=lambda x: x[1]["count"], reverse=True)

    for reason, stats in sorted_reasons:
        count = stats["count"]
        pnl = stats["pnl"]
        wr = (stats["wins"] / count * 100) if count > 0 else 0.0
        pct_of_total = (count / len(trades) * 100) if trades else 0.0

        print(f"{reason:<20} {count:>5} trades ({pct_of_total:>5.1f}%) | ${pnl:>10,.2f} | WR: {wr:>5.1f}%")

    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 7. MONTHLY BREAKDOWN
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("📅 MONTHLY TRADE BREAKDOWN")
    print("=" * 80)

    monthly_stats = defaultdict(lambda: {
        "total_trades": 0,
        "long_trades": 0,
        "short_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "total_pnl": 0.0,
        "signal_exits": 0,
        "sl_exits": 0,
        "liquidations": 0,
        "regime_changes": 0,
        "force_closes": 0,
    })

    for trade in trades:
        entry_date = pd.to_datetime(trade["entry_date"])
        month_key = entry_date.strftime("%Y-%m")

        stats = monthly_stats[month_key]
        stats["total_trades"] += 1

        if trade["direction"] == "LONG":
            stats["long_trades"] += 1
        else:
            stats["short_trades"] += 1

        if trade["pnl"] > 0:
            stats["winning_trades"] += 1
        else:
            stats["losing_trades"] += 1

        stats["total_pnl"] += trade["pnl"]

        exit_reason = trade["exit_reason"]
        if exit_reason == "signal":
            stats["signal_exits"] += 1
        elif exit_reason == "stop_loss":
            stats["sl_exits"] += 1
        elif exit_reason == "liquidation":
            stats["liquidations"] += 1
        elif exit_reason == "regime_change":
            stats["regime_changes"] += 1
        elif exit_reason == "force_close":
            stats["force_closes"] += 1

    print()
    print(f"{'Month':<10} {'Trades':>7} {'Long':>5} {'Short':>6} {'Win':>5} {'Loss':>5} {'P&L':>12} {'Exits':<30}")
    print("─" * 100)

    cumulative_pnl = INITIAL_CAPITAL
    for month in sorted(monthly_stats.keys()):
        stats = monthly_stats[month]
        cumulative_pnl += stats["total_pnl"]

        exit_details = []
        if stats["signal_exits"] > 0:
            exit_details.append(f"Sig:{stats['signal_exits']}")
        if stats["sl_exits"] > 0:
            exit_details.append(f"SL:{stats['sl_exits']}")
        if stats["liquidations"] > 0:
            exit_details.append(f"Liq:{stats['liquidations']}")
        if stats["regime_changes"] > 0:
            exit_details.append(f"Reg:{stats['regime_changes']}")
        if stats["force_closes"] > 0:
            exit_details.append(f"FC:{stats['force_closes']}")
        exit_str = ", ".join(exit_details) if exit_details else "None"

        pnl_symbol = "+" if stats["total_pnl"] >= 0 else ""

        print(f"{month:<10} {stats['total_trades']:>7} {stats['long_trades']:>5} {stats['short_trades']:>6} "
              f"{stats['winning_trades']:>5} {stats['losing_trades']:>5} "
              f"{pnl_symbol}${stats['total_pnl']:>10,.2f} {exit_str:<30}")

    print("─" * 100)
    print(f"{'TOTAL':<10} {sum(s['total_trades'] for s in monthly_stats.values()):>7} "
          f"{sum(s['long_trades'] for s in monthly_stats.values()):>5} "
          f"{sum(s['short_trades'] for s in monthly_stats.values()):>6} "
          f"{sum(s['winning_trades'] for s in monthly_stats.values()):>5} "
          f"{sum(s['losing_trades'] for s in monthly_stats.values()):>5} "
          f"+${sum(s['total_pnl'] for s in monthly_stats.values()):>10,.2f}")

    print()
    print(f"Final Equity: ${cumulative_pnl:,.2f}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 8. SAMPLE TRADES
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("📋 SAMPLE TRADES (First 10)")
    print("=" * 80)

    for i, trade in enumerate(trades[:10], 1):
        direction = trade["direction"]
        entry_date = pd.to_datetime(trade["entry_date"]).strftime("%Y-%m-%d %H:%M")
        exit_date = pd.to_datetime(trade["exit_date"]).strftime("%Y-%m-%d %H:%M")
        pnl_pct = trade["pnl_pct"]
        exit_reason = trade["exit_reason"]
        sl_price = trade.get("sl_price", "N/A")

        pnl_symbol = "📈" if pnl_pct > 0 else "📉"

        print(f"{pnl_symbol} Trade #{i} ({direction})")
        print(f"   Entry:  {entry_date} @ ${trade['entry_price']:,.2f}")
        print(f"   Exit:   {exit_date} @ ${trade['exit_price']:,.2f}")
        print(f"   SL:     ${sl_price:,.2f}" if isinstance(sl_price, float) else f"   SL:     {sl_price}")
        print(f"   P&L:    {pnl_pct:+.2f}% (${trade['pnl']:+,.2f})")
        print(f"   Reason: {exit_reason}")
        print()

    print("=" * 80)
    print("✅ Smoke test complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
