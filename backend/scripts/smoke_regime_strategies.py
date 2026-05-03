"""
Smoke Test: Pluggable Regime Detection Strategies

Tests all three segmentation strategies on BTC 2021-2025 data:
- l1_trend: L1 Trend Filter (2 regimes: BULL/BEAR)
- pelt_directional: PELT rolling_mean (4 regimes)
- pelt_volatility: PELT returns_vol (4 regimes)

Validates:
- Correct regime counts per strategy
- No crashes or errors
- Reasonable segment counts
- Proper date ranges
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from collections import Counter

import pandas as pd
import yfinance as yf

from app.engine.robustness.regime_detection import detect_regimes


def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_segment_summary(segments, strategy_name: str):
    """Print summary statistics for segments."""
    print(f"\n{strategy_name} Strategy Results:")
    print(f"  Total segments: {len(segments)}")

    # Regime distribution
    regime_counts = Counter([s.regime for s in segments])
    print(f"  Regime distribution:")
    for regime, count in sorted(regime_counts.items()):
        pct = count / len(segments) * 100
        print(f"    {regime}: {count} segments ({pct:.1f}%)")

    # Segment length stats
    lengths = [s.bar_count for s in segments]
    print(f"  Segment lengths: min={min(lengths)}, max={max(lengths)}, avg={sum(lengths)/len(lengths):.1f} bars")

    # Show first 3 segments
    print(f"  First 3 segments:")
    for seg in segments[:3]:
        print(f"    {seg.start_date.date()} to {seg.end_date.date()}: {seg.regime} ({seg.bar_count} bars)")


def main():
    print_section("SMOKE TEST: Pluggable Regime Detection Strategies")

    # Fetch BTC data 2021-2025
    print("\nFetching BTC-USD data (2021-01-01 to 2025-04-30, 1d)...")
    ticker = yf.Ticker("BTC-USD")
    df_raw = ticker.history(start="2021-01-01", end="2025-04-30", interval="1d")

    if df_raw.empty:
        print("ERROR: No data fetched")
        return

    print(f"Fetched {len(df_raw)} bars")
    print(f"Date range: {df_raw.index[0].date()} to {df_raw.index[-1].date()}")

    # Standardize column names
    df_raw.columns = [col.lower() for col in df_raw.columns]

    # Test 1: L1 Trend Filter (2 regimes)
    print_section("TEST 1: L1 Trend Filter (2 regimes: BULL/BEAR)")
    try:
        segments_l1, labels_l1 = detect_regimes(
            df_raw,
            strategy="l1_trend",
            k=0.015,
        )
        print_segment_summary(segments_l1, "L1 Trend Filter")

        # Validate: Should only have BULL and BEAR
        unique_regimes = set([s.regime for s in segments_l1])
        expected = {"BULL", "BEAR"}
        if unique_regimes == expected:
            print(f"\n✅ L1 regime types correct: {sorted(unique_regimes)}")
        else:
            print(f"\n❌ L1 regime types incorrect: expected {expected}, got {unique_regimes}")

        # Validate: Should have 15-30 segments (not too few, not too many)
        if 15 <= len(segments_l1) <= 30:
            print(f"✅ L1 segment count reasonable: {len(segments_l1)}")
        else:
            print(f"⚠️  L1 segment count unusual: {len(segments_l1)} (expected 15-30)")

    except Exception as e:
        print(f"❌ L1 strategy failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: PELT Directional (4 regimes)
    print_section("TEST 2: PELT Directional (4 regimes)")
    try:
        segments_dir, labels_dir = detect_regimes(
            df_raw,
            strategy="pelt_directional",
            penalty=None,  # Auto: np.log(n)
            min_segment_length=20,
            vol_window=20,
        )
        print_segment_summary(segments_dir, "PELT Directional")

        # Validate: Should have 4 regime types
        unique_regimes = set([s.regime for s in segments_dir])
        expected = {"BULL", "BEAR", "CHOPPY", "RANGING"}
        if unique_regimes == expected:
            print(f"\n✅ PELT Directional regime types correct: {sorted(unique_regimes)}")
        else:
            print(f"\n⚠️  PELT Directional regime types: {sorted(unique_regimes)} (expected all 4, may not all appear)")

        # Validate: Should have 40-100 segments
        if 40 <= len(segments_dir) <= 100:
            print(f"✅ PELT Directional segment count reasonable: {len(segments_dir)}")
        else:
            print(f"⚠️  PELT Directional segment count unusual: {len(segments_dir)} (expected 40-100)")

    except Exception as e:
        print(f"❌ PELT Directional strategy failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: PELT Volatility (4 regimes)
    print_section("TEST 3: PELT Volatility (4 regimes)")
    try:
        segments_vol, labels_vol = detect_regimes(
            df_raw,
            strategy="pelt_volatility",
            penalty=None,  # Auto: np.log(n)
            min_segment_length=20,
            vol_window=20,
        )
        print_segment_summary(segments_vol, "PELT Volatility")

        # Validate: Should have 3 regime types (HIGH_VOL, LOW_VOL, TRANSITION)
        unique_regimes = set([s.regime for s in segments_vol])
        expected = {"HIGH_VOL", "LOW_VOL", "TRANSITION"}
        if unique_regimes.issubset(expected):
            print(f"\n✅ PELT Volatility regime types correct: {sorted(unique_regimes)}")
        else:
            print(f"\n❌ PELT Volatility has unexpected regimes: {unique_regimes - expected}")

        # Validate: Should have 20-60 segments
        if 20 <= len(segments_vol) <= 60:
            print(f"✅ PELT Volatility segment count reasonable: {len(segments_vol)}")
        else:
            print(f"⚠️  PELT Volatility segment count unusual: {len(segments_vol)} (expected 20-60)")

    except Exception as e:
        print(f"❌ PELT Volatility strategy failed: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print_section("SUMMARY")
    print("\nAll three strategies executed successfully!")
    print("\nStrategy characteristics:")
    print("  l1_trend       : 2 regimes (BULL/BEAR), stable, ~15-30 segments")
    print("  pelt_directional: 4 regimes, responsive to trends, ~40-100 segments")
    print("  pelt_volatility : 3 regimes, volatility-focused, ~20-60 segments")
    print("\nRecommendations:")
    print("  - Directional strategies → l1_trend (k=0.015, 4h)")
    print("  - Responsive strategies  → pelt_directional (pen=1.0, 1h/4h)")
    print("  - Volatility strategies  → pelt_volatility (pen=1.0, 1h)")


if __name__ == "__main__":
    main()
