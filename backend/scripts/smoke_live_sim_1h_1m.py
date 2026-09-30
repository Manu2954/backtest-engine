"""
LIVE-SIMULATION Backtest: 1h signals with FORMING-bar indicators, executed at 5m.

GOAL
────
Faithfully reproduce the LIVE trading experience on past data. When you watch a
1h chart, the Donchian/SMA lines MOVE as the current candle forms (they include
the still-forming partial hour). You enter the moment dc_mid crosses sma_50 on
those live, moving lines — without waiting for the 1h candle to close.

This script simulates exactly that:
  - Step through time at EXEC_RESOLUTION granularity (5m for now).
  - At each step, build the FORMING 1h candle from the finer bars seen so far
    THIS hour (open fixed at hour start; high/low/close live up to "now").
  - Recompute Donchian(20)+SMA(50) on [closed 1h bars ... + forming 1h bar].
  - Detect the cross the moment the live lines touch (this step vs previous step).
  - Enter at the current price. Exit symmetrically on the live cross-back.

NO LOOKAHEAD (the one hard rule)
────────────────────────────────
At simulated time T, only bars with timestamp <= T are used. The forming 1h
candle at minute M is built solely from finer bars <= M. We NEVER read the
finished 1h close before the hour actually ends. An assertion enforces this.

This mode = TradingView's realtime-bar / ta4j's live-candle mode. Repainting is
EXPECTED and correct: a cross can reverse before the hour closes, but you acted
on it live, so the trade is real. Repainting is only a bug when a backtest uses
the FINISHED bar values as if known mid-bar — which we do not.

Refs: docs/MTF_RESEARCH_FINDINGS.txt

Usage:
  python scripts/smoke_live_sim_1h_1m.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION  (overridable via env vars so the SAME script serves every run,
# e.g.  EXEC_RESOLUTION=5m LEVERAGE=2 python scripts/smoke_live_sim_1h_1m.py)
# ═══════════════════════════════════════════════════════════════════════════════

import os

TICKER = os.environ.get("TICKER", "BTCUSDT")
START = os.environ.get("START", "2026-01-01")
END = os.environ.get("END", "2026-12-31")
ASSET_CLASS = "CRYPTO"

SIGNAL_RESOLUTION = "1h"    # timeframe the indicators/chart are drawn on
EXEC_RESOLUTION = os.environ.get("EXEC_RESOLUTION", "1m")  # sim step granularity

DONCHIAN_PERIOD = 20
SMA_PERIOD = 50

INITIAL_CAPITAL = 100.0
LEVERAGE = float(os.environ.get("LEVERAGE", "5.0"))
POSITION_SIZE_VALUE = 95.0  # % of capital per trade
COMMISSION_PCT = 0.1        # 0.1% per side

USE_HEIKIN_ASHI = os.environ.get("USE_HEIKIN_ASHI", "1") == "1"  # HA candles

# Engine data is naive-UTC. Display trade times in this zone so they match the
# Binance/TradingView chart you watch. IST = UTC+5:30.
DISPLAY_TZ_OFFSET_HOURS = 5.5   # Asia/Kolkata (IST). Set 0.0 to show raw UTC.
DISPLAY_TZ_LABEL = "IST"

# Counter-trade (same rule as smoke_ha_donchian_sma_custom.py)
ENABLE_COUNTER_TRADES = True
COUNTER_TP_MULTIPLIER = 1.5

# How many trailing 1h bars to recompute indicators on each step.
# Must exceed max(SMA_PERIOD, DONCHIAN_PERIOD) with a safety margin.
INDICATOR_WINDOW = max(SMA_PERIOD, DONCHIAN_PERIOD) + 10


# ═══════════════════════════════════════════════════════════════════════════════
# HEIKIN ASHI (vectorized, on a closed-bar 1h frame — used for the STABLE history)
# ═══════════════════════════════════════════════════════════════════════════════

def heikin_ashi(o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray):
    """Return HA (open, high, low, close) arrays. Recursive ha_open."""
    n = len(c)
    ha_close = (o + h + l + c) / 4.0
    ha_open = np.empty(n, dtype=float)
    if n == 0:
        return ha_open, ha_open.copy(), ha_open.copy(), ha_close
    ha_open[0] = (o[0] + c[0]) / 2.0
    for i in range(1, n):
        ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2.0
    ha_high = np.maximum.reduce([h, ha_open, ha_close])
    ha_low = np.minimum.reduce([l, ha_open, ha_close])
    return ha_open, ha_high, ha_low, ha_close


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE INDICATOR COMPUTATION on [closed 1h bars + forming 1h bar]
# ═══════════════════════════════════════════════════════════════════════════════

def compute_live_dc_sma(o, h, l, c):
    """
    Compute dc_mid and sma_50 on the given OHLC arrays (already HA-transformed if
    USE_HEIKIN_ASHI). The LAST element is the forming bar. Returns (dc_mid, sma)
    for the last (forming) bar only. No lookahead: arrays contain only bars <= now.
    """
    n = len(c)
    if n < max(SMA_PERIOD, DONCHIAN_PERIOD):
        return np.nan, np.nan

    if USE_HEIKIN_ASHI:
        _, h, l, c = heikin_ashi(o, h, l, c)

    # SMA(50) on close — last bar
    sma = c[-SMA_PERIOD:].mean()

    # Donchian(20) mid — last bar: (max high + min low) over last DONCHIAN_PERIOD
    dc_upper = h[-DONCHIAN_PERIOD:].max()
    dc_lower = l[-DONCHIAN_PERIOD:].min()
    dc_mid = (dc_upper + dc_lower) / 2.0

    return dc_mid, sma


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("LIVE-SIM Backtest: 1h forming-bar indicators, executed at " + EXEC_RESOLUTION)
    print("=" * 80)
    print(f"Ticker: {TICKER}   Period: {START} to {END}")
    print(f"Signal TF: {SIGNAL_RESOLUTION}   Exec step: {EXEC_RESOLUTION}")
    print(f"Heikin Ashi: {USE_HEIKIN_ASHI}   Leverage: {LEVERAGE}x   Counter-trades: {ENABLE_COUNTER_TRADES}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. FETCH DATA — closed 1h bars (history) + fine exec bars (stepping)
    # ──────────────────────────────────────────────────────────────────────────
    print("📊 Fetching data...")
    df_1h = fetch_ohlcv(TICKER, START, END, SIGNAL_RESOLUTION, ASSET_CLASS)
    df_ex = fetch_ohlcv(TICKER, START, END, EXEC_RESOLUTION, ASSET_CLASS)
    print(f"   ✓ {SIGNAL_RESOLUTION}: {len(df_1h)} bars    {EXEC_RESOLUTION}: {len(df_ex)} bars")
    print()

    # Both are naive-UTC DatetimeIndex (per data-layer). Align by flooring exec
    # timestamps to the hour to know which 1h bucket each exec bar belongs to.
    df_1h = df_1h.sort_index()
    df_ex = df_ex.sort_index()

    # Closed 1h bars as arrays for fast slicing
    h1_ts = df_1h.index.values
    h1_o = df_1h["open"].to_numpy(float)
    h1_h = df_1h["high"].to_numpy(float)
    h1_l = df_1h["low"].to_numpy(float)
    h1_c = df_1h["close"].to_numpy(float)

    # For each exec bar, the hour bucket it belongs to
    ex_hour = df_ex.index.floor("h")

    # ── CLOSED-bar reference series (the "previous closed candle" anchor) ──
    # dc_mid and sma computed on FULLY CLOSED 1h bars. During any forming hour,
    # the arming reference is the value at the LAST CLOSED bar — a FIXED level
    # held for the whole hour. This is the shift(1) reference of CROSSES_ABOVE,
    # anchored to the previous CLOSED candle (not the previous step).
    if USE_HEIKIN_ASHI:
        _, ch, cl, cc_ha = heikin_ashi(h1_o, h1_h, h1_l, h1_c)
    else:
        ch, cl, cc_ha = h1_h, h1_l, h1_c
    n1 = len(h1_c)
    closed_dcmid = np.full(n1, np.nan)
    closed_sma = np.full(n1, np.nan)
    for k in range(n1):
        if k + 1 >= max(SMA_PERIOD, DONCHIAN_PERIOD):
            closed_sma[k] = cc_ha[k + 1 - SMA_PERIOD:k + 1].mean()
            closed_dcmid[k] = (ch[k + 1 - DONCHIAN_PERIOD:k + 1].max()
                               + cl[k + 1 - DONCHIAN_PERIOD:k + 1].min()) / 2.0

    # ──────────────────────────────────────────────────────────────────────────
    # 2. STEP THROUGH EXEC BARS, BUILDING THE FORMING 1h CANDLE LIVE
    # ──────────────────────────────────────────────────────────────────────────
    print("🔄 Simulating live chart step-by-step...")

    capital = INITIAL_CAPITAL
    position = None           # dict or None
    trades = []
    counter_trade_pending = None
    last_entry_hour = None    # idempotency guard (ta4j): one entry per cross/hour

    prev_hour = None

    # running forming-bar accumulators for the CURRENT hour
    f_open = f_high = f_low = f_close = np.nan
    lookahead_violations = 0

    ex_ts = df_ex.index
    ex_o = df_ex["open"].to_numpy(float)
    ex_h = df_ex["high"].to_numpy(float)
    ex_l = df_ex["low"].to_numpy(float)
    ex_c = df_ex["close"].to_numpy(float)

    for i in range(len(df_ex)):
        now = ex_ts[i]
        hour = ex_hour[i]

        # New hour started → reset forming bar
        if hour != prev_hour:
            f_open = ex_o[i]
            f_high = ex_h[i]
            f_low = ex_l[i]
            prev_hour = hour
        else:
            f_high = max(f_high, ex_h[i])
            f_low = min(f_low, ex_l[i])
        f_close = ex_c[i]  # live close = current price

        # Closed 1h bars STRICTLY before this hour (no lookahead: exclude current)
        # searchsorted on hour start gives count of 1h bars with ts < hour.
        n_closed = np.searchsorted(h1_ts, np.datetime64(hour), side="left")

        # NO-LOOKAHEAD CHECK: the newest closed 1h bar must end at/before `now`.
        if n_closed > 0:
            newest_closed_ts = h1_ts[n_closed - 1]
            # that bar covers [ts, ts+1h); it is only "closed" once now >= ts+1h
            if newest_closed_ts + np.timedelta64(1, "h") > np.datetime64(now):
                lookahead_violations += 1

        if n_closed < INDICATOR_WINDOW:
            prev_hour = hour
            continue

        # Build live series: last INDICATOR_WINDOW closed bars + forming bar
        lo = n_closed - INDICATOR_WINDOW
        o = np.append(h1_o[lo:n_closed], f_open)
        hh = np.append(h1_h[lo:n_closed], f_high)
        ll = np.append(h1_l[lo:n_closed], f_low)
        cc = np.append(h1_c[lo:n_closed], f_close)

        dc_mid, sma = compute_live_dc_sma(o, hh, ll, cc)

        # ── CROSS DETECTION (Reading A) ──
        # L = dc_mid, R = sma. BOTH are computed on the LIVE forming candle.
        # The arming "was below/above" reference is the PREVIOUS CLOSED candle
        # (a FIXED level held for the whole hour), NOT the previous step.
        # This is CROSSES_ABOVE(L, R) evaluated live, with shift(1) anchored to
        # the last closed bar — matches watching two moving lines cross, knowing
        # which side they were on at the last close. No flicker from a moving ref.
        ref_dc = closed_dcmid[n_closed - 1]
        ref_sma = closed_sma[n_closed - 1]
        cross_above = (
            not np.isnan(ref_dc) and not np.isnan(dc_mid)
            and ref_dc <= ref_sma and dc_mid > sma
        )
        cross_below = (
            not np.isnan(ref_dc) and not np.isnan(dc_mid)
            and ref_dc >= ref_sma and dc_mid < sma
        )

        price = ex_c[i]  # fill at current price the moment lines cross

        # ── EXIT (symmetric live cross-back or counter-trade TP) ──
        if position is not None:
            exit_price = None
            exit_reason = None
            d = position["direction"]

            # dynamic TP for counter-trades
            if position.get("dynamic_tp_pct") is not None:
                tp = position["dynamic_tp_pct"]
                if d == "LONG":
                    tp_price = position["entry_price"] * (1 + tp / 100)
                    if ex_h[i] >= tp_price:
                        exit_price, exit_reason = tp_price, "take_profit_dynamic"
                else:
                    tp_price = position["entry_price"] * (1 - tp / 100)
                    if ex_l[i] <= tp_price:
                        exit_price, exit_reason = tp_price, "take_profit_dynamic"

            # live signal cross-back
            if exit_price is None:
                if d == "LONG" and cross_below:
                    exit_price, exit_reason = price, "signal"
                elif d == "SHORT" and cross_above:
                    exit_price, exit_reason = price, "signal"

            # force close on last bar
            if exit_price is None and i == len(df_ex) - 1:
                exit_price, exit_reason = price, "force_close"

            if exit_price is not None:
                if d == "LONG":
                    gross = (exit_price - position["entry_price"]) * position["shares"]
                    pnl_pct = (exit_price - position["entry_price"]) / position["entry_price"] * 100
                else:
                    gross = (position["entry_price"] - exit_price) * position["shares"]
                    pnl_pct = (position["entry_price"] - exit_price) / position["entry_price"] * 100
                notional = position["entry_price"] * position["shares"]
                commission = (COMMISSION_PCT / 100) * (notional + exit_price * position["shares"])
                net = gross - commission
                capital += position["margin"] + net
                trades.append({
                    "direction": d,
                    "entry_date": position["entry_date"],
                    "entry_price": position["entry_price"],
                    "exit_date": now,
                    "exit_price": exit_price,
                    "pnl": net,
                    "pnl_pct": pnl_pct,
                    "exit_reason": exit_reason,
                })
                # counter-trade on losing signal exit
                counter_trade_pending = None
                if ENABLE_COUNTER_TRADES and net < 0 and exit_reason == "signal":
                    counter_trade_pending = {
                        "direction": "SHORT" if d == "LONG" else "LONG",
                        "tp_pct": abs(pnl_pct) * COUNTER_TP_MULTIPLIER,
                    }
                position = None

        # ── ENTRY ──
        if position is None and i < len(df_ex) - 1:
            entry_dir = None
            dyn_tp = None

            # counter-trade priority
            if counter_trade_pending is not None:
                entry_dir = counter_trade_pending["direction"]
                dyn_tp = counter_trade_pending["tp_pct"]
                counter_trade_pending = None
            elif cross_above and last_entry_hour != hour:
                entry_dir = "LONG"
            elif cross_below and last_entry_hour != hour:
                entry_dir = "SHORT"

            if entry_dir is not None:
                pos_value = capital * (POSITION_SIZE_VALUE / 100)
                shares = (pos_value * LEVERAGE) / price
                position = {
                    "direction": entry_dir,
                    "entry_price": price,
                    "entry_date": now,
                    "shares": shares,
                    "margin": pos_value,
                    "dynamic_tp_pct": dyn_tp,
                }
                capital -= pos_value
                last_entry_hour = hour  # idempotency: one entry per hour/cross

    # ──────────────────────────────────────────────────────────────────────────
    # 3. RESULTS
    # ──────────────────────────────────────────────────────────────────────────
    print(f"   ✓ Steps: {len(df_ex)}   Lookahead violations: {lookahead_violations}")
    print()

    if not trades:
        print("⚠️  No trades.")
        return

    wins = [t for t in trades if t["pnl"] > 0]
    directions = {}
    reasons = {}
    for t in trades:
        directions[t["direction"]] = directions.get(t["direction"], 0) + 1
        reasons[t["exit_reason"]] = reasons.get(t["exit_reason"], 0) + 1

    print("📊 RESULTS")
    print("─" * 80)
    print(f"Total trades:   {len(trades)}")
    print(f"Win rate:       {100*len(wins)/len(trades):.1f}%")
    print(f"Final capital:  ${capital:,.2f}")
    print(f"Total return:   {(capital-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:.1f}%")
    print(f"Directions:     {directions}")
    print(f"Exit reasons:   {reasons}")
    print()

    # ── Full trade log ──
    # Times stored as naive-UTC; also show DISPLAY_TZ so they match your chart.
    tz_delta = pd.Timedelta(hours=DISPLAY_TZ_OFFSET_HOURS)

    def fmt_utc(ts):
        return str(ts)[:16]

    def fmt_disp(ts):
        return str(pd.Timestamp(ts) + tz_delta)[:16]

    print("📋 TRADE LOG   (times shown as UTC | " + DISPLAY_TZ_LABEL + ")")
    print("─" * 132)
    print(
        f"{'#':>3}  {'DIR':<5}  {'ENTRY (UTC)':<16} {'ENTRY (' + DISPLAY_TZ_LABEL + ')':<16}  {'PRICE':>10}  "
        f"{'EXIT (UTC)':<16} {'EXIT (' + DISPLAY_TZ_LABEL + ')':<16}  {'PRICE':>10}  {'PnL$':>9}  {'PnL%':>7}  {'REASON':<20}"
    )
    print("─" * 132)
    running = INITIAL_CAPITAL
    for n, t in enumerate(trades, 1):
        running += t["pnl"]
        mark = "📈" if t["pnl"] > 0 else "📉"
        print(
            f"{n:>3}  {t['direction']:<5}  {fmt_utc(t['entry_date']):<16} {fmt_disp(t['entry_date']):<16}  {t['entry_price']:>10.2f}  "
            f"{fmt_utc(t['exit_date']):<16} {fmt_disp(t['exit_date']):<16}  {t['exit_price']:>10.2f}  {t['pnl']:>9.2f}  {t['pnl_pct']:>6.2f}%  "
            f"{t['exit_reason']:<20} {mark} eq=${running:,.2f}"
        )
    print("─" * 132)
    print()

    if lookahead_violations == 0:
        print("✅ No lookahead: forming bar at each step used only bars <= now.")
    else:
        print(f"❌ {lookahead_violations} lookahead violations — investigate!")


if __name__ == "__main__":
    main()
