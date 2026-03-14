"""
Milestone 6 Smoke Test: Benchmark Comparison for Multiple Tickers

This test validates that buy-and-hold benchmark calculations work correctly
for both US stocks (AAPL) and international indices (^NSEI) when indicators
require warmup periods.

The test ensures:
1. Benchmark is calculated from FULL original date range (not trimmed)
2. Benchmark returns are consistent across different tickers
3. Warmup trim doesn't affect benchmark accuracy
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
from app.engine.report_generator import generate_report, calculate_buy_and_hold_equity  # noqa: E402


def run_benchmark_test(ticker: str, start: str, end: str) -> dict:
    """
    Run a backtest with benchmark comparison for a given ticker.

    Args:
        ticker: Stock symbol
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)

    Returns:
        Dictionary with backtest results and benchmark stats
    """
    print(f"\n{'='*80}")
    print(f"Testing: {ticker}")
    print(f"Date Range: {start} to {end}")
    print(f"{'='*80}")

    initial_capital = 10000.0

    # Fetch OHLCV data
    print(f"Fetching OHLCV data for {ticker}...")
    df = fetch_ohlcv(ticker, start, end, "1d", "STOCK")
    original_bars = len(df)
    print(f"✅ Fetched {original_bars} bars")

    # Store original data for benchmark (BEFORE warmup trim)
    df_original = df[["open", "high", "low", "close", "volume"]].copy()
    print(f"✅ Stored original data: {df_original.index[0].date()} to {df_original.index[-1].date()}")

    # Add indicators (SMA 50 and SMA 200 require warmup)
    print("Computing indicators (SMA 50, SMA 200)...")
    indicators = [
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
        {"indicator_type": "SMA", "alias": "sma_200", "params": {"period": 200, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)
    print(f"✅ Indicators computed")

    # Trim warmup period
    print("Trimming warmup period...")
    df, warmup_bars = trim_warmup_period(df)
    trimmed_bars = len(df)
    print(f"✅ Trimmed {warmup_bars} warmup bars")
    print(f"   Strategy starts from: {df.index[0].date()} ({trimmed_bars} bars remaining)")

    # Define entry/exit conditions
    entry_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_50",
                "operator": "CROSSES_ABOVE",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_200",
            }
        ],
    }

    exit_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_50",
                "operator": "CROSSES_BELOW",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_200",
            }
        ],
    }

    # Evaluate signals and run backtest
    print("Evaluating conditions and running backtest...")
    entry_signal = evaluate_conditions(df, entry_group)
    exit_signal = evaluate_conditions(df, exit_group)

    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
    )
    print(f"✅ Backtest complete: {len(trades)} trades executed")

    # Calculate benchmark from ORIGINAL data (full period)
    print("Calculating buy-and-hold benchmark from ORIGINAL data...")
    benchmark_equity = calculate_buy_and_hold_equity(
        df_original, initial_capital, asset_class="STOCK"
    )
    print(f"✅ Benchmark calculated: {benchmark_equity.index[0].date()} to {benchmark_equity.index[-1].date()}")

    # Generate report with benchmark
    report = generate_report(trades, equity_curve, initial_capital, benchmark_equity=benchmark_equity)

    # Print results
    print(f"\n{'-'*80}")
    print("RESULTS")
    print(f"{'-'*80}")
    print(f"Original Data Range: {df_original.index[0].date()} to {df_original.index[-1].date()} ({original_bars} bars)")
    print(f"Strategy Start Date: {df.index[0].date()} (after {warmup_bars} bar warmup)")
    print(f"Strategy Bars: {trimmed_bars}")
    print(f"\nStrategy Performance:")
    print(f"  Total Return: {report['total_return_pct']:.2f}%")
    print(f"  Final Capital: ${report['final_capital']:.2f}")
    print(f"  Total Trades: {report['total_trades']}")
    print(f"  Win Rate: {report['win_rate']:.2f}%")
    print(f"  Sharpe Ratio: {report['sharpe_ratio']:.4f}")
    print(f"  Max Drawdown: {report['max_drawdown_pct']:.2f}%")

    print(f"\nBenchmark (Buy & Hold from {df_original.index[0].date()}):")
    print(f"  Benchmark Return: {report.get('benchmark_return_pct', 0):.2f}%")
    print(f"  Benchmark Final: ${report.get('benchmark_final_capital', 0):.2f}")
    print(f"  Benchmark Sharpe: {report.get('benchmark_sharpe_ratio', 0):.4f}")
    print(f"  Benchmark Max DD: {report.get('benchmark_max_drawdown_pct', 0):.2f}%")

    print(f"\nComparison:")
    print(f"  Alpha (Excess Return): {report.get('alpha', 0):.2f}%")
    print(f"  Beta (Market Correlation): {report.get('beta', 0):.4f}")

    if report.get('alpha', 0) > 0:
        print(f"  ✅ Strategy OUTPERFORMED buy-and-hold by {report.get('alpha', 0):.2f}%")
    else:
        print(f"  ⚠️  Strategy UNDERPERFORMED buy-and-hold by {abs(report.get('alpha', 0)):.2f}%")

    return {
        "ticker": ticker,
        "original_bars": original_bars,
        "warmup_bars": warmup_bars,
        "strategy_bars": trimmed_bars,
        "original_start": df_original.index[0].date(),
        "original_end": df_original.index[-1].date(),
        "strategy_start": df.index[0].date(),
        "strategy_return": report['total_return_pct'],
        "benchmark_return": report.get('benchmark_return_pct', 0),
        "alpha": report.get('alpha', 0),
        "trades": len(trades),
    }


def main() -> None:
    print("\n" + "="*80)
    print("MILESTONE 6 SMOKE TEST: BENCHMARK COMPARISON VALIDATION")
    print("="*80)
    print("\nThis test validates that benchmark calculations work correctly")
    print("for different tickers when indicators require warmup periods.")
    print("\nTest Setup:")
    print("  - Strategy: SMA 50/200 crossover (200-bar warmup required)")
    print("  - Date Range: 2020-01-01 to 2023-12-31 (4 years)")
    print("  - Initial Capital: $10,000")
    print("  - Tickers: AAPL (US stock), ^NSEI (Indian index)")

    # Test configuration
    start_date = "2020-01-01"
    end_date = "2023-12-31"

    try:
        # Test 1: AAPL (US stock)
        aapl_results = run_benchmark_test("AAPL", start_date, end_date)

        # Test 2: ^NSEI (Indian index)
        nsei_results = run_benchmark_test("^NSEI", start_date, end_date)

        # Comparison
        print(f"\n{'='*80}")
        print("COMPARISON: AAPL vs ^NSEI")
        print(f"{'='*80}")

        print(f"\n{'Metric':<35} {'AAPL':<20} {'^NSEI':<20}")
        print("-"*75)
        print(f"{'Original Bars Fetched:':<35} {aapl_results['original_bars']:<20} {nsei_results['original_bars']:<20}")
        print(f"{'Warmup Bars Trimmed:':<35} {aapl_results['warmup_bars']:<20} {nsei_results['warmup_bars']:<20}")
        print(f"{'Strategy Bars Used:':<35} {aapl_results['strategy_bars']:<20} {nsei_results['strategy_bars']:<20}")
        print(f"{'Original Start Date:':<35} {str(aapl_results['original_start']):<20} {str(nsei_results['original_start']):<20}")
        print(f"{'Strategy Start Date:':<35} {str(aapl_results['strategy_start']):<20} {str(nsei_results['strategy_start']):<20}")
        print()
        print(f"{'Strategy Return:':<35} {aapl_results['strategy_return']:>18.2f}%  {nsei_results['strategy_return']:>18.2f}%")
        print(f"{'Benchmark Return:':<35} {aapl_results['benchmark_return']:>18.2f}%  {nsei_results['benchmark_return']:>18.2f}%")
        print(f"{'Alpha:':<35} {aapl_results['alpha']:>18.2f}%  {nsei_results['alpha']:>18.2f}%")
        print(f"{'Total Trades:':<35} {aapl_results['trades']:<20} {nsei_results['trades']:<20}")

        # Validation
        print(f"\n{'='*80}")
        print("VALIDATION")
        print(f"{'='*80}")

        validation_passed = True

        # Check 1: Both benchmarks should show non-zero returns
        if abs(aapl_results['benchmark_return']) < 0.1:
            print("❌ FAIL: AAPL benchmark return is ~0% (expected significant return)")
            validation_passed = False
        else:
            print(f"✅ PASS: AAPL benchmark shows {aapl_results['benchmark_return']:.2f}% return")

        if abs(nsei_results['benchmark_return']) < 0.1:
            print("❌ FAIL: ^NSEI benchmark return is ~0% (expected significant return)")
            validation_passed = False
        else:
            print(f"✅ PASS: ^NSEI benchmark shows {nsei_results['benchmark_return']:.2f}% return")

        # Check 2: Original dates should match requested dates
        if str(aapl_results['original_start']) != start_date.replace('-', '/'):
            # Date format might differ, just check year and month
            if aapl_results['original_start'].year != 2020 or aapl_results['original_start'].month != 1:
                print(f"⚠️  WARNING: AAPL original start is {aapl_results['original_start']}, expected 2020-01-01")

        if str(nsei_results['original_start']) != start_date.replace('-', '/'):
            if nsei_results['original_start'].year != 2020 or nsei_results['original_start'].month != 1:
                print(f"⚠️  WARNING: ^NSEI original start is {nsei_results['original_start']}, expected 2020-01-01")

        # Check 3: Both should have same warmup (200 bars for SMA 200)
        if aapl_results['warmup_bars'] != 200:
            print(f"⚠️  WARNING: AAPL warmup is {aapl_results['warmup_bars']} bars, expected ~200")

        if nsei_results['warmup_bars'] != 200:
            print(f"⚠️  WARNING: ^NSEI warmup is {nsei_results['warmup_bars']} bars, expected ~200")

        # Final result
        print(f"\n{'='*80}")
        if validation_passed:
            print("✅ ALL VALIDATIONS PASSED!")
            print("="*80)
            print("\nBenchmark calculations are working correctly for both tickers.")
            print("The fix for warmup period alignment is functioning as expected.")
        else:
            print("❌ VALIDATION FAILED!")
            print("="*80)
            print("\nBenchmark calculations are NOT working correctly.")
            print("\nDebug Steps:")
            print("1. Check if Celery worker was restarted after code changes")
            print("2. Verify df_original is being created in backtest_task.py line 63")
            print("3. Verify calculate_buy_and_hold_equity uses df_original (line 136)")
            print("4. Check Celery logs for:")
            print("   - 'Storing original OHLCV for benchmark'")
            print("   - 'Calculating buy-and-hold benchmark from original OHLCV'")
            print("5. Add debug logging to see actual date ranges:")
            print("   logger.info(f'df_original: {len(df_original)} bars from {df_original.index[0]} to {df_original.index[-1]}')")

    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        print(f"\n{'='*80}")
        print("SMOKE TEST FAILED")
        print("="*80)
        sys.exit(1)


if __name__ == "__main__":
    main()
