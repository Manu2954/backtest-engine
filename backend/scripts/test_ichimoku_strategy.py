"""
Ichimoku Cloud Strategy Test

LONG ENTRY — all required:
□ Price close > Span A and Span B
□ Future cloud is bullish (Span A > Span B, 26 periods forward)
□ Tenkan crosses above Kijun on current candle close
□ Cross occurs above the cloud
□ Chikou Span > price from 26 periods back

ENTER: Next candle open

STOP: Below Kijun-sen (or cloud base if wider)

EXIT — first of these:
□ Daily close below Kijun-sen → exit next open
□ Tenkan crosses below Kijun → exit on close

NO partial exits. NO profit targets. Ride until exit triggers.

================================================================================
CONDITION ENGINE vs MANUAL FILTERS
================================================================================

The condition engine supports:
✅ GT, LT, EQ, GTE, LTE - Simple comparisons
✅ CROSSES_ABOVE, CROSSES_BELOW - Crossover detection
✅ IS_RISING, IS_FALLING - Direction detection
✅ AND, OR logic between conditions

Manual filters needed when:
❌ .shift() operations - Comparing to past/future values (e.g., close.shift(26))
❌ .rolling() operations - Moving window calculations
❌ Complex calculations - Multiple steps, custom formulas
❌ Lookback/lookahead - Accessing values from different time periods

In this Ichimoku strategy:
✅ 6 conditions in condition engine (price vs cloud, crossovers, cloud color)
❌ 1 manual filter (Chikou vs shifted price - requires .shift(26))

Rule of thumb: If it can be expressed as "A operator B" where A and B are
columns/scalars and operator is comparison/cross/direction, use condition engine.
If it requires pandas operations like .shift(), .rolling(), .rank(), etc.,
use manual filters.
================================================================================
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
from app.engine.report_generator import generate_report, calculate_buy_and_hold_equity  # noqa: E402


def test_ichimoku_strategy():
    """Test Ichimoku Cloud strategy with all entry/exit rules."""
    print("\n" + "="*80)
    print("ICHIMOKU CLOUD STRATEGY TEST")
    print("="*80)

    ticker = "AAPL"
    start = "2010-01-01"
    end = "2023-12-31"
    initial_capital = 10000.0

    print(f"\nFetching {ticker} data from {start} to {end}...")
    df = fetch_ohlcv(ticker, start, end, "1d", "STOCK")
    print(f"Fetched {len(df)} bars")

    # Compute Ichimoku Cloud with standard settings
    indicators = [
        {
            "indicator_type": "ICHIMOKU",
            "alias": "ichimoku",
            "params": {
                "tenkan": 9,   # Conversion Line (Tenkan-sen)
                "kijun": 26,   # Base Line (Kijun-sen)
                "senkou": 52,  # Leading Span B lookback
            }
        },
    ]

    df = compute_indicators(df, indicators)

    print(f"\nIchimoku columns added:")
    print(f"  - ichimoku_tenkan (Conversion Line)")
    print(f"  - ichimoku_kijun (Base Line)")
    print(f"  - ichimoku_span_a (Leading Span A)")
    print(f"  - ichimoku_span_b (Leading Span B)")
    print(f"  - ichimoku_chikou (Lagging Span)")

    df, warmup_bars = trim_warmup_period(df)
    print(f"\nAfter warmup: {len(df)} bars (trimmed {warmup_bars} bars)")

    # ========================================================================
    # ENTRY CONDITIONS (AND logic - all must be true)
    # ========================================================================
    print("\n" + "-"*80)
    print("ENTRY CONDITIONS (All Required)")
    print("-"*80)
    print("1. Price close > Span A AND Price close > Span B")
    print("2. Tenkan crosses above Kijun on current candle close")
    print("3. Cross occurs above the cloud (Tenkan > Span A AND Tenkan > Span B)")
    print("4. Future cloud is bullish (Span A > Span B)")
    print("5. Chikou Span > price from 26 periods back (manual filter)")

    # Entry conditions
    entry_group = {
        "logic": "AND",
        "conditions": [
            # Condition 1a: Price close > Span A
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "ichimoku_span_a",
            },
            # Condition 1b: Price close > Span B
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "ichimoku_span_b",
            },
            # Condition 2: Tenkan crosses above Kijun
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "ichimoku_tenkan",
                "operator": "CROSSES_ABOVE",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "ichimoku_kijun",
            },
            # Condition 3a: Cross occurs above cloud - Tenkan > Span A
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "ichimoku_tenkan",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "ichimoku_span_a",
            },
            # Condition 3b: Cross occurs above cloud - Tenkan > Span B
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "ichimoku_tenkan",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "ichimoku_span_b",
            },
            # Condition 4: Future cloud is bullish (Span A > Span B)
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "ichimoku_span_a",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "ichimoku_span_b",
            },
        ],
    }

    entry_signal = evaluate_conditions(df, entry_group)

    # Additional entry filter that CANNOT be in condition engine:
    # Reason: Requires .shift() operation which condition engine doesn't support
    # Chikou Span > price from 26 periods back
    df['chikou_above_price'] = df['ichimoku_chikou'] > df['close'].shift(26)

    # Apply manual filter
    entry_signal = entry_signal & df['chikou_above_price'].fillna(False)

    print(f"\nEntry signals generated: {entry_signal.sum()}")

    # ========================================================================
    # EXIT CONDITIONS (OR logic - exit on first trigger)
    # ========================================================================
    print("\n" + "-"*80)
    print("EXIT CONDITIONS (First Trigger)")
    print("-"*80)
    print("1. Daily close below Kijun-sen")
    print("2. Tenkan crosses below Kijun")

    exit_group = {
        "logic": "OR",
        "conditions": [
            # Exit 1: Close below Kijun-sen
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "LT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "ichimoku_kijun",
            },
            # Exit 2: Tenkan crosses below Kijun
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "ichimoku_tenkan",
                "operator": "CROSSES_BELOW",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "ichimoku_kijun",
            },
        ],
    }

    exit_signal = evaluate_conditions(df, exit_group)
    print(f"Exit signals generated: {exit_signal.sum()}")

    # ========================================================================
    # CALCULATE DYNAMIC STOP LOSS
    # ========================================================================
    print("\n" + "-"*80)
    print("STOP LOSS: Below Kijun-sen (dynamic)")
    print("-"*80)
    print("Using dynamic stop loss based on Kijun-sen")
    print("Exit if price drops below Kijun-sen at any bar")

    # ========================================================================
    # RUN BACKTEST
    # ========================================================================
    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        position_size_type="percent_capital",
        position_size_value=100.0,  # Full capital per trade (no pyramiding)
        dynamic_stop_column="ichimoku_kijun",  # Use Kijun-sen as dynamic stop
        commission_pct=0.1,
        slippage_pct=0.05,
    )

    # Calculate benchmark
    benchmark_equity = calculate_buy_and_hold_equity(df, initial_capital, asset_class="STOCK")

    # Generate report
    report = generate_report(trades, equity_curve, initial_capital, benchmark_equity=benchmark_equity)

    # ========================================================================
    # DISPLAY RESULTS
    # ========================================================================
    print("\n" + "="*80)
    print("ICHIMOKU STRATEGY PERFORMANCE")
    print("="*80)
    print(f"Total Trades: {report['total_trades']}")

    if report['total_trades'] > 0:
        print(f"Win Rate: {report.get('win_rate', 0):.2f}%")
        print(f"Profit Factor: {report.get('profit_factor', 0):.2f}")
        print(f"\nTotal Return: {report['total_return_pct']:.2f}%")
        print(f"Final Capital: ${report['final_capital']:,.2f}")
        print(f"CAGR: {report.get('cagr', 0):.2f}%")
        print(f"Max Drawdown: {report['max_drawdown_pct']:.2f}%")
        print(f"Sharpe Ratio: {report['sharpe_ratio']:.4f}")
        print(f"\nAvg Win: ${report.get('avg_win', 0):.2f}")
        print(f"Avg Loss: ${report.get('avg_loss', 0):.2f}")
        print(f"Largest Win: ${report.get('largest_win', 0):.2f}")
        print(f"Largest Loss: ${report.get('largest_loss', 0):.2f}")
        print(f"Avg Trade Duration: {report.get('avg_trade_duration_days', 0):.1f} days")
    else:
        print("\n⚠️  No trades executed")
        print(f"Total Return: {report['total_return_pct']:.2f}%")
        print(f"Final Capital: ${report['final_capital']:,.2f}")

    print("\n" + "="*80)
    print("BENCHMARK COMPARISON")
    print("="*80)
    print(f"{'Metric':<30} {'Strategy':<15} {'Buy & Hold':<15} {'Alpha':<15}")
    print("-"*80)
    print(f"{'Total Return':<30} {report['total_return_pct']:>10.2f}%  {report['benchmark_return_pct']:>12.2f}%  {report['alpha']:>12.2f}%")
    print(f"{'Sharpe Ratio':<30} {report['sharpe_ratio']:>10.4f}  {report['benchmark_sharpe_ratio']:>12.4f}")
    print(f"{'Max Drawdown':<30} {report['max_drawdown_pct']:>10.2f}%  {report['benchmark_max_drawdown_pct']:>12.2f}%")
    print(f"{'Beta (Correlation)':<30} {report['beta']:>10.4f}")

    if report.get('alpha', 0) > 0:
        print(f"\n✅ Strategy BEAT buy-and-hold by {report['alpha']:.2f}%")
    else:
        print(f"\n⚠️  Strategy UNDERPERFORMED buy-and-hold by {abs(report['alpha']):.2f}%")

    # ========================================================================
    # ANALYZE EXIT REASONS
    # ========================================================================
    if report['total_trades'] > 0:
        print("\n" + "="*80)
        print("EXIT REASON BREAKDOWN")
        print("="*80)

        exit_reasons = {}
        for trade in trades:
            reason = trade.get('exit_reason', 'signal')
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        for reason, count in sorted(exit_reasons.items(), key=lambda x: x[1], reverse=True):
            pct = (count / len(trades)) * 100
            reason_label = {
                'signal': 'Exit Signal (Close < Kijun or Tenkan x Kijun)',
                'stop_loss': 'Dynamic Stop with Loss',
                'trailing_stop': 'Dynamic Stop with Profit (Trailing)',
                'take_profit': 'Take Profit (N/A for Ichimoku)',
                'force_close': 'Force Close at End',
            }.get(reason, reason)
            print(f"{reason_label:<50} {count:>5} trades ({pct:>5.1f}%)")

        print("\n" + "="*80)
        print("SAMPLE TRADES (First 5)")
        print("="*80)

        for i, trade in enumerate(trades[:5], 1):
            print(f"\nTrade #{i}:")
            print(f"  Entry: {trade['entry_date'].date()} @ ${trade['entry_price']:.2f}")
            print(f"  Exit:  {trade['exit_date'].date()} @ ${trade['exit_price']:.2f}")
            print(f"  Shares: {trade['shares']:.2f}")
            print(f"  P&L: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")
            print(f"  Commissions: ${trade.get('total_commission', 0):.2f}")
            print(f"  Exit Reason: {trade.get('exit_reason', 'signal')}")
            print(f"  Duration: {trade['trade_duration_days']} days")

    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)
    print("\nIchimoku Strategy Implementation:")
    print("  ✓ All 5 Ichimoku lines computed")
    print("  ✓ Entry: Price above cloud + Tenkan crosses Kijun + filters")
    print("  ✓ Exit: Close below Kijun OR Tenkan crosses below Kijun")
    print("  ✓ Stop loss: Dynamic Kijun-based (price < Kijun)")
    print("  ✓ No profit targets (ride the trend)")
    print("\nNote: Dynamic Kijun-sen stop implemented!")
    print("      Exit triggers when price drops below current Kijun value\n")


def main() -> None:
    try:
        test_ichimoku_strategy()
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
