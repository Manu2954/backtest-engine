from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.report_generator import (  # noqa: E402
    calculate_buy_and_hold_equity,
    generate_report,
)


def test_benchmark_alignment_with_warmup_trim() -> None:
    """
    Test that benchmark aligns correctly when strategy starts after warmup period.

    This simulates the real scenario:
    1. Fetch OHLCV from Jan 1 to Dec 31 (365 days)
    2. Compute indicators (e.g., SMA 50 needs 50 bars warmup)
    3. Trim warmup period - strategy starts from day 50
    4. Benchmark should also align to start from day 50 for fair comparison
    """
    # Create full dataset (365 days)
    dates = pd.date_range("2023-01-01", periods=365, freq="D")

    # Simulate price going from $100 to $200 (100% return over the year)
    prices = np.linspace(100, 200, 365)

    df_full = pd.DataFrame({
        "open": prices,
        "high": prices * 1.02,
        "low": prices * 0.98,
        "close": prices,
        "volume": [1000000] * 365,
    }, index=dates)

    # Simulate warmup trim: strategy starts from day 50 (after SMA 50 warmup)
    warmup_bars = 50
    df_trimmed = df_full.iloc[warmup_bars:].copy()

    # Strategy equity: let's say it grew from $10000 to $15000 (50% return)
    # Starting from day 50
    strategy_equity = pd.Series(
        np.linspace(10000, 15000, len(df_trimmed)),
        index=df_trimmed.index,
        name="strategy_equity"
    )

    # Calculate benchmark from FULL dataset (before warmup trim)
    # This simulates the fix we just implemented
    initial_capital = 10000.0
    benchmark_equity = calculate_buy_and_hold_equity(df_full, initial_capital, asset_class="STOCK")

    # Minimal trade log
    trades = [
        {
            "entry_date": df_trimmed.index[10],
            "exit_date": df_trimmed.index[100],
            "pnl": 2000,
            "trade_duration_days": 90,
        },
    ]

    # Generate report with benchmark alignment
    report = generate_report(trades, strategy_equity, initial_capital, benchmark_equity=benchmark_equity)

    # Key verification:
    # 1. Strategy return should be calculated correctly (from trimmed start)
    strategy_return = report["total_return_pct"]
    expected_strategy_return = ((15000 - 10000) / 10000) * 100  # 50%
    assert abs(strategy_return - expected_strategy_return) < 0.1, \
        f"Strategy return should be ~50%, got {strategy_return}%"

    # 2. Benchmark return should be calculated from FULL PERIOD (day 1 to day 365)
    #    Price goes from 100 to 200 = 100% return
    #    But with integer shares, we get slightly less due to rounding
    benchmark_return = report.get("benchmark_return_pct", 0)

    # The benchmark should buy at day 1's price
    day_1_price = df_full.iloc[0]["open"]  # 100
    final_price = df_full.iloc[-1]["close"]  # 200
    shares = int(initial_capital / day_1_price)  # Integer shares for STOCK
    expected_benchmark_final = shares * final_price
    expected_benchmark_return = ((expected_benchmark_final - initial_capital) / initial_capital) * 100

    # Allow some tolerance due to rounding
    assert abs(benchmark_return - expected_benchmark_return) < 1.0, \
        f"Benchmark return should be ~{expected_benchmark_return:.1f}% (from day 1), " \
        f"got {benchmark_return:.1f}%"

    # 3. Alpha: Strategy (50%) vs Benchmark (~100%) = negative alpha
    alpha = report.get("alpha", 0)
    expected_alpha = strategy_return - expected_benchmark_return
    assert abs(alpha - expected_alpha) < 1.0, \
        f"Alpha should be ~{expected_alpha:.1f}%, got {alpha:.1f}%"

    print(f"✅ Strategy return (from day 50 warmup start): {strategy_return:.2f}%")
    print(f"✅ Benchmark return (from day 1 actual start): {benchmark_return:.2f}%")
    print(f"✅ Alpha (strategy - benchmark): {alpha:.2f}%")
    print(f"✅ Benchmark correctly calculated from full period!")


def test_benchmark_no_warmup() -> None:
    """
    Test benchmark when there's no warmup period (strategy starts from day 1).
    This verifies backward compatibility.
    """
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    prices = np.linspace(100, 150, 100)

    df = pd.DataFrame({
        "open": prices,
        "high": prices * 1.02,
        "low": prices * 0.98,
        "close": prices,
        "volume": [1000000] * 100,
    }, index=dates)

    initial_capital = 10000.0

    # No warmup trim - full dataset used
    strategy_equity = pd.Series(
        np.linspace(10000, 12000, 100),
        index=df.index,
    )

    benchmark_equity = calculate_buy_and_hold_equity(df, initial_capital, asset_class="STOCK")

    trades = [{"entry_date": dates[10], "exit_date": dates[50], "pnl": 1000, "trade_duration_days": 40}]

    report = generate_report(trades, strategy_equity, initial_capital, benchmark_equity=benchmark_equity)

    # Both should start from day 1, so returns are comparable
    assert "benchmark_return_pct" in report
    assert "alpha" in report

    print(f"✅ No warmup scenario: Strategy {report['total_return_pct']:.2f}%, "
          f"Benchmark {report['benchmark_return_pct']:.2f}%")
