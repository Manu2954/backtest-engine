"""
Smoke Test for Walk-Forward Validation

Tests the walk-forward validation logic end-to-end using engine functions directly:
1. Fetch data and compute indicators
2. Generate windows
3. Run backtest for each window
4. Calculate consistency score
5. Assess results

No API/Celery - tests core logic only.

Run: python scripts/walk_forward_smoke.py
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
from app.engine.robustness.walk_forward import (  # noqa: E402
    generate_windows,
    calculate_consistency_score,
    assess_walk_forward_results,
    build_walk_forward_report,
)


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main() -> None:
    print_section("WALK-FORWARD VALIDATION - SMOKE TEST")

    # Configuration
    ticker = "MSFT"
    start = "2001-01-01"
    end = "2024-01-01"
    initial_capital = 10000.0
    window_count = 5

    print(f"\nConfiguration:")
    print(f"  Ticker: {ticker}")
    print(f"  Period: {start} to {end}")
    print(f"  Initial Capital: ${initial_capital:,.2f}")
    print(f"  Window Count: {window_count}")

    # Step 1: Fetch data
    print_section("STEP 1: Fetch OHLCV Data")
    df = fetch_ohlcv(ticker, start, end, "1d", "STOCK")
    print(f"✅ Fetched {len(df)} bars")

    # Step 2: Compute indicators
    print_section("STEP 2: Compute Indicators")
    indicators = [
        {"alias": "sma_9", "indicator_type": "SMA", "params": {"period": 9}},
        {"alias": "sma_31", "indicator_type": "SMA", "params": {"period": 31}},
    ]
    df = compute_indicators(df, indicators)
    print(f"✅ Computed indicators: sma_9, sma_31")

    # Step 3: Trim warmup
    print_section("STEP 3: Trim Warmup")
    df, warmup_bars = trim_warmup_period(df)
    print(f"✅ Trimmed {warmup_bars} warmup bars, {len(df)} bars remaining")

    # Step 4: Generate windows
    print_section("STEP 4: Generate Windows")
    windows = generate_windows(df, window_count)
    print(f"✅ Generated {len(windows)} windows:")
    for w in windows:
        bars = w.end_idx - w.start_idx + 1
        print(f"   Window {w.index}: {w.start_date} to {w.end_date} ({bars} bars)")

    # Step 5: Define strategy
    print_section("STEP 5: Define Strategy")
    entry_group = {
        "logic": "AND",
        "conditions": [
            {
                "id": "entry-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_9",
                "operator": "CROSSES_ABOVE",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_31",
            },
        ],
    }
    exit_group = {
        "logic": "AND",
        "conditions": [
            {
                "id": "exit-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_9",
                "operator": "CROSSES_BELOW",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_31",
            },
        ],
    }
    print("✅ Strategy: SMA 20/50 Crossover")
    print("   Entry: sma_9 crosses above sma_31")
    print("   Exit: sma_9 crosses below sma_31")

    # Step 6: Run backtests for each window
    print_section("STEP 6: Run Backtests Per Window")
    window_results = []

    for window in windows:
        # Slice dataframe
        df_window = df.iloc[window.start_idx:window.end_idx + 1].copy()

        # Evaluate conditions
        entry_signal = evaluate_conditions(df_window, entry_group)
        exit_signal = evaluate_conditions(df_window, exit_group)

        # Run backtest
        trades, equity_curve = run_backtest(
            df=df_window,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            initial_capital=initial_capital,
            asset_class="STOCK",
        )

        # for trade in trades:
        #     print(
        #         f"Entry {trade['entry_date'].date()} @ {trade['entry_price']:.2f} \n "
        #         f"Exit {trade['exit_date'].date()} @ {trade['exit_price']:.2f} \n "
        #         f"PnL {trade['pnl']:.2f} \n "
        #         f"Shares {trade['shares']:.2f} \n"
        #         f"Total capital = {equity_curve.at[trade['exit_date']]}\n"
        #         "-------------------------------------------------------------"
        #     )

        # Generate report
        report = generate_report(trades, equity_curve, initial_capital)
        print(f"{report}\n")
        print("------------------------------------\n")
        # Build result
        period_str = f"{window.start_date} to {window.end_date}"
        trade_count = report.get("total_trades", 0)

        result = {
            "period": period_str,
            "start_date": str(window.start_date),
            "end_date": str(window.end_date),
            "metrics": {
                "total_return_pct": round(report.get("total_return_pct", 0.0), 2),
                "sharpe_ratio": round(report.get("sharpe_ratio", 0.0), 2),
                "max_drawdown_pct": round(report.get("max_drawdown_pct", 0.0), 2),
                "win_rate": round(report.get("win_rate", 0.0), 2),
                "total_trades": trade_count,
            },
        }
        window_results.append(result)

        print(f"   Window {window.index}: Return={result['metrics']['total_return_pct']:+.2f}%, "
              f"Sharpe={result['metrics']['sharpe_ratio']:.2f}, "
              f"Trades={trade_count}")

    # Step 7: Calculate consistency
    print_section("STEP 7: Calculate Consistency Score")
    consistency_score, metric_cvs = calculate_consistency_score(window_results)
    print(f"✅ Consistency Score: {consistency_score:.3f}")
    print(f"   Per-Metric CV:")
    for metric, cv in metric_cvs.items():
        print(f"     • {metric}: {cv:.3f}")

    # Step 8: Assess results
    print_section("STEP 8: Assess Results")
    assessment = assess_walk_forward_results(window_results, consistency_score)
    print(f"✅ Assessment Level: {assessment['level']}")
    print(f"   Risk Flags: {len(assessment['risk_flags'])}")
    if assessment['risk_flags']:
        for flag in assessment['risk_flags']:
            print(f"     ⚠️  {flag}")
    print(f"   Recommendation: {assessment['recommendation'][:100]}...")

    # Step 9: Build full report
    print_section("STEP 9: Build Report")
    report = build_walk_forward_report(
        window_results,
        consistency_score,
        metric_cvs,
        assessment,
    )

    print(f"✅ Report Summary:")
    print(f"   Total Windows: {report['summary']['total_windows']}")
    print(f"   Sufficient Sample Windows: {report['summary']['sufficient_sample_windows']}")
    print(f"   Profitable Windows: {report['summary']['profitable_windows']}")
    print(f"   Profitable Ratio: {report['summary']['profitable_ratio']:.0%}")
    print(f"   Return Range: [{report['summary']['return_range']['min']:.2f}%, {report['summary']['return_range']['max']:.2f}%]")
    print(f"   Best Window: {report['summary']['best_window']}")
    print(f"   Worst Window: {report['summary']['worst_window']}")

    # Validation
    assert len(report["windows"]) == window_count
    assert "summary" in report
    assert "assessment" in report
    assert 0.0 <= consistency_score <= 1.0
    assert assessment["level"] in ["ROBUST", "MODERATE", "FRAGILE"]

    # Final summary
    print_section("SMOKE TEST RESULTS")

    print("\n✅ SMOKE TEST PASSED")
    print("\nWalk-Forward Validation:")
    print("  ✅ Data fetching works")
    print("  ✅ Indicator computation works")
    print("  ✅ Window generation works")
    print("  ✅ Per-window backtest works")
    print("  ✅ Consistency score calculation works")
    print("  ✅ Assessment generation works")
    print("  ✅ Report structure valid")

    print("\n" + "=" * 80)
    print(f"  WALK-FORWARD VALIDATION: OPERATIONAL ✅")
    print(f"  Consistency: {assessment['level']} (score: {consistency_score:.2f})")
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
