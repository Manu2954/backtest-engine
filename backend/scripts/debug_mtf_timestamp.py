"""
Diagnostic script to debug the 1h to 4h timestamp mapping in MTF strategy.

Focus:
1. How ts_1h_to_4h mapping is built
2. Whether 4h crossover signals are detected at the right time relative to 1h bars
3. Check for off-by-one issues

Uses actual ETHUSDT data from 2023-01-01 to 2024-01-01.
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


TICKER = "ETHUSDT"
START = "2023-01-01"
END = "2024-01-01"
ASSET_CLASS = "CRYPTO"


def compute_ha_and_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Heikin Ashi candles and indicators (Donchian, SMA50)."""
    df = compute_indicators(df, [{"indicator_type": "HEIKINASHI", "alias": "ha", "params": {}}])
    df["open"] = df["ha_open"]
    df["high"] = df["ha_high"]
    df["low"] = df["ha_low"]
    df["close"] = df["ha_close"]
    df = compute_indicators(df, [
        {"indicator_type": "DONCHIAN", "alias": "dc_20", "params": {"period": 20}},
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    ])
    return df


def detect_crossovers(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Detect DC mid crossing above/below SMA50."""
    dc_above_sma = df["dc_20_mid"] > df["sma_50"]
    dc_below_sma = df["dc_20_mid"] < df["sma_50"]
    cross_above = dc_above_sma & dc_below_sma.shift(1).fillna(True)
    cross_below = dc_below_sma & dc_above_sma.shift(1).fillna(True)
    return cross_above, cross_below


def main():
    print("=" * 80)
    print("DEBUG: 1h to 4h Timestamp Mapping Analysis")
    print("=" * 80)
    print()

    # Fetch data
    print("Fetching data...")
    df_1h_raw = fetch_ohlcv(TICKER, START, END, "1h", ASSET_CLASS)
    df_4h_raw = fetch_ohlcv(TICKER, START, END, "4h", ASSET_CLASS)
    print(f"1h bars: {len(df_1h_raw)}")
    print(f"4h bars: {len(df_4h_raw)}")
    print()

    # Show raw timestamp samples
    print("=" * 80)
    print("1. RAW TIMESTAMPS (first 10 bars)")
    print("=" * 80)
    print()
    print("1h timestamps:")
    for i, ts in enumerate(df_1h_raw.index[:10]):
        print(f"  [{i}] {ts}")
    print()
    print("4h timestamps:")
    for i, ts in enumerate(df_4h_raw.index[:10]):
        print(f"  [{i}] {ts}")
    print()

    # Compute indicators
    print("Computing HA + indicators...")
    df_4h = compute_ha_and_indicators(df_4h_raw.copy())
    df_4h, _ = trim_warmup_period(df_4h)
    df_1h = compute_ha_and_indicators(df_1h_raw.copy())
    df_1h, _ = trim_warmup_period(df_1h)
    print(f"After warmup: 1h={len(df_1h)}, 4h={len(df_4h)}")
    print()

    # Detect crossovers
    cross_above_4h, cross_below_4h = detect_crossovers(df_4h)
    cross_above_1h, cross_below_1h = detect_crossovers(df_1h)

    print("=" * 80)
    print("2. TIMESTAMP MAPPING ANALYSIS")
    print("=" * 80)
    print()

    # Build the mapping (same logic as original script)
    df_4h_sorted = df_4h.sort_index()
    ts_1h_to_4h = {}
    for ts_1h in df_1h.index:
        valid_4h = df_4h_sorted.index[df_4h_sorted.index <= ts_1h]
        if len(valid_4h) > 0:
            ts_1h_to_4h[ts_1h] = valid_4h[-1]

    # Show mapping for first few 4h bars
    print("First 3 4h bars and which 1h bars map to them:")
    print()
    first_4h_bars = df_4h_sorted.index[:3]
    for i, ts_4h in enumerate(first_4h_bars):
        print(f"4h bar [{i}]: {ts_4h}")
        mapped_1h = [ts_1h for ts_1h, mapped_ts in ts_1h_to_4h.items() if mapped_ts == ts_4h]
        mapped_1h.sort()
        print(f"  1h bars that map to this 4h bar:")
        for ts_1h in mapped_1h:
            print(f"    {ts_1h}")
        print()

    print("=" * 80)
    print("3. FIRST 4h CROSS ABOVE EVENT")
    print("=" * 80)
    print()

    # Find first 4h cross above
    first_cross_above_4h_idx = cross_above_4h.index[cross_above_4h][0]
    first_cross_idx = list(df_4h.index).index(first_cross_above_4h_idx)
    print(f"First 4h CROSS ABOVE at: {first_cross_above_4h_idx}")
    print(f"  Index position: {first_cross_idx}")
    print()

    # Show the 4h context around the cross
    print("4h bars around the cross (DC_mid vs SMA50):")
    start_idx = max(0, first_cross_idx - 2)
    end_idx = min(len(df_4h), first_cross_idx + 3)
    for i in range(start_idx, end_idx):
        ts = df_4h.index[i]
        dc_mid = df_4h.iloc[i]["dc_20_mid"]
        sma50 = df_4h.iloc[i]["sma_50"]
        is_cross = cross_above_4h.iloc[i]
        marker = " <<< CROSS" if is_cross else ""
        print(f"  [{i}] {ts} | DC_mid={dc_mid:.2f} | SMA50={sma50:.2f} | diff={dc_mid-sma50:+.2f}{marker}")
    print()

    # Find 1h bars that map to this 4h bar
    print("1h bars that map to this 4h bar:")
    mapped_1h = sorted([ts_1h for ts_1h, ts_4h in ts_1h_to_4h.items() if ts_4h == first_cross_above_4h_idx])
    for ts_1h in mapped_1h:
        dc_mid = df_1h.loc[ts_1h, "dc_20_mid"]
        sma50 = df_1h.loc[ts_1h, "sma_50"]
        is_1h_cross = cross_above_1h.loc[ts_1h]
        marker = " <<< 1h CROSS ABOVE" if is_1h_cross else ""
        print(f"  {ts_1h} | DC_mid={dc_mid:.2f} | SMA50={sma50:.2f} | diff={dc_mid-sma50:+.2f}{marker}")
    print()

    print("=" * 80)
    print("4. TIMELINE ANALYSIS: When does signal flow happen?")
    print("=" * 80)
    print()

    # Find the next 1h cross above after the 4h cross
    # This simulates what should trigger an entry
    print("Looking for 1h cross ABOVE after 4h cross...")
    found_1h_cross = None
    for ts_1h in df_1h.index:
        if ts_1h > first_cross_above_4h_idx and cross_above_1h.loc[ts_1h]:
            found_1h_cross = ts_1h
            break

    if found_1h_cross:
        print(f"First 1h cross above after 4h signal: {found_1h_cross}")
        print()

        # Show context
        idx = list(df_1h.index).index(found_1h_cross)
        start_idx = max(0, idx - 3)
        end_idx = min(len(df_1h), idx + 3)
        print("1h context around confirmation cross:")
        for i in range(start_idx, end_idx):
            ts = df_1h.index[i]
            ts_4h = ts_1h_to_4h.get(ts, "N/A")
            dc_mid = df_1h.iloc[i]["dc_20_mid"]
            sma50 = df_1h.iloc[i]["sma_50"]
            is_cross = cross_above_1h.iloc[i]
            marker = " <<< 1h CONFIRM" if is_cross else ""
            print(f"  [{i}] {ts} -> 4h:{ts_4h} | DC={dc_mid:.2f} | SMA50={sma50:.2f}{marker}")
    print()

    print("=" * 80)
    print("5. DETAILED: Signal Flow Simulation for First Entry")
    print("=" * 80)
    print()

    # Simulate the original logic but with verbose output
    armed_long = False
    last_4h_ts = None

    print("Walking through 1h bars, showing state changes...")
    print()

    # Start a bit before the 4h cross
    start_ts = first_cross_above_4h_idx - pd.Timedelta(hours=8)
    df_1h_subset = df_1h[df_1h.index >= start_ts].head(20)

    for i, ts in enumerate(df_1h_subset.index):
        ts_4h = ts_1h_to_4h.get(ts)

        events = []

        # Check 4h crossovers (only on new 4h bar)
        if ts_4h is not None and ts_4h != last_4h_ts:
            events.append(f"NEW 4h bar: {ts_4h}")
            if ts_4h in cross_above_4h.index and cross_above_4h.loc[ts_4h]:
                events.append("  -> 4h CROSS ABOVE detected, ARMING LONG")
                armed_long = True
            last_4h_ts = ts_4h

        # Check 1h confirmation
        is_1h_cross_above = cross_above_1h.loc[ts]
        is_1h_cross_below = cross_below_1h.loc[ts]

        if armed_long and is_1h_cross_above:
            events.append("  -> 1h CROSS ABOVE while armed -> ENTRY SIGNAL!")

        if is_1h_cross_above:
            events.append("  (1h cross above)")
        if is_1h_cross_below:
            events.append("  (1h cross below)")

        # Print this bar
        dc_mid = df_1h.loc[ts, "dc_20_mid"]
        sma50 = df_1h.loc[ts, "sma_50"]
        print(f"1h bar: {ts}")
        print(f"  maps to 4h: {ts_4h}")
        print(f"  DC={dc_mid:.2f} SMA50={sma50:.2f} diff={dc_mid-sma50:+.2f}")
        print(f"  armed_long={armed_long}")
        if events:
            for e in events:
                print(f"  EVENT: {e}")
        print()

        # Stop after entry signal
        if armed_long and is_1h_cross_above:
            print(">>> ENTRY WOULD FIRE HERE <<<")
            break

    print()
    print("=" * 80)
    print("6. POTENTIAL ISSUE: Timestamp Alignment")
    print("=" * 80)
    print()

    # The key question: When a 4h bar starts at T, does it include data up to T+4h or from T-4h to T?
    # Binance convention: bar at T contains data from T to T+4h (T is bar open time)
    # So a 4h bar at 00:00 contains 00:00, 01:00, 02:00, 03:00 1h bars

    # Check if the mapping is correct
    sample_4h = df_4h.index[5]  # Pick a sample 4h bar
    print(f"Sample 4h bar timestamp: {sample_4h}")
    print()
    print("Expected 1h bars that should map to this 4h bar:")
    print("  If 4h bar at T represents [T, T+4h):")
    for i in range(4):
        expected = sample_4h + pd.Timedelta(hours=i)
        print(f"    {expected}")
    print()
    print("Actual 1h bars mapping to this 4h bar:")
    mapped = sorted([ts for ts, ts_4h in ts_1h_to_4h.items() if ts_4h == sample_4h])
    for ts in mapped:
        print(f"    {ts}")
    print()

    # Check if there's an offset issue
    print("=" * 80)
    print("7. IST OFFSET CHECK")
    print("=" * 80)
    print()

    # Get the raw timestamps to see the actual offset
    print("First 4h bar raw timestamp:", df_4h_raw.index[0])
    print("First 1h bar raw timestamp:", df_1h_raw.index[0])
    print()

    # Check if :30 offset exists
    sample_ts = df_1h_raw.index[0]
    print(f"Sample 1h timestamp: {sample_ts}")
    print(f"  Minute: {sample_ts.minute}")
    print(f"  Hour: {sample_ts.hour}")
    print()

    sample_ts_4h = df_4h_raw.index[0]
    print(f"Sample 4h timestamp: {sample_ts_4h}")
    print(f"  Minute: {sample_ts_4h.minute}")
    print(f"  Hour: {sample_ts_4h.hour}")
    print()

    # The issue: If timestamps are at :30, then a 4h bar at 00:30 should map to
    # 1h bars at 00:30, 01:30, 02:30, 03:30 - NOT 04:30
    # But the current mapping uses ts_1h <= ts_4h, so:
    # - 1h 00:30 maps to 4h 00:30 (correct)
    # - 1h 01:30 maps to 4h 00:30 (WRONG - should map to NEXT 4h bar that will close it)

    print("ANALYSIS OF MAPPING LOGIC:")
    print()
    print("Current logic: ts_1h_to_4h[ts_1h] = max(ts_4h where ts_4h <= ts_1h)")
    print()
    print("This means:")
    print("  1h bar at 00:30 -> maps to 4h bar at 00:30")
    print("  1h bar at 01:30 -> maps to 4h bar at 00:30 (since 04:30 > 01:30)")
    print("  1h bar at 02:30 -> maps to 4h bar at 00:30")
    print("  1h bar at 03:30 -> maps to 4h bar at 00:30")
    print("  1h bar at 04:30 -> maps to 4h bar at 04:30")
    print()
    print("THE PROBLEM: When a 4h cross happens at 04:30, we detect it on the 1h bar at 04:30.")
    print("But by then, the 4h bar is already CLOSED. We should detect the cross when")
    print("we first see the 4h bar, which is when processing 1h bar at 04:30.")
    print()
    print("Actually wait - that's correct. The cross is detected on the 4h bar that closes")
    print("at the end of that bar's period. When we're at 1h 04:30, we see that 4h 04:30")
    print("is a new 4h bar, and we check if 4h 00:30 (previous) had a cross.")
    print()
    print("Let me verify the actual mapping by showing timestamp differences...")
    print()

    # Show the actual difference between consecutive 4h bar mappings
    prev_4h = None
    transitions = []
    for ts_1h in df_1h.index[:50]:
        ts_4h = ts_1h_to_4h.get(ts_1h)
        if ts_4h != prev_4h:
            transitions.append((ts_1h, ts_4h, prev_4h))
            prev_4h = ts_4h

    print("1h -> 4h mapping transitions (first 10):")
    for ts_1h, ts_4h, prev_4h in transitions[:10]:
        print(f"  At 1h {ts_1h}: 4h changes from {prev_4h} to {ts_4h}")

    print()
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)


if __name__ == "__main__":
    main()
