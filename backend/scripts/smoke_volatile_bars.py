"""
Volatile Bar Detection — Find 1-Hour Bars with Large High-Low Range

Identifies all 1h bars where (high - low) / low >= THRESHOLD%.
These represent periods of extreme intra-bar volatility.

Usage:
  python scripts/smoke_volatile_bars.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TICKER = "BTCUSDT"
START = "2025-01-01"
END = "2026-05-05"
TF = "1h"
ASSET_CLASS = "CRYPTO"

THRESHOLD_PCT = 2.0       # Minimum high-low range as % of low
DIRECTION_FILTER = "DOWN" # "UP" = bullish only, "DOWN" = bearish only, None = all
SHOW_TOP_N = 5000         # Max events to display


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║           VOLATILE BAR DETECTION (High-Low Range)                   ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"  Ticker: {TICKER}  |  Timeframe: {TF}  |  Period: {START} to {END}")
    print(f"  Range threshold: >= {THRESHOLD_PCT}%  (high - low) / low")
    if DIRECTION_FILTER:
        print(f"  Direction filter: {DIRECTION_FILTER} only")

    # Fetch data
    print(f"\n{'─' * 70}")
    print("  FETCHING DATA")
    print(f"{'─' * 70}")

    df = fetch_ohlcv(TICKER, START, END, TF, ASSET_CLASS)
    print(f"  Bars: {len(df):,}  |  Range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")

    # Calculate high-low range as percentage
    df["hl_range_pct"] = (df["high"] - df["low"]) / df["low"] * 100

    # Filter by threshold
    volatile = df[df["hl_range_pct"] >= THRESHOLD_PCT].copy()

    # Filter by direction
    if DIRECTION_FILTER == "DOWN":
        volatile = volatile[volatile["close"] < volatile["open"]]
    elif DIRECTION_FILTER == "UP":
        volatile = volatile[volatile["close"] > volatile["open"]]

    volatile = volatile.sort_index()

    # Print results
    print(f"\n{'─' * 70}")
    print("  VOLATILE BARS")
    print(f"{'─' * 70}")
    print(f"  Total bars: {len(df):,}")
    print(f"  Volatile bars (>= {THRESHOLD_PCT}%): {len(volatile):,}")
    print(f"  Frequency: {len(volatile) / len(df) * 100:.1f}% of all bars")
    print(f"  Avg occurrence: 1 every {len(df) / max(len(volatile), 1):.1f} bars ({len(df) / max(len(volatile), 1) / 24:.1f} days)")

    # Direction analysis
    volatile["direction"] = "FLAT"
    volatile.loc[volatile["close"] > volatile["open"], "direction"] = "UP"
    volatile.loc[volatile["close"] < volatile["open"], "direction"] = "DOWN"

    up_count = (volatile["direction"] == "UP").sum()
    down_count = (volatile["direction"] == "DOWN").sum()
    flat_count = (volatile["direction"] == "FLAT").sum()

    print(f"\n  Direction breakdown:")
    print(f"    Bullish (close > open): {up_count} ({up_count / max(len(volatile), 1) * 100:.1f}%)")
    print(f"    Bearish (close < open): {down_count} ({down_count / max(len(volatile), 1) * 100:.1f}%)")
    if flat_count:
        print(f"    Flat:                   {flat_count}")

    print(f"\n  {'#':<4} {'Timestamp':<20} {'Low':>10} {'High':>10} {'Range%':>8} {'Close':>10} {'Dir':<5}")
    print(f"  {'─' * 72}")

    for i, (idx, row) in enumerate(volatile.iloc[:SHOW_TOP_N].iterrows(), 1):
        ts = idx.strftime("%Y-%m-%d %H:%M")
        direction = "▲" if row["close"] > row["open"] else "▼" if row["close"] < row["open"] else "─"
        print(f"  {i:<4} {ts:<20} ${row['low']:>9,.0f} ${row['high']:>9,.0f} "
              f"{row['hl_range_pct']:>+7.2f}% ${row['close']:>9,.0f} {direction}")

    # Summary stats
    print(f"\n{'─' * 70}")
    print("  STATISTICS")
    print(f"{'─' * 70}")

    if len(volatile) > 0:
        import statistics
        ranges = volatile["hl_range_pct"].tolist()
        print(f"  Avg range:     {statistics.mean(ranges):.2f}%")
        print(f"  Median range:  {statistics.median(ranges):.2f}%")
        print(f"  Max range:     {max(ranges):.2f}%")
        print(f"  Min range:     {min(ranges):.2f}% (above threshold)")

        # Next-bar behavior (what happens after a volatile bar?)
        print(f"\n  Next-bar behavior (1h after volatile bar):")
        next_returns = []
        for idx in volatile.index:
            loc = df.index.get_loc(idx)
            if loc + 1 < len(df):
                current_close = df.iloc[loc]["close"]
                next_bar = df.iloc[loc + 1]
                ret = (next_bar["close"] - current_close) / current_close * 100
                next_returns.append(ret)

        if next_returns:
            print(f"    Avg next-bar return:  {statistics.mean(next_returns):+.3f}%")
            print(f"    Positive next bar:    {sum(1 for r in next_returns if r > 0) / len(next_returns) * 100:.1f}%")
            print(f"    Avg |move| next bar:  {statistics.mean(abs(r) for r in next_returns):.3f}%")

    print(f"\n{'═' * 70}")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n  FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
