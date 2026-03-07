"""
Smoke test for Buy-and-Hold Benchmark Comparison.

Tests:
1. Calculate buy-and-hold equity
2. Benchmark statistics calculation
3. Alpha calculation (strategy vs benchmark)
4. Beta calculation (correlation)
5. Full integration test
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.report_generator import (  # noqa: E402
    calculate_buy_and_hold_equity,
    generate_report,
)
from app.engine.data_layer import fetch_ohlcv  # noqa: E402
from app.engine.indicator_layer import compute_indicators, trim_warmup_period  # noqa: E402
from app.engine.condition_engine import evaluate_conditions  # noqa: E402
from app.engine.state_machine import run_backtest  # noqa: E402


def test_buy_and_hold_calculation():
    """Test buy-and-hold equity calculation."""
    print("\n" + "="*80)
    print("TEST 1: Buy-and-Hold Equity Calculation")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    df = pd.DataFrame({
        "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        "high": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
        "low": [98, 99, 100, 101, 102, 103, 104, 105, 106, 107],
        "close": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        "volume": [1000000] * 10,
    }, index=dates)

    initial_capital = 10000.0

    # Calculate buy-and-hold for stocks (integer shares)
    benchmark_equity = calculate_buy_and_hold_equity(df, initial_capital, asset_class="STOCK")

    print(f"Initial capital: ${initial_capital}")
    print(f"Entry price (first open): ${df.iloc[0]['open']}")
    print(f"Shares bought: {initial_capital / df.iloc[0]['open']:.0f}")
    print(f"First equity: ${benchmark_equity.iloc[0]:.2f}")
    print(f"Last equity: ${benchmark_equity.iloc[-1]:.2f}")
    print(f"Benchmark return: {((benchmark_equity.iloc[-1] - initial_capital) / initial_capital * 100):.2f}%")

    # Verify equity grows with price
    assert benchmark_equity.iloc[-1] > benchmark_equity.iloc[0], "Benchmark should grow with price"
    assert len(benchmark_equity) == len(df), "Benchmark should have same length as data"

    print("\n✅ TEST 1 PASSED\n")


def test_benchmark_with_declining_price():
    """Test buy-and-hold when price declines."""
    print("\n" + "="*80)
    print("TEST 2: Buy-and-Hold with Declining Price")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    df = pd.DataFrame({
        "open": [110, 109, 108, 107, 106, 105, 104, 103, 102, 101],
        "high": [112, 111, 110, 109, 108, 107, 106, 105, 104, 103],
        "low": [108, 107, 106, 105, 104, 103, 102, 101, 100, 99],
        "close": [109, 108, 107, 106, 105, 104, 103, 102, 101, 100],
        "volume": [1000000] * 10,
    }, index=dates)

    initial_capital = 10000.0
    benchmark_equity = calculate_buy_and_hold_equity(df, initial_capital, asset_class="STOCK")

    print(f"Initial capital: ${initial_capital}")
    print(f"Final equity: ${benchmark_equity.iloc[-1]:.2f}")
    print(f"Benchmark return: {((benchmark_equity.iloc[-1] - initial_capital) / initial_capital * 100):.2f}%")

    # Verify equity declines with price
    assert benchmark_equity.iloc[-1] < benchmark_equity.iloc[0], "Benchmark should decline with price"

    print("\n✅ TEST 2 PASSED\n")


def test_benchmark_statistics():
    """Test benchmark statistics calculation."""
    print("\n" + "="*80)
    print("TEST 3: Benchmark Statistics")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=100, freq="D")

    # Create strategy equity that outperforms
    strategy_equity = pd.Series(
        np.linspace(10000, 15000, 100),  # 50% return
        index=dates,
        name="strategy_equity"
    )

    # Create benchmark equity
    benchmark_equity = pd.Series(
        np.linspace(10000, 13000, 100),  # 30% return
        index=dates,
        name="benchmark_equity"
    )

    # Generate minimal trade log
    trades = [
        {
            "entry_date": dates[10],
            "exit_date": dates[50],
            "pnl": 2000,
            "trade_duration_days": 40,
        },
        {
            "entry_date": dates[60],
            "exit_date": dates[90],
            "pnl": 3000,
            "trade_duration_days": 30,
        },
    ]

    report = generate_report(trades, strategy_equity, 10000.0, benchmark_equity=benchmark_equity)

    print(f"Strategy Return: {report['total_return_pct']:.2f}%")
    print(f"Benchmark Return: {report.get('benchmark_return_pct', 0):.2f}%")
    print(f"Alpha: {report.get('alpha', 0):.2f}%")
    print(f"Beta: {report.get('beta', 0):.4f}")
    print(f"Strategy Sharpe: {report['sharpe_ratio']:.4f}")
    print(f"Benchmark Sharpe: {report.get('benchmark_sharpe_ratio', 0):.4f}")

    # Verify alpha is positive (strategy beat benchmark)
    assert report.get('alpha', 0) > 0, "Alpha should be positive when strategy outperforms"
    assert 'benchmark_return_pct' in report, "Should have benchmark return"
    assert 'beta' in report, "Should have beta"

    print("\n✅ TEST 3 PASSED\n")


def test_negative_alpha():
    """Test when strategy underperforms benchmark (negative alpha)."""
    print("\n" + "="*80)
    print("TEST 4: Negative Alpha (Strategy Underperforms)")
    print("="*80)

    dates = pd.date_range("2023-01-01", periods=100, freq="D")

    # Strategy underperforms
    strategy_equity = pd.Series(
        np.linspace(10000, 11000, 100),  # 10% return
        index=dates,
    )

    # Benchmark outperforms
    benchmark_equity = pd.Series(
        np.linspace(10000, 13000, 100),  # 30% return
        index=dates,
    )

    trades = [{"entry_date": dates[10], "exit_date": dates[50], "pnl": 1000, "trade_duration_days": 40}]

    report = generate_report(trades, strategy_equity, 10000.0, benchmark_equity=benchmark_equity)

    print(f"Strategy Return: {report['total_return_pct']:.2f}%")
    print(f"Benchmark Return: {report.get('benchmark_return_pct', 0):.2f}%")
    print(f"Alpha: {report.get('alpha', 0):.2f}%")

    # Verify alpha is negative
    assert report.get('alpha', 0) < 0, "Alpha should be negative when strategy underperforms"
    print(f"\n❌ Strategy underperformed by {abs(report.get('alpha', 0)):.2f}%")

    print("\n✅ TEST 4 PASSED\n")


def test_real_backtest_with_benchmark():
    """Test full backtest with benchmark comparison."""
    print("\n" + "="*80)
    print("TEST 5: Full Integration (Real Backtest + Benchmark)")
    print("="*80)

    ticker = "AAPL"
    start = "2023-01-01"
    end = "2023-12-31"
    initial_capital = 10000.0

    df = fetch_ohlcv(ticker, start, end, "1d", "STOCK")

    indicators = [
        {"indicator_type": "SMA", "alias": "sma_20", "params": {"period": 20, "source": "close"}},
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)
    df, warmup_bars = trim_warmup_period(df)

    print(f"Data fetched: {len(df) + warmup_bars} bars, after warmup: {len(df)} bars")

    entry_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_20",
                "operator": "CROSSES_ABOVE",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_50",
            }
        ],
    }

    exit_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_20",
                "operator": "CROSSES_BELOW",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_50",
            }
        ],
    }

    entry_signal = evaluate_conditions(df, entry_group)
    exit_signal = evaluate_conditions(df, exit_group)

    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
    )

    # Calculate benchmark
    benchmark_equity = calculate_buy_and_hold_equity(df, initial_capital, asset_class="STOCK")

    # Generate report with benchmark
    report = generate_report(trades, equity_curve, initial_capital, benchmark_equity=benchmark_equity)

    print("\n" + "-"*80)
    print("RESULTS COMPARISON")
    print("-"*80)
    print(f"{'Strategy':<30} {'Benchmark':<30} {'Difference':<20}")
    print("-"*80)

    strategy_return = report['total_return_pct']
    benchmark_return = report.get('benchmark_return_pct', 0)
    print(f"{'Total Return:':<30} {strategy_return:>10.2f}%  {benchmark_return:>17.2f}%  {report.get('alpha', 0):>17.2f}%")

    print(f"{'Final Capital:':<30} ${report['final_capital']:>10.2f}  ${report.get('benchmark_final_capital', 0):>17.2f}")

    strategy_sharpe = report['sharpe_ratio']
    benchmark_sharpe = report.get('benchmark_sharpe_ratio', 0)
    print(f"{'Sharpe Ratio:':<30} {strategy_sharpe:>10.4f}  {benchmark_sharpe:>17.4f}")

    strategy_dd = report['max_drawdown_pct']
    benchmark_dd = report.get('benchmark_max_drawdown_pct', 0)
    print(f"{'Max Drawdown:':<30} {strategy_dd:>10.2f}%  {benchmark_dd:>17.2f}%")

    print(f"\n{'Alpha (Excess Return):':<30} {report.get('alpha', 0):>10.2f}%")
    print(f"{'Beta (Market Correlation):':<30} {report.get('beta', 0):>10.4f}")
    print(f"{'Total Trades:':<30} {report['total_trades']:>10d}")

    # Verify all benchmark stats are present
    assert 'benchmark_return_pct' in report, "Should have benchmark return"
    assert 'alpha' in report, "Should have alpha"
    assert 'beta' in report, "Should have beta"
    assert 'benchmark_sharpe_ratio' in report, "Should have benchmark Sharpe"

    # Determine if strategy beat benchmark
    if report.get('alpha', 0) > 0:
        print(f"\n✅ Strategy BEAT buy-and-hold by {report.get('alpha', 0):.2f}%")
    else:
        print(f"\n❌ Strategy UNDERPERFORMED buy-and-hold by {abs(report.get('alpha', 0)):.2f}%")

    print("\n✅ TEST 5 PASSED\n")


def main() -> None:
    print("\n" + "="*80)
    print("SMOKE TEST: Buy-and-Hold Benchmark Comparison")
    print("="*80)

    try:
        test_buy_and_hold_calculation()
        test_benchmark_with_declining_price()
        test_benchmark_statistics()
        test_negative_alpha()
        test_real_backtest_with_benchmark()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nBenchmark Comparison Coverage:")
        print("  ✓ Buy-and-hold equity calculation")
        print("  ✓ Rising and declining prices")
        print("  ✓ Benchmark statistics (return, Sharpe, drawdown)")
        print("  ✓ Alpha calculation (positive and negative)")
        print("  ✓ Beta calculation (market correlation)")
        print("  ✓ Full integration with real backtest")
        print("\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
