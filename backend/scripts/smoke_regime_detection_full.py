"""
Smoke Test for Regime Detection

Tests the regime detection logic end-to-end using engine functions directly:
1. Fetch data
2. Compare segmentation strategies (volatility vs directional)
3. Detect regimes (PELT + SNR-based labeling)
4. Run real backtest with a simple strategy
5. Analyze actual trades by regime
6. Generate report

No API/Celery - tests core logic only.

Run: python scripts/regime_detection_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv  # noqa: E402
from app.engine.indicator_layer import compute_indicators, trim_warmup_period  # noqa: E402
from app.engine.condition_engine import evaluate_conditions  # noqa: E402
from app.engine.state_machine import run_backtest  # noqa: E402
from app.engine.report_generator import generate_report  # noqa: E402
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
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main() -> None:
    print_section("REGIME DETECTION - SMOKE TEST (WITH REAL TRADES)")

    # Configuration
    ticker = "BTCUSDT"
    start = "2026-01-01"
    end = "2026-04-01"
    initial_capital = 100000.0

    print(f"\nConfiguration:")
    print(f"  Ticker: {ticker}")
    print(f"  Period: {start} to {end}")
    print(f"  Initial Capital: ${initial_capital:,.0f}")

    # Step 1: Fetch data
    print_section("STEP 1: Fetch OHLCV Data")
    df_raw = fetch_ohlcv(ticker, start, end, "5m", "CRYPTO")
    print(f"✅ Fetched {len(df_raw)} bars")
    print(f"   Date range: {df_raw.index[0].date()} to {df_raw.index[-1].date()}")

    # Step 2a: Compare segmentation strategies
    print_section("STEP 2a: VOLATILITY STRATEGY (detects vol shifts)")
    vol_strategy = SegmentationFactory.create_strategy("volatility")
    changepoints_vol = detect_changepoints(
        df_raw,
        strategy="volatility",
        penalty=None,
        min_segment_length=20,
        vol_window=20,
    )
    print(f"✅ Volatility strategy found {len(changepoints_vol) - 1} segments")
    print(f"   Regime types: {vol_strategy.get_regime_types()}")

    raw_features_vol = extract_segment_features(df_raw, changepoints_vol, strategy="volatility")
    for i, feat in enumerate(raw_features_vol):
        start_idx = changepoints_vol[i]
        end_idx = changepoints_vol[i + 1] - 1
        start_date = df_raw.index[start_idx].date()
        end_date = df_raw.index[end_idx].date()
        bars = end_idx - start_idx + 1
        print(f"   Segment {i + 1}: {start_date} to {end_date} ({bars} bars)")
        print(f"      mean_vol={feat.get('mean_vol', 0):.4f}, mean_ret={feat.get('mean_return', 0):.4f}")

    print_section("STEP 2b: DIRECTIONAL STRATEGY (detects trend reversals)")
    dir_strategy_inst = SegmentationFactory.create_strategy("directional")
    changepoints_dir = detect_changepoints(
        df_raw,
        strategy="directional",
        penalty=None,
        min_segment_length=20,
        vol_window=20,
    )
    print(f"✅ Directional strategy found {len(changepoints_dir) - 1} segments")
    print(f"   Regime types: {dir_strategy_inst.get_regime_types()}")

    raw_features_dir = extract_segment_features(df_raw, changepoints_dir, strategy="directional")
    for i, feat in enumerate(raw_features_dir):
        start_idx = changepoints_dir[i]
        end_idx = changepoints_dir[i + 1] - 1
        start_date = df_raw.index[start_idx].date()
        end_date = df_raw.index[end_idx].date()
        bars = end_idx - start_idx + 1
        print(f"   Segment {i + 1}: {start_date} to {end_date} ({bars} bars)")
        print(f"      slope={feat['slope']:.4f}, R²={feat['r_squared']:.4f}")

    print_section("STEP 2c: STRATEGY COMPARISON")
    print(f"   Volatility: {len(changepoints_vol) - 1} segments")
    print(f"   Directional: {len(changepoints_dir) - 1} segments")

    # Check if directional splits the problematic 450-bar segment
    vol_max_bars = max(changepoints_vol[i+1] - changepoints_vol[i] for i in range(len(changepoints_vol) - 1))
    dir_max_bars = max(changepoints_dir[i+1] - changepoints_dir[i] for i in range(len(changepoints_dir) - 1))
    print(f"   Largest segment (volatility): {vol_max_bars} bars")
    print(f"   Largest segment (directional): {dir_max_bars} bars")

    # Step 3: Use directional strategy for full regime detection
    print_section("STEP 3: Labeled Regimes (Directional + SNR-Based)")
    segments, regime_labels = detect_regimes(
        df_raw,
        strategy="directional",  # Use directional for better trend detection
        penalty=None,
        min_segment_length=20,
        vol_window=20,
    )

    print(f"✅ Found {len(segments)} regime segments:")
    for i, seg in enumerate(segments):
        strength_str = f", strength={seg.strength:.2f}" if seg.strength is not None else ""
        print(f"   Segment {i + 1}: {seg.start_date.date()} to {seg.end_date.date()} "
              f"({seg.bar_count} bars) → {seg.regime}{strength_str}")
        # Print available features (varies by strategy)
        feat_str = ", ".join(f"{k}={v:.4f}" for k, v in seg.features.items() if isinstance(v, (int, float)))
        print(f"      Features: {feat_str}")

    # Step 4: Calculate regime distribution
    print_section("STEP 4: Regime Distribution")
    distribution = calculate_regime_distribution(regime_labels)
    for regime, pct in distribution.items():
        print(f"   {regime}: {pct:.1f}%")

    # Step 5: Define a simple SMA crossover strategy
    print_section("STEP 5: Define Strategy (SMA 9/31 Crossover)")

    indicators = [
        {"indicator_type": "SMA", "alias": "sma_9", "params": {"period": 9}},
        {"indicator_type": "SMA", "alias": "sma_31", "params": {"period": 31}},
    ]

    entry_group = {
        "logic": "AND",
        "conditions": [
            {
                "id": "1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_9",
                "operator": "CROSSES_ABOVE",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_31",
            }
        ],
    }

    exit_group = {
        "logic": "AND",
        "conditions": [
            {
                "id": "2",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_9",
                "operator": "CROSSES_BELOW",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_31",
            }
        ],
    }

    print("   Entry: SMA(9) crosses above SMA(31)")
    print("   Exit: SMA(9) crosses below SMA(31)")

    # Step 6: Run backtest
    print_section("STEP 6: Run Backtest")

    # Compute indicators
    df = compute_indicators(df_raw.copy(), indicators)
    df, warmup_bars = trim_warmup_period(df)
    print(f"   Warmup bars trimmed: {warmup_bars}")
    print(f"   Bars after warmup: {len(df)}")

    # Trim regime labels to match
    regime_labels_trimmed = regime_labels.loc[df.index]

    # Evaluate signals
    entry_signal = evaluate_conditions(df, entry_group)
    exit_signal = evaluate_conditions(df, exit_group)

    # Run backtest
    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=initial_capital,
        asset_class="CRYPTO",
        position_size_type="full_capital",
        position_size_value=100.0,
    )

    # Generate report
    report = generate_report(trades, equity_curve, initial_capital)

    print(f"✅ Backtest complete")
    print(f"   Total trades: {report['total_trades']}")
    print(f"   Total return: {report['total_return_pct']:.2f}%")
    print(f"   Win rate: {report['win_rate']:.1f}%")
    print(f"   Sharpe ratio: {report['sharpe_ratio']:.2f}")

    # Step 7: Convert trades to dict format for regime analysis
    print_section("STEP 7: Analyze Trades by Regime")

    trades_dicts = [
        {
            "entry_date": t["entry_date"],
            "exit_date": t["exit_date"],
            "pnl_pct": t["pnl_pct"],
        }
        for t in trades
    ]

    print(f"   Analyzing {len(trades_dicts)} real trades...")

    regime_metrics = analyze_trades_by_regime(trades_dicts, regime_labels_trimmed)

    for regime, metrics in regime_metrics.items():
        print(f"\n   {regime}:")
        print(f"      Trades: {metrics['total_trades']}")
        print(f"      Total Return: {metrics['total_return_pct']:.2f}%")
        print(f"      Win Rate: {metrics['win_rate']:.1f}%")
        print(f"      Avg P&L: {metrics['avg_pnl_pct']:.2f}%")

    # Step 8: Assess regime dependency
    print_section("STEP 8: Assess Regime Dependency")
    dependency_level, dependency_score = assess_regime_dependency(regime_metrics)
    print(f"✅ Dependency Level: {dependency_level}")
    print(f"   CV Score: {dependency_score:.3f}")

    # Step 9: Build report
    print_section("STEP 9: Build Report")
    full_report = build_regime_report(
        segments,
        regime_labels,
        regime_metrics,
        distribution,
        dependency_level,
        dependency_score,
    )

    print(f"✅ Report Summary:")
    print(f"   Total Bars: {full_report['summary']['total_bars']}")
    print(f"   Total Segments: {full_report['summary']['total_segments']}")
    print(f"   Best Regime: {full_report['summary']['best_regime']}")
    print(f"   Worst Regime: {full_report['summary']['worst_regime']}")
    print(f"   Dependency: {full_report['summary']['dependency_level']} (score: {full_report['summary']['dependency_score']:.2f})")

    if full_report['assessment']['risk_flags']:
        print(f"\n   Risk Flags:")
        for flag in full_report['assessment']['risk_flags']:
            print(f"      ⚠️  {flag}")

    print(f"\n   Recommendation: {full_report['assessment']['recommendation'][:100]}...")

    # Validation
    dir_strategy = SegmentationFactory.create_strategy("directional")
    valid_regimes = dir_strategy.get_regime_types()

    assert len(segments) > 0, "Should have at least one segment"
    assert len(regime_labels) == len(df_raw), "Should have label for each bar"
    assert all(r in valid_regimes for r in regime_labels), "All labels should be valid regimes"
    assert "segments" in full_report
    assert "regimes" in full_report
    assert "summary" in full_report
    assert "assessment" in full_report
    assert len(trades) > 0, "Should have at least one trade"

    # Final summary
    print_section("SMOKE TEST RESULTS")

    print("\n✅ SMOKE TEST PASSED")
    print("\nRegime Detection (with pluggable strategies):")
    print("  ✅ Data fetching works")
    print("  ✅ Pluggable segmentation architecture works")
    print(f"     - Volatility: {len(changepoints_vol) - 1} segments → {vol_strategy.get_regime_types()}")
    print(f"     - Directional: {len(changepoints_dir) - 1} segments → {dir_strategy.get_regime_types()}")
    print("  ✅ Strategy-specific labeling works")
    print("  ✅ Feature extraction per strategy works")
    print("  ✅ Strength metric for directional regimes")
    print("  ✅ Real backtest executed")
    print(f"  ✅ {len(trades)} actual trades analyzed by regime")
    print("  ✅ Dependency assessment works")
    print("  ✅ Report structure valid")

    print("\n" + "=" * 80)
    print(f"  REGIME DETECTION: OPERATIONAL ✅")
    print(f"  {len(segments)} regimes, {len(trades)} trades, Dependency: {dependency_level}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ SMOKE TEST FAILED")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
