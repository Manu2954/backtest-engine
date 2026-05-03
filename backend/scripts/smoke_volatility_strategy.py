"""
Smoke Test for Volatility Segmentation Strategy

Tests the volatility-based regime detection:
- Signal: [log_returns, rolling_vol]
- Regimes: HIGH_VOL, LOW_VOL, TRANSITION
- Good for: Detecting volatility regime shifts

Run: python scripts/smoke_volatility_strategy.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv  # noqa: E402
from app.engine.robustness.regime_detection import (  # noqa: E402
    detect_regimes,
    detect_changepoints,
    extract_segment_features,
    analyze_trades_by_regime,
    calculate_regime_distribution,
    assess_regime_dependency,
    build_regime_report,
)
from app.engine.robustness.segmentation import SegmentationFactory  # noqa: E402


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main() -> None:
    print_section("VOLATILITY STRATEGY - SMOKE TEST")

    # Configuration
    ticker = "BTCUSDT"
    start = "2020-01-01"
    end = "2024-01-01"

    print(f"\nConfiguration:")
    print(f"  Ticker: {ticker}")
    print(f"  Period: {start} to {end}")
    print(f"  Strategy: volatility")

    # Step 1: Fetch data
    print_section("STEP 1: Fetch OHLCV Data")
    df = fetch_ohlcv(ticker, start, end, "1d", "CRYPTO")
    print(f"✅ Fetched {len(df)} bars")
    print(f"   Date range: {df.index[0].date()} to {df.index[-1].date()}")

    # Step 2: Get strategy info
    print_section("STEP 2: Strategy Info")
    strategy = SegmentationFactory.create_strategy("volatility")
    print(f"   Strategy name: {strategy.get_strategy_name()}")
    print(f"   Regime types: {strategy.get_regime_types()}")

    # Step 3: Detect changepoints
    print_section("STEP 3: Detect Changepoints")
    changepoints = detect_changepoints(
        df,
        strategy="volatility",
        penalty=None,
        min_segment_length=20,
        vol_window=20,
    )
    print(f"✅ Found {len(changepoints) - 1} segments")

    # Step 4: Extract features
    print_section("STEP 4: Segment Features")
    features = extract_segment_features(df, changepoints, strategy="volatility")

    print(f"\n   First 10 segments:")
    for i, feat in enumerate(features[:10]):
        start_idx = changepoints[i]
        end_idx = changepoints[i + 1] - 1
        start_date = df.index[start_idx].date()
        end_date = df.index[end_idx].date()
        bars = end_idx - start_idx + 1
        print(f"   {i + 1}. {start_date} to {end_date} ({bars} bars)")
        print(f"      mean_vol={feat['mean_vol']:.6f}, std_vol={feat['std_vol']:.6f}")
        print(f"      mean_return={feat['mean_return']:.4f}%, max_dd={feat['max_drawdown']:.2f}%")

    # Step 5: Full regime detection
    print_section("STEP 5: Labeled Regimes")
    segments, regime_labels = detect_regimes(
        df,
        strategy="volatility",
        min_segment_length=20,
        vol_window=20,
    )

    print(f"✅ {len(segments)} labeled segments")

    # Count by regime
    regime_counts = {}
    for seg in segments:
        regime_counts[seg.regime] = regime_counts.get(seg.regime, 0) + 1

    print(f"\n   Segment counts by regime:")
    for regime, count in sorted(regime_counts.items()):
        print(f"      {regime}: {count}")

    # Step 6: Distribution
    print_section("STEP 6: Time Distribution")
    distribution = calculate_regime_distribution(regime_labels)
    for regime, pct in sorted(distribution.items()):
        print(f"   {regime}: {pct:.1f}%")

    # Step 7: Sample segments
    print_section("STEP 7: Sample Segments by Regime")

    for regime_type in strategy.get_regime_types():
        regime_segs = [s for s in segments if s.regime == regime_type]
        if regime_segs:
            seg = regime_segs[0]
            print(f"\n   {regime_type} example:")
            print(f"      {seg.start_date.date()} to {seg.end_date.date()} ({seg.bar_count} bars)")
            print(f"      strength={seg.strength}")
            feat_str = ", ".join(f"{k}={v:.4f}" for k, v in seg.features.items() if isinstance(v, float))
            print(f"      features: {feat_str}")

    # Validation
    print_section("VALIDATION")

    valid_regimes = strategy.get_regime_types()

    assert len(segments) > 0, "Should have segments"
    assert len(regime_labels) == len(df), "Labels should match data length"
    assert all(s.regime in valid_regimes for s in segments), "All regimes should be valid"
    assert all(r in valid_regimes for r in regime_labels.unique()), "All labels should be valid"

    print("✅ All validations passed")

    print_section("VOLATILITY STRATEGY: OPERATIONAL ✅")
    print(f"   {len(segments)} segments detected")
    print(f"   Regimes: {list(regime_counts.keys())}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ SMOKE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
