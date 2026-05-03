"""
Smoke Test for Directional Segmentation Strategy

Tests the directional (trend-based) regime detection end-to-end:
1. Fetch data
2. Detect regimes using directional strategy
3. Run real backtest with a simple strategy
4. Analyze actual trades by regime
5. Generate report

Signal: rolling_mean(log_returns)
Regimes: BULL, BEAR, CHOPPY, RANGING
Good for: Detecting trend reversals

Run: python scripts/smoke_directional_strategy.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

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
    analyze_cross_regime_trades,
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
    print_section("DIRECTIONAL STRATEGY - SMOKE TEST (WITH REAL TRADES)")

    # Configuration
    ticker = "BTCUSDT"
    start = "2026-03-01"
    end = "2026-04-25"
    initial_capital = 10000.0

    print(f"\nConfiguration:")
    print(f"  Ticker: {ticker}")
    print(f"  Period: {start} to {end}")
    print(f"  Strategy: directional")
    print(f"  Initial Capital: ${initial_capital:,.0f}")

    # Step 1: Fetch data
    print_section("STEP 1: Fetch OHLCV Data")
    df_raw = fetch_ohlcv(ticker, start, end, "5m", "CRYPTO")
    print(f"✅ Fetched {len(df_raw)} bars")
    print(f"   Date range: {df_raw.index[0].date()} to {df_raw.index[-1].date()}")

    # Step 2: Strategy info
    print_section("STEP 2: Strategy Info")
    strategy = SegmentationFactory.create_strategy("directional", r2_mode="fixed")
    
    print(f"   Strategy name: {strategy.get_strategy_name()}")
    print(f"   Regime types: {strategy.get_regime_types()}")
    print(f"   R² mode: {strategy.r2_mode}")
    if strategy.r2_mode == "percentile":
        print(f"   R² percentile: {strategy.r2_percentile} (top {100 - strategy.r2_percentile}% considered directional)")
    else:
        print(f"   R² fixed threshold: {strategy.r2_fixed}")

    # Step 3: Full regime detection with labels
    print_section("STEP 3: Detect & Label Regimes")
    segments, regime_labels = detect_regimes(
        df_raw,
        strategy="directional",
        penalty=None,
        min_segment_length=20,
        vol_window=20,
    )

    print(f"✅ Found {len(segments)} regime segments:")
    for i, seg in enumerate(segments[:15]):  # First 15
        strength_str = f", strength={seg.strength:.2f}" if seg.strength is not None else ""
        print(f"   Segment {i + 1}: {seg.start_date} to {seg.end_date} "
              f"({seg.bar_count} bars) → {seg.regime}{strength_str}")
        feat_str = ", ".join(f"{k}={v:.4f}" for k, v in seg.features.items() if isinstance(v, (int, float)))
        print(f"      Features: {feat_str}")

    if len(segments) > 15:
        print(f"   ... and {len(segments) - 15} more segments")

    # Step 4: Calculate regime distribution
    print_section("STEP 4: Regime Distribution")
    distribution = calculate_regime_distribution(regime_labels)
    for regime, pct in distribution.items():
        print(f"   {regime}: {pct:.1f}%")

    # Step 5: Define a simple SMA crossover strategy
    print_section("STEP 5: Define Trading Strategy (SMA 9/31 Crossover)")

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

    # Step 7: Analyze trades by regime
    print_section("STEP 7: Analyze Trades by Regime")

    trades_dicts = [
        {
            "entry_date": t["entry_date"],
            "exit_date": t["exit_date"],
            "pnl_pct": t["pnl_pct"],
            "entry_price": t["entry_price"],
            "exit_price": t["exit_price"],
        }
        for t in trades
    ]

    print(f"   Analyzing {len(trades_dicts)} real trades...")

    # Group trades by entry regime for detailed output
    from app.engine.robustness.regime_detection import get_regime_at_date
    trades_by_regime: dict[str, list] = {r: [] for r in ["BULL", "BEAR", "CHOPPY", "RANGING"]}
    for t in trades_dicts:
        entry_regime = get_regime_at_date(regime_labels_trimmed, pd.Timestamp(t["entry_date"]))
        exit_regime = get_regime_at_date(regime_labels_trimmed, pd.Timestamp(t["exit_date"]))
        trades_by_regime[entry_regime].append({**t, "exit_regime": exit_regime})

    regime_metrics = analyze_trades_by_regime(trades_dicts, regime_labels_trimmed)

    for regime, metrics in regime_metrics.items():
        print(f"\n   {regime}:")
        print(f"      Trades: {metrics['total_trades']}")
        print(f"      Total Return: {metrics['total_return_pct']:.2f}%")
        print(f"      Win Rate: {metrics['win_rate']:.1f}%")
        print(f"      Avg P&L: {metrics['avg_pnl_pct']:.2f}%")

        # Show first 5 trades for debugging
        regime_trades = trades_by_regime.get(regime, [])
        if regime_trades:
            print(f"      Sample trades (first 5):")
            for t in regime_trades:
                pnl_display = t["pnl_pct"] * 100  # Convert to percentage
                cross_marker = " [CROSS]" if t["exit_regime"] != regime else ""
                print(f"         {t['entry_date']} → {t['exit_date']}: "
                      f"${t['entry_price']:.2f} → ${t['exit_price']:.2f} "
                      f"({pnl_display:+.2f}%){cross_marker}")

    # Step 8: Cross-regime trade analysis
    print_section("STEP 8: Cross-Regime Trade Analysis")
    cross_regime = analyze_cross_regime_trades(trades_dicts, regime_labels_trimmed)

    print(f"   Total trades: {cross_regime['total_trades']}")
    print(f"   Cross-regime trades: {cross_regime['cross_regime_trades']} ({cross_regime['cross_regime_pct']:.1f}%)")
    print(f"   Cross-regime avg P&L: {cross_regime['cross_regime_avg_pnl']:.2f}%")
    print(f"   Same-regime avg P&L: {cross_regime['same_regime_avg_pnl']:.2f}%")

    if cross_regime['transitions']:
        print(f"\n   Regime transitions:")
        for transition, count in sorted(cross_regime['transitions'].items(), key=lambda x: -x[1]):
            print(f"      {transition}: {count} trades")

    # Step 9: Assess regime dependency
    print_section("STEP 9: Assess Regime Dependency")
    dependency_level, dependency_score = assess_regime_dependency(regime_metrics)
    print(f"✅ Dependency Level: {dependency_level}")
    print(f"   CV Score: {dependency_score:.3f}")

    # Step 10: Build report
    print_section("STEP 10: Build Report")
    full_report = build_regime_report(
        segments,
        regime_labels,
        regime_metrics,
        distribution,
        dependency_level,
        dependency_score,
        cross_regime_analysis=cross_regime,
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
    valid_regimes = strategy.get_regime_types()

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
    print("\nDirectional Strategy Regime Detection:")
    print("  ✅ Data fetching works")
    print("  ✅ PELT changepoint detection works")
    print("  ✅ Feature extraction works (slope, R², trend_score)")
    print("  ✅ R²-based labeling works")
    print(f"  ✅ 4 regimes: {strategy.get_regime_types()}")
    print("  ✅ Strength metric for BULL/BEAR regimes")
    print("  ✅ Real backtest executed")
    print(f"  ✅ {len(trades)} actual trades analyzed by regime")
    print("  ✅ Dependency assessment works")
    print("  ✅ Report structure valid")

    print("\n" + "=" * 80)
    print(f"  DIRECTIONAL STRATEGY: OPERATIONAL ✅")
    print(f"  {len(segments)} segments, {len(trades)} trades, Dependency: {dependency_level}")
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
