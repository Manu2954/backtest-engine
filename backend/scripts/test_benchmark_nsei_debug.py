"""
Debug smoke test for ^NSEI benchmark issue with actual service layer calls.

This test runs a real backtest with indicators requiring warmup and compares
benchmark results between AAPL and ^NSEI to identify the issue.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.models.strategy import Strategy, Indicator, ConditionGroup, Condition
from app.models.backtest import BacktestRun
from app.tasks.backtest_task import _run_backtest_async


async def create_test_strategy(ticker_name: str) -> str:
    """
    Create a simple SMA crossover strategy for testing.

    Returns:
        Strategy ID
    """
    async with get_session() as session:
        # Create strategy
        strategy = Strategy(
            name=f"SMA Crossover Test - {ticker_name}",
            description="Simple SMA 20/50 crossover for benchmark testing",
            user_id=None,
        )
        session.add(strategy)
        await session.flush()

        # Add indicators (SMA 20 and SMA 50 - requires 50 bar warmup)
        ind1 = Indicator(
            strategy_id=strategy.id,
            indicator_type="SMA",
            alias="sma_20",
            params={"period": 20, "source": "close"},
        )
        ind2 = Indicator(
            strategy_id=strategy.id,
            indicator_type="SMA",
            alias="sma_50",
            params={"period": 50, "source": "close"},
        )
        session.add_all([ind1, ind2])

        # Entry conditions: SMA 20 crosses above SMA 50
        entry_group = ConditionGroup(
            strategy_id=strategy.id,
            group_type="ENTRY",
            logic="AND",
        )
        session.add(entry_group)
        await session.flush()

        entry_condition = Condition(
            group_id=entry_group.id,
            left_operand_type="INDICATOR",
            left_operand_value="sma_20",
            operator="CROSSES_ABOVE",
            right_operand_type="INDICATOR",
            right_operand_value="sma_50",
        )
        session.add(entry_condition)

        # Exit conditions: SMA 20 crosses below SMA 50
        exit_group = ConditionGroup(
            strategy_id=strategy.id,
            group_type="EXIT",
            logic="AND",
        )
        session.add(exit_group)
        await session.flush()

        exit_condition = Condition(
            group_id=exit_group.id,
            left_operand_type="INDICATOR",
            left_operand_value="sma_20",
            operator="CROSSES_BELOW",
            right_operand_type="INDICATOR",
            right_operand_value="sma_50",
        )
        session.add(exit_condition)

        await session.commit()
        return str(strategy.id)


async def create_backtest_run(
    strategy_id: str,
    ticker: str,
    start_date: date,
    end_date: date,
) -> str:
    """
    Create a backtest run entry.

    Returns:
        Backtest run ID
    """
    async with get_session() as session:
        run = BacktestRun(
            strategy_id=strategy_id,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10000.0,
            bar_resolution="1d",
            asset_class="STOCK",
            status="PENDING",
        )
        session.add(run)
        await session.commit()
        return str(run.id)


async def get_backtest_results(run_id: str) -> dict:
    """Get backtest results from database."""
    async with get_session() as session:
        run = await session.get(BacktestRun, run_id)
        if run is None:
            raise ValueError(f"Backtest run {run_id} not found")

        return {
            "status": run.status,
            "error_message": run.error_message,
            "report": run.report,
        }


async def run_benchmark_debug_test():
    """
    Main test function - runs backtests for both AAPL and ^NSEI
    and compares benchmark results.
    """
    print("\n" + "=" * 80)
    print("BENCHMARK DEBUG TEST: AAPL vs ^NSEI")
    print("=" * 80)

    # Test configuration - SAME dates for both tickers
    start_date = date(2020, 1, 1)
    end_date = date(2023, 12, 31)

    print(f"\nTest Configuration:")
    print(f"  Date Range: {start_date} to {end_date}")
    print(f"  Strategy: SMA 20/50 crossover (requires 50-bar warmup)")
    print(f"  Initial Capital: $10,000")
    print(f"  Asset Class: STOCK")

    # Test 1: AAPL
    print("\n" + "-" * 80)
    print("TEST 1: AAPL Backtest")
    print("-" * 80)

    try:
        print("Creating strategy for AAPL...")
        aapl_strategy_id = await create_test_strategy("AAPL")
        print(f"✅ Strategy created: {aapl_strategy_id}")

        print("Creating backtest run for AAPL...")
        aapl_run_id = await create_backtest_run(
            aapl_strategy_id, "AAPL", start_date, end_date
        )
        print(f"✅ Backtest run created: {aapl_run_id}")

        print("Running backtest for AAPL...")
        await _run_backtest_async(aapl_run_id)

        print("Fetching results for AAPL...")
        aapl_results = await get_backtest_results(aapl_run_id)

        if aapl_results["status"] != "COMPLETE":
            print(f"❌ AAPL backtest failed: {aapl_results['error_message']}")
            return

        aapl_report = aapl_results["report"]
        print(f"✅ AAPL backtest completed successfully")
        print(f"\nAAPL Results:")
        print(f"  Strategy Return: {aapl_report.get('total_return_pct', 0):.2f}%")
        print(f"  Strategy Final: ${aapl_report.get('final_capital', 0):.2f}")
        print(f"  Benchmark Return: {aapl_report.get('benchmark_return_pct', 0):.2f}%")
        print(f"  Benchmark Final: ${aapl_report.get('benchmark_final_capital', 0):.2f}")
        print(f"  Alpha: {aapl_report.get('alpha', 0):.2f}%")
        print(f"  Total Trades: {aapl_report.get('total_trades', 0)}")

    except Exception as e:
        print(f"❌ AAPL test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 2: ^NSEI
    print("\n" + "-" * 80)
    print("TEST 2: ^NSEI Backtest")
    print("-" * 80)

    try:
        print("Creating strategy for ^NSEI...")
        nsei_strategy_id = await create_test_strategy("^NSEI")
        print(f"✅ Strategy created: {nsei_strategy_id}")

        print("Creating backtest run for ^NSEI...")
        nsei_run_id = await create_backtest_run(
            nsei_strategy_id, "^NSEI", start_date, end_date
        )
        print(f"✅ Backtest run created: {nsei_run_id}")

        print("Running backtest for ^NSEI...")
        await _run_backtest_async(nsei_run_id)

        print("Fetching results for ^NSEI...")
        nsei_results = await get_backtest_results(nsei_run_id)

        if nsei_results["status"] != "COMPLETE":
            print(f"❌ ^NSEI backtest failed: {nsei_results['error_message']}")
            return

        nsei_report = nsei_results["report"]
        print(f"✅ ^NSEI backtest completed successfully")
        print(f"\n^NSEI Results:")
        print(f"  Strategy Return: {nsei_report.get('total_return_pct', 0):.2f}%")
        print(f"  Strategy Final: ${nsei_report.get('final_capital', 0):.2f}")
        print(f"  Benchmark Return: {nsei_report.get('benchmark_return_pct', 0):.2f}%")
        print(f"  Benchmark Final: ${nsei_report.get('benchmark_final_capital', 0):.2f}")
        print(f"  Alpha: {nsei_report.get('alpha', 0):.2f}%")
        print(f"  Total Trades: {nsei_report.get('total_trades', 0)}")

    except Exception as e:
        print(f"❌ ^NSEI test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return

    # Compare results
    print("\n" + "=" * 80)
    print("COMPARISON: AAPL vs ^NSEI")
    print("=" * 80)

    print(f"\n{'Metric':<30} {'AAPL':<20} {'^NSEI':<20}")
    print("-" * 70)
    print(f"{'Benchmark Return:':<30} {aapl_report.get('benchmark_return_pct', 0):>18.2f}%  {nsei_report.get('benchmark_return_pct', 0):>18.2f}%")
    print(f"{'Benchmark Final Capital:':<30} ${aapl_report.get('benchmark_final_capital', 0):>17.2f}  ${nsei_report.get('benchmark_final_capital', 0):>17.2f}")
    print(f"{'Strategy Return:':<30} {aapl_report.get('total_return_pct', 0):>18.2f}%  {nsei_report.get('total_return_pct', 0):>18.2f}%")
    print(f"{'Alpha:':<30} {aapl_report.get('alpha', 0):>18.2f}%  {nsei_report.get('alpha', 0):>18.2f}%")

    # Analysis
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    aapl_benchmark = aapl_report.get('benchmark_return_pct', 0)
    nsei_benchmark = nsei_report.get('benchmark_return_pct', 0)

    print(f"\nBenchmark Returns:")
    print(f"  AAPL: {aapl_benchmark:.2f}%")
    print(f"  ^NSEI: {nsei_benchmark:.2f}%")

    if abs(aapl_benchmark) < 0.01 and abs(nsei_benchmark) < 0.01:
        print("\n⚠️  WARNING: Both benchmarks show ~0% return!")
        print("   This suggests the benchmark is not being calculated correctly.")
        print("   Expected: Significant returns over 4-year period for both.")
    elif abs(nsei_benchmark) < 0.01:
        print("\n❌ ISSUE CONFIRMED: ^NSEI benchmark shows ~0% return!")
        print("   AAPL shows normal returns, but ^NSEI doesn't.")
        print("   This confirms the bug exists.")
    else:
        print("\n✅ Both benchmarks show reasonable returns.")
        print("   The issue may have been fixed!")

    print("\nExpected Behavior:")
    print("  - Both AAPL and ^NSEI should show their actual historical returns")
    print("  - Benchmark should represent buy-and-hold from Jan 1, 2020 to Dec 31, 2023")
    print("  - Benchmark return should reflect the full 4-year period")

    print("\nDebug Information:")
    print("  If benchmarks are wrong, check:")
    print("  1. Is df_original being created correctly in backtest_task.py?")
    print("  2. Is calculate_buy_and_hold_equity using df_original (not df)?")
    print("  3. Is the date range in df_original correct (start to end)?")
    print("  4. Add logging to see actual data ranges:")
    print("     logger.info(f'df_original range: {df_original.index[0]} to {df_original.index[-1]}')")
    print("     logger.info(f'df_original length: {len(df_original)} bars')")
    print("     logger.info(f'df (trimmed) range: {df.index[0]} to {df.index[-1]}')")
    print("     logger.info(f'df (trimmed) length: {len(df)} bars')")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


def main():
    """Entry point."""
    asyncio.run(run_benchmark_debug_test())


if __name__ == "__main__":
    main()
