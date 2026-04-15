"""
End-to-End Engine Smoke Test - Full Backtest Flow (No API/Celery)

Tests the complete backtest pipeline using engine functions directly:
1. Fetch OHLCV data
2. Compute indicators
3. Trim warmup period
4. Evaluate conditions
5. Run backtest with attribution
6. Generate reports
7. Run robustness analysis
8. Verify all outputs

No network calls to API - tests engine logic only.
Requires: Redis running for OHLCV cache (docker-compose up redis)

Run: python scripts/e2e_engine_smoke.py
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
from app.engine.report_generator import (  # noqa: E402
    generate_report,
    generate_attribution_report,
    generate_binning_report,
    calculate_buy_and_hold_equity,
)
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


def print_subsection(title: str) -> None:
    """Print a subsection header."""
    print(f"\n--- {title} ---")


def main() -> None:
    print_section("E2E ENGINE SMOKE TEST - FULL BACKTEST FLOW")

    # Configuration
    ticker = "AAPL"
    start_date = "2020-01-01"
    end_date = "2024-01-01"
    resolution = "1d"
    asset_class = "STOCK"
    initial_capital = 10000.0

    print(f"\nConfiguration:")
    print(f"  Ticker: {ticker}")
    print(f"  Period: {start_date} to {end_date}")
    print(f"  Resolution: {resolution}")
    print(f"  Asset Class: {asset_class}")
    print(f"  Initial Capital: ${initial_capital:,.2f}")

    # =========================================================================
    # STEP 1: Fetch OHLCV Data
    # =========================================================================
    print_section("STEP 1: Fetch OHLCV Data")

    df_raw = fetch_ohlcv(ticker, start_date, end_date, resolution, asset_class)

    print(f"Fetched {len(df_raw)} bars")
    print(f"  Date Range: {df_raw.index[0].date()} to {df_raw.index[-1].date()}")
    print(f"  Columns: {list(df_raw.columns)}")

    assert len(df_raw) > 100, f"Expected >100 bars, got {len(df_raw)}"
    assert "open" in df_raw.columns
    assert "high" in df_raw.columns
    assert "low" in df_raw.columns
    assert "close" in df_raw.columns
    assert "volume" in df_raw.columns

    # Store original for benchmark calculation
    df_original = df_raw[["open", "high", "low", "close", "volume"]].copy()

    # =========================================================================
    # STEP 2: Compute Indicators
    # =========================================================================
    print_section("STEP 2: Compute Indicators")

    indicators = [
        {"alias": "sma_20", "indicator_type": "SMA", "params": {"period": 20}},
        {"alias": "sma_50", "indicator_type": "SMA", "params": {"period": 50}},
        {"alias": "rsi_14", "indicator_type": "RSI", "params": {"period": 14}},
        {"alias": "atr_14", "indicator_type": "ATR", "params": {"period": 14}},
    ]

    df = compute_indicators(df_raw.copy(), indicators)

    print(f"Computed {len(indicators)} indicators")
    for ind in indicators:
        alias = ind["alias"]
        non_nan = df[alias].notna().sum()
        print(f"  {alias}: {non_nan}/{len(df)} non-NaN values")

    assert "sma_20" in df.columns
    assert "sma_50" in df.columns
    assert "rsi_14" in df.columns
    assert "atr_14" in df.columns

    # =========================================================================
    # STEP 3: Trim Warmup Period
    # =========================================================================
    print_section("STEP 3: Trim Warmup Period")

    requested_start = df_raw.index[0].date()
    df, warmup_bars = trim_warmup_period(df)
    actual_start = df.index[0].date() if not df.empty else requested_start

    print(f"Warmup Analysis:")
    print(f"  Requested Start: {requested_start}")
    print(f"  Actual Start: {actual_start}")
    print(f"  Warmup Bars Trimmed: {warmup_bars}")
    print(f"  Remaining Bars: {len(df)}")

    if warmup_bars > 0:
        print(f"  Note: Backtest starts {warmup_bars} bars after requested date")

    assert len(df) > 30, f"Need at least 30 bars after warmup, got {len(df)}"
    assert df["sma_50"].isna().sum() == 0, "SMA_50 should have no NaN after warmup"

    # =========================================================================
    # STEP 4: Define Strategy & Evaluate Conditions
    # =========================================================================
    print_section("STEP 4: Define Strategy & Evaluate Conditions")

    # Entry: SMA 20 crosses above SMA 50 AND RSI > 40
    entry_group = {
        "logic": "AND",
        "conditions": [
            {
                "id": "entry-sma-cross",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_20",
                "operator": "CROSSES_ABOVE",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_50",
            },
            {
                "id": "entry-rsi-filter",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "40",
            },
        ],
    }

    # Exit: SMA 20 crosses below SMA 50 OR RSI < 30
    exit_group = {
        "logic": "OR",
        "conditions": [
            {
                "id": "exit-sma-cross",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_20",
                "operator": "CROSSES_BELOW",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_50",
            },
            {
                "id": "exit-rsi-oversold",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "30",
            },
        ],
    }

    print("Strategy:")
    print("  Entry: SMA_20 crosses above SMA_50 AND RSI_14 > 40")
    print("  Exit: SMA_20 crosses below SMA_50 OR RSI_14 < 30")

    entry_signal = evaluate_conditions(df, entry_group)
    exit_signal = evaluate_conditions(df, exit_group)

    print(f"\nSignals:")
    print(f"  Entry signals: {entry_signal.sum()} bars")
    print(f"  Exit signals: {exit_signal.sum()} bars")

    assert entry_signal.sum() > 0, "Expected at least 1 entry signal"

    # =========================================================================
    # STEP 5: Run Backtest with Attribution
    # =========================================================================
    print_section("STEP 5: Run Backtest with Attribution")

    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=initial_capital,
        asset_class=asset_class,
        position_size_type="full_capital",
        commission_per_trade=1.0,
        slippage_pct=0.05,
        enable_attribution=True,
        entry_conditions=entry_group,
        exit_conditions=exit_group,
    )

    print(f"Backtest Results:")
    print(f"  Total Trades: {len(trades)}")
    print(f"  Equity Curve Length: {len(equity_curve)}")

    if trades:
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] < 0]
        print(f"  Winning Trades: {len(wins)}")
        print(f"  Losing Trades: {len(losses)}")

        print_subsection("Sample Trades")
        for i, trade in enumerate(trades[:3]):
            print(f"  Trade {i+1}:")
            print(f"    Entry: {trade['entry_date'].date()} @ ${trade['entry_price']:.2f}")
            print(f"    Exit: {trade['exit_date'].date()} @ ${trade['exit_price']:.2f}")
            print(f"    PnL: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")
            print(f"    Exit Reason: {trade.get('exit_reason', 'signal')}")

    assert len(equity_curve) > 0, "Equity curve should not be empty"

    # =========================================================================
    # STEP 6: Generate Reports
    # =========================================================================
    print_section("STEP 6: Generate Reports")

    # Calculate benchmark
    benchmark_equity = calculate_buy_and_hold_equity(df_original, initial_capital, asset_class)

    # Main report
    report = generate_report(trades, equity_curve, initial_capital, benchmark_equity=benchmark_equity)

    # Add warmup info (as backtest_task.py does)
    report["requested_start_date"] = str(requested_start)
    report["actual_start_date"] = str(actual_start)
    report["warmup_bars_trimmed"] = warmup_bars
    if warmup_bars > 0:
        report["warmup_note"] = (
            f"Backtest started {warmup_bars} bars after requested date due to indicator warmup. "
            f"Requested: {requested_start}, Actual: {actual_start}"
        )

    print_subsection("Core Metrics")
    print(f"  Total Return: {report['total_return_pct']:.2f}%")
    print(f"  CAGR: {report['cagr']:.2f}%")
    print(f"  Sharpe Ratio: {report['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {report['max_drawdown_pct']:.2f}%")
    print(f"  Total Trades: {report['total_trades']}")
    print(f"  Win Rate: {report['win_rate']:.2f}%")
    print(f"  Profit Factor: {report['profit_factor']:.2f}")
    print(f"  Final Capital: ${report['final_capital']:,.2f}")

    print_subsection("Warmup Info")
    print(f"  Requested Start: {report['requested_start_date']}")
    print(f"  Actual Start: {report['actual_start_date']}")
    print(f"  Warmup Bars: {report['warmup_bars_trimmed']}")

    print_subsection("Benchmark Comparison")
    if "benchmark_return_pct" in report:
        print(f"  Benchmark Return: {report['benchmark_return_pct']:.2f}%")
        print(f"  Alpha: {report.get('alpha', 0):.2f}%")
        print(f"  Beta: {report.get('beta', 0):.2f}")

    # Verify report structure
    assert "total_return_pct" in report
    assert "cagr" in report
    assert "sharpe_ratio" in report
    assert "requested_start_date" in report
    assert "actual_start_date" in report
    assert "warmup_bars_trimmed" in report

    # Attribution report
    if trades:
        attribution_report = generate_attribution_report(trades)
        if attribution_report:
            print_subsection("Attribution Report")
            print(f"  Total Alpha: {attribution_report['total_alpha']:.2f}%")
            print(f"  Signal Strength Bins: {list(attribution_report['signal_strength'].keys())}")

            for bin_name, stats in attribution_report['signal_strength'].items():
                if stats['count'] > 0:
                    print(f"    {bin_name}: {stats['count']} trades, {stats['win_rate']:.1f}% win rate")

    # Binning report
    if len(trades) >= 50:
        all_conditions = entry_group["conditions"] + exit_group["conditions"]
        binning_report = generate_binning_report(trades, indicators, conditions=all_conditions)
        if binning_report:
            print_subsection("Binning Analysis")
            print(f"  Analyzed Indicators: {binning_report.get('summary', {}).get('analyzed_indicators', 'N/A')}")

    # =========================================================================
    # STEP 7: Run Robustness Analysis
    # =========================================================================
    print_section("STEP 7: Run Robustness Analysis")

    # Build strategy dict for variant generation
    strategy_dict = {
        "name": "SMA Crossover with RSI Filter",
        "indicators": indicators,
        "condition_groups": [
            {"group_type": "ENTRY", **entry_group},
            {"group_type": "EXIT", **exit_group},
        ],
    }

    # Generate variants
    variation_pct = 0.2
    variants = generate_parameter_variants(strategy_dict, variation_pct)

    print(f"Generated {len(variants)} parameter variants (+/-{variation_pct*100:.0f}%)")
    for v in variants:
        print(f"  - {v['variant_label']}")

    # Run baseline metrics (already have from step 6)
    baseline_metrics = {
        "total_return_pct": report["total_return_pct"],
        "sharpe_ratio": report["sharpe_ratio"],
        "win_rate": report["win_rate"],
        "max_drawdown_pct": report["max_drawdown_pct"],
        "total_trades": report["total_trades"],
    }

    # Run variant backtests
    print_subsection("Running Variant Backtests")
    variant_metrics_list = []

    for i, variant_data in enumerate(variants):
        variant_strategy = variant_data["strategy"]

        # Compute indicators for variant
        df_variant = compute_indicators(df_raw.copy(), variant_strategy["indicators"])
        df_variant, _ = trim_warmup_period(df_variant)

        if len(df_variant) < 30:
            print(f"  {i+1}. {variant_data['variant_label']}: SKIPPED (insufficient data)")
            continue

        # Evaluate conditions
        v_entry_group = variant_strategy["condition_groups"][0]
        v_exit_group = variant_strategy["condition_groups"][1]

        v_entry_signal = evaluate_conditions(df_variant, v_entry_group)
        v_exit_signal = evaluate_conditions(df_variant, v_exit_group)

        # Run backtest
        v_trades, v_equity = run_backtest(
            df=df_variant,
            entry_signal=v_entry_signal,
            exit_signal=v_exit_signal,
            initial_capital=initial_capital,
            asset_class=asset_class,
        )

        # Generate report
        v_report = generate_report(v_trades, v_equity, initial_capital)

        metrics = {
            "total_return_pct": v_report.get("total_return_pct", 0.0),
            "sharpe_ratio": v_report.get("sharpe_ratio", 0.0),
            "win_rate": v_report.get("win_rate", 0.0),
            "max_drawdown_pct": v_report.get("max_drawdown_pct", 0.0),
            "total_trades": v_report.get("total_trades", 0),
        }
        variant_metrics_list.append(metrics)

        delta = metrics["total_return_pct"] - baseline_metrics["total_return_pct"]
        print(f"  {i+1}. {variant_data['variant_label']}: {metrics['total_return_pct']:.2f}% ({delta:+.2f}%)")

    # Calculate stability
    print_subsection("Stability Analysis")

    if variant_metrics_list:
        stability_score, metric_cvs = calculate_stability_score(baseline_metrics, variant_metrics_list)
        robustness_level = assess_robustness_level(stability_score)
        risk_flags = generate_risk_flags(baseline_metrics, variant_metrics_list, metric_cvs)
        recommendation = generate_recommendation(robustness_level, risk_flags, stability_score)

        print(f"  Stability Score: {stability_score:.3f}")
        print(f"  Robustness Level: {robustness_level}")
        print(f"  Risk Flags: {len(risk_flags)}")
        if risk_flags:
            for flag in risk_flags:
                print(f"    - {flag}")
        print(f"  Recommendation: {recommendation[:80]}...")

        assert 0.0 <= stability_score <= 1.0
        assert robustness_level in ["ROBUST", "MODERATE", "FRAGILE"]
    else:
        print("  No variants completed - skipping stability analysis")

    # =========================================================================
    # STEP 8: Final Validation
    # =========================================================================
    print_section("STEP 8: Final Validation")

    print("\nAll engine functions tested:")
    print("  1. fetch_ohlcv() - Data fetching")
    print("  2. compute_indicators() - Indicator computation")
    print("  3. trim_warmup_period() - Warmup handling")
    print("  4. evaluate_conditions() - Signal generation")
    print("  5. run_backtest() - Trade simulation with attribution")
    print("  6. generate_report() - Performance metrics")
    print("  7. calculate_buy_and_hold_equity() - Benchmark")
    print("  8. generate_attribution_report() - Attribution analysis")
    print("  9. generate_parameter_variants() - Robustness variants")
    print("  10. calculate_stability_score() - Stability metrics")
    print("  11. assess_robustness_level() - Robustness assessment")

    print("\n" + "=" * 80)
    print("  E2E ENGINE SMOKE TEST: PASSED")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nE2E ENGINE SMOKE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
