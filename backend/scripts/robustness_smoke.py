"""
Smoke Test for Parameter Sensitivity / Robustness Analysis

Tests the core robustness analysis logic end-to-end:
1. Fetch data and compute indicators
2. Generate parameter variants
3. Run baseline and variant backtests
4. Calculate stability metrics
5. Assess robustness level

No network calls - tests engine functions directly.

Run: python scripts/robustness_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv  # noqa: E402
from app.engine.indicator_layer import compute_indicators  # noqa: E402
from app.engine.condition_engine import evaluate_conditions  # noqa: E402
from app.engine.state_machine import run_backtest  # noqa: E402
from app.engine.report_generator import generate_report  # noqa: E402
from app.engine.robustness.parameter_sensitivity import (  # noqa: E402
    generate_parameter_variants,
    calculate_stability_score,
    assess_robustness_level,
    generate_risk_flags,
    generate_recommendation,
)


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def run_backtest_for_strategy(
    df_base,
    strategy_dict: dict,
    initial_capital: float,
) -> dict:
    """
    Run backtest for a strategy dict and return key metrics.
    """
    # Compute indicators for this strategy variant
    df = df_base.copy()
    df = compute_indicators(df, strategy_dict["indicators"])

    # Evaluate conditions
    entry_group = strategy_dict["condition_groups"][0]  # First ENTRY group
    exit_group = strategy_dict["condition_groups"][1]   # First EXIT group

    entry_signal = evaluate_conditions(df, entry_group)
    exit_signal = evaluate_conditions(df, exit_group)

    # Run backtest
    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
    )

    for trade in trades:
        print(
            f"Entry {trade['entry_date'].date()} @ {trade['entry_price']:.2f} \n "
            f"Exit {trade['exit_date'].date()} @ {trade['exit_price']:.2f} \n "
            f"PnL {trade['pnl']:.2f} \n "
            f"Shares {trade['shares']:.2f} \n"
            f"Total capital = {equity_curve.at[trade['exit_date']]}\n"
            "-------------------------------------------------------------"
        )

    # Generate report
    report = generate_report(trades, equity_curve, initial_capital)

    return {
        "total_return_pct": report.get("total_return_pct", 0.0),
        "sharpe_ratio": report.get("sharpe_ratio", 0.0),
        "win_rate": report.get("win_rate", 0.0),
        "max_drawdown_pct": report.get("max_drawdown_pct", 0.0),
        "total_trades": report.get("total_trades", 0),
    }


def main() -> None:
    print_section("PARAMETER SENSITIVITY / ROBUSTNESS ANALYSIS - SMOKE TEST")

    # Configuration
    ticker = "ICICIBANK.NS"
    start = "2002-01-01"
    end = "2024-01-01"
    initial_capital = 10000.0
    variation_pct = 0.2  # ±20%

    print(f"\nConfiguration:")
    print(f"  Ticker: {ticker}")
    print(f"  Period: {start} to {end}")
    print(f"  Initial Capital: ${initial_capital:,.2f}")
    print(f"  Parameter Variation: ±{variation_pct*100:.0f}%")

    # Step 1: Fetch data
    print_section("STEP 1: Fetch OHLCV Data")
    df_base = fetch_ohlcv(ticker, start, end, "1d", "STOCK")
    print(f"✅ Fetched {len(df_base)} bars")

    # Step 2: Define base strategy
    print_section("STEP 2: Define Base Strategy")

    # Use a more active strategy (SMA crossover) to ensure trades are generated
    base_strategy = {
        "name": "SMA Crossover Strategy",
        "indicators": [
            {"alias": "sma_50", "indicator_type": "SMA", "params": {"period": 50}},
            {"alias": "sma_200", "indicator_type": "SMA", "params": {"period": 200}},
        ],
        "condition_groups": [
            {
                "group_type": "ENTRY",
                "logic": "AND",
                "conditions": [
                    {
                        "left_operand_type": "INDICATOR",
                        "left_operand_value": "sma_50",
                        "operator": "CROSSES_ABOVE",
                        "right_operand_type": "INDICATOR",
                        "right_operand_value": "sma_200",
                    },
                ],
            },
            {
                "group_type": "EXIT",
                "logic": "AND",
                "conditions": [
                    {
                        "left_operand_type": "INDICATOR",
                        "left_operand_value": "sma_50",
                        "operator": "CROSSES_BELOW",
                        "right_operand_type": "INDICATOR",
                        "right_operand_value": "sma_200",
                    },
                ],
            },
        ],
    }

    print(f"✅ Strategy: {base_strategy['name']}")
    print(f"   Indicators: sma_50 (period=50), sma_200 (period=200)")
    print(f"   Entry: SMA50 crosses above SMA200")
    print(f"   Exit: SMA200 crosses below SMA50")

    # Step 3: Generate parameter variants
    print_section("STEP 3: Generate Parameter Variants")

    variants = generate_parameter_variants(base_strategy, variation_pct)

    print(f"✅ Generated {len(variants)} variants:")
    for i, v in enumerate(variants):
        print(f"   {i+1}. {v['variant_label']}")

    assert len(variants) == 4, f"Expected 4 variants (2 indicators × 2 directions), got {len(variants)}"
    print(f"\n✅ Variant count correct (4 variants)")

    # Step 4: Run baseline backtest
    print_section("STEP 4: Run Baseline Backtest")

    baseline_metrics = run_backtest_for_strategy(df_base, base_strategy, initial_capital)

    print(f"✅ Baseline Metrics:")
    print(f"   - Total Return: {baseline_metrics['total_return_pct']:.2f}%")
    print(f"   - Sharpe Ratio: {baseline_metrics['sharpe_ratio']:.2f}")
    print(f"   - Win Rate: {baseline_metrics['win_rate']:.2f}%")
    print(f"   - Max Drawdown: {baseline_metrics['max_drawdown_pct']:.2f}%")
    print(f"   - Total Trades: {baseline_metrics['total_trades']}")

    # Step 5: Run variant backtests
    print_section("STEP 5: Run Variant Backtests")

    variant_metrics_list = []
    for i, variant_data in enumerate(variants):
        variant_strategy = variant_data["strategy"]
        metrics = run_backtest_for_strategy(df_base, variant_strategy, initial_capital)
        variant_metrics_list.append(metrics)

        delta_return = metrics["total_return_pct"] - baseline_metrics["total_return_pct"]
        print(f"   {i+1}. {variant_data['variant_label']}")
        print(f"      Return: {metrics['total_return_pct']:.2f}% (Δ {delta_return:+.2f}%)")

    print(f"\n✅ Completed {len(variant_metrics_list)} variant backtests")

    # Step 6: Calculate stability metrics
    print_section("STEP 6: Calculate Stability Metrics")

    stability_score, metric_cvs = calculate_stability_score(
        baseline_metrics,
        variant_metrics_list,
    )

    print(f"✅ Stability Analysis:")
    print(f"   - Overall Stability Score: {stability_score:.3f}")
    print(f"   - Per-Metric Coefficient of Variation:")
    for metric, cv in metric_cvs.items():
        print(f"     • {metric}: {cv:.3f}")

    assert 0.0 <= stability_score <= 1.0, f"Stability score out of range: {stability_score}"
    print(f"\n✅ Stability score in valid range [0.0, 1.0]")

    # Step 7: Assess robustness level
    print_section("STEP 7: Assess Robustness Level")

    robustness_level = assess_robustness_level(stability_score)
    risk_flags = generate_risk_flags(baseline_metrics, variant_metrics_list, metric_cvs)
    recommendation = generate_recommendation(robustness_level, risk_flags, stability_score)

    print(f"✅ Robustness Assessment:")
    print(f"   - Level: {robustness_level}")
    print(f"   - Risk Flags: {len(risk_flags)}")
    if risk_flags:
        for flag in risk_flags:
            print(f"     ⚠️  {flag}")
    print(f"   - Recommendation: {recommendation[:100]}{'...' if len(recommendation) > 100 else ''}")

    assert robustness_level in ["ROBUST", "MODERATE", "FRAGILE"], \
        f"Invalid robustness level: {robustness_level}"
    print(f"\n✅ Robustness level valid")

    # Step 8: Build full report structure
    print_section("STEP 8: Build Report Structure")

    report = {
        "baseline": {
            "strategy_name": base_strategy["name"],
            "params": {
                ind["alias"]: ind["params"]
                for ind in base_strategy["indicators"]
            },
            "metrics": baseline_metrics,
        },
        "variants": [
            {
                "variant_label": variants[i]["variant_label"],
                "variant_params": variants[i]["variant_params"],
                "metrics": variant_metrics_list[i],
                "delta_from_baseline": {
                    "total_return_pct": variant_metrics_list[i]["total_return_pct"] - baseline_metrics["total_return_pct"],
                    "sharpe_ratio": variant_metrics_list[i]["sharpe_ratio"] - baseline_metrics["sharpe_ratio"],
                    "win_rate": variant_metrics_list[i]["win_rate"] - baseline_metrics["win_rate"],
                }
            }
            for i in range(len(variants))
        ],
        "stability_metrics": {
            "overall_stability_score": stability_score,
            "per_metric_cv": metric_cvs,
        },
        "assessment": {
            "robustness_level": robustness_level,
            "risk_flags": risk_flags,
            "recommendation": recommendation,
        },
    }

    # Validate report structure
    assert "baseline" in report
    assert "variants" in report
    assert "stability_metrics" in report
    assert "assessment" in report
    assert len(report["variants"]) == 4

    print(f"✅ Report structure valid")
    print(f"   - Baseline: ✓")
    print(f"   - Variants: {len(report['variants'])} ✓")
    print(f"   - Stability Metrics: ✓")
    print(f"   - Assessment: ✓")

    # Final summary
    print_section("SMOKE TEST RESULTS")

    print("\n✅ SMOKE TEST PASSED")
    print("\nParameter Sensitivity / Robustness Analysis:")
    print("  ✅ Data fetching works")
    print("  ✅ Indicator computation works")
    print("  ✅ Parameter variant generation works")
    print("  ✅ Backtest execution works")
    print("  ✅ Stability score calculation works")
    print("  ✅ Robustness assessment works")
    print("  ✅ Report structure valid")

    print("\n" + "=" * 80)
    print(f"  ROBUSTNESS ANALYSIS: OPERATIONAL ✅")
    print(f"  Strategy robustness: {robustness_level} (stability: {stability_score:.2f})")
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
