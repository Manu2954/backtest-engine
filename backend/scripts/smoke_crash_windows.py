"""
Crash Window Detection — Find 1-Hour Price Drops

Identifies all time windows where price dropped >= THRESHOLD% within 1 hour.
Deduplicates by clustering events within CLUSTER_HOURS of each other.

Usage:
  python scripts/smoke_crash_windows.py

Configuration:
  Edit TICKER, START, END, TF, THRESHOLD_PCT, CLUSTER_HOURS below.
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
START = "2026-01-01"
END = "2026-05-05"
TF = "5m"
ASSET_CLASS = "CRYPTO"

THRESHOLD_PCT = -1.5      # Drop threshold (negative = down)
LOOKBACK_BARS = 12        # 12 bars of 5m = 1 hour
CLUSTER_HOURS = 2         # Deduplicate events within this window
SHOW_TOP_N = 5000         # Max events to display


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║           CRASH WINDOW DETECTION                                    ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    # Calculate lookback duration label
    tf_minutes = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
    bar_minutes = tf_minutes.get(TF, 5)
    window_minutes = LOOKBACK_BARS * bar_minutes
    if window_minutes >= 60:
        window_label = f"{window_minutes // 60}h"
    else:
        window_label = f"{window_minutes}m"

    print(f"  Ticker: {TICKER}  |  Timeframe: {TF}  |  Period: {START} to {END}")
    print(f"  Drop threshold: {THRESHOLD_PCT}%  |  Window: {window_label} ({LOOKBACK_BARS} bars)")
    print(f"  Cluster dedup: {CLUSTER_HOURS}h")

    # Fetch data
    print(f"\n{'─' * 70}")
    print("  FETCHING DATA")
    print(f"{'─' * 70}")

    df = fetch_ohlcv(TICKER, START, END, TF, ASSET_CLASS)
    print(f"  Bars: {len(df):,}  |  Range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")

    # Calculate rolling return over lookback window
    df["pct_change"] = (df["close"] - df["close"].shift(LOOKBACK_BARS)) / df["close"].shift(LOOKBACK_BARS) * 100

    # Filter by threshold
    drops = df[df["pct_change"] <= THRESHOLD_PCT].copy()
    total_raw = len(drops)

    # Deduplicate: keep only the worst drop per cluster window
    cluster_bars = int(CLUSTER_HOURS * 60 / bar_minutes)
    events = []
    used_indices = set()

    for idx, row in drops.sort_values("pct_change").iterrows():
        loc = df.index.get_loc(idx)
        skip = False
        for prev_loc in used_indices:
            if abs(loc - prev_loc) < cluster_bars:
                skip = True
                break
        if skip:
            continue
        used_indices.add(loc)
        events.append((idx, row, loc))

    # Sort by time
    events.sort(key=lambda x: x[0])

    # Print results
    print(f"\n{'─' * 70}")
    print("  CRASH EVENTS")
    print(f"{'─' * 70}")
    print(f"  Raw instances (>= {THRESHOLD_PCT}%): {total_raw:,}")
    print(f"  Unique events (clustered): {len(events)}")
    print(f"  Avg frequency: 1 event every {len(df) / max(len(events), 1) * bar_minutes / 60 / 24:.1f} days")

    print(f"\n  {'#':<4} {'Timestamp':<20} {'Price':>10} {'Drop':>8} {'Before':>10} {'Recovery 1h':>12}")
    print(f"  {'─' * 68}")

    for i, (idx, row, loc) in enumerate(events[:SHOW_TOP_N], 1):
        price_before = df["close"].iloc[loc - LOOKBACK_BARS]
        ts = idx.strftime("%Y-%m-%d %H:%M")

        # Check recovery: price 1h (12 bars) after the drop
        recovery_loc = min(loc + LOOKBACK_BARS, len(df) - 1)
        price_after = df["close"].iloc[recovery_loc]
        recovery_pct = (price_after - row["close"]) / row["close"] * 100

        print(f"  {i:<4} {ts:<20} ${row['close']:>9,.0f} {row['pct_change']:>+7.2f}% ${price_before:>9,.0f} {recovery_pct:>+10.2f}%")

    # Summary stats
    print(f"\n{'─' * 70}")
    print("  STATISTICS")
    print(f"{'─' * 70}")

    drop_magnitudes = [row["pct_change"] for _, row, _ in events]
    recoveries = []
    for idx, row, loc in events:
        recovery_loc = min(loc + LOOKBACK_BARS, len(df) - 1)
        price_after = df["close"].iloc[recovery_loc]
        recoveries.append((price_after - row["close"]) / row["close"] * 100)

    if events:
        import statistics
        print(f"  Avg drop magnitude:    {statistics.mean(drop_magnitudes):+.2f}%")
        print(f"  Worst drop:            {min(drop_magnitudes):+.2f}%")
        print(f"  Median drop:           {statistics.median(drop_magnitudes):+.2f}%")
        print()
        print(f"  Avg 1h recovery:       {statistics.mean(recoveries):+.2f}%")
        print(f"  Best recovery:         {max(recoveries):+.2f}%")
        print(f"  Worst (continued down):{min(recoveries):+.2f}%")
        print(f"  Bounce rate (>0%):     {sum(1 for r in recoveries if r > 0) / len(recoveries) * 100:.1f}%")

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
