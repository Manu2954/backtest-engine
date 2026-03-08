#!/usr/bin/env python3
"""
Demonstration: LOOKBACK Operand Type (V2 Feature)

Shows how to use the new LOOKBACK operand for historical comparisons.
This enables checking if indicators are rising/falling over N periods.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv
from app.engine.indicator_layer import compute_indicators, trim_warmup_period
from app.engine.condition_engine import evaluate_conditions
from app.engine.state_machine import run_backtest


def demo_lookback_feature():
    """Demonstrate LOOKBACK feature with real examples."""

    print("="*70)
    print("  LOOKBACK OPERAND TYPE - DEMONSTRATION")
    print("="*70)

    # Fetch data
    print("\n1. Fetching SPY data...")
    df = fetch_ohlcv("SPY", "2023-01-01", "2024-01-01", "1d", "STOCK")
    print(f"   Fetched {len(df)} bars")

    # Compute indicators
    print("\n2. Computing indicators...")
    indicators = [
        {"indicator_type": "ADX", "alias": "adx", "params": {"period": 14}},
        {"indicator_type": "RSI", "alias": "rsi", "params": {"period": 14, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)
    df, warmup = trim_warmup_period(df)
    print(f"   After warmup: {len(df)} bars")

    # Example 1: ADX Rising (ADX > ADX from 3 bars ago)
    print("\n" + "-"*70)
    print("Example 1: ADX Rising Over 3 Bars")
    print("-"*70)

    condition_adx_rising = {
        "logic": "AND",
        "conditions": [{
            "left_operand_type": "INDICATOR",
            "left_operand_value": "adx",
            "operator": "GT",
            "right_operand_type": "LOOKBACK",
            "right_operand_value": "adx:-3"  # 3 bars ago
        }]
    }

    result = evaluate_conditions(df, condition_adx_rising)
    print(f"✓ ADX rising signals: {result.sum()} / {len(df)} bars")
    print(f"  Format: 'adx:-3' means ADX from 3 bars ago")
    print(f"  Logic: current ADX > ADX[-3]")

    # Example 2: RSI Falling (RSI < RSI from 5 bars ago)
    print("\n" + "-"*70)
    print("Example 2: RSI Falling Over 5 Bars")
    print("-"*70)

    condition_rsi_falling = {
        "logic": "AND",
        "conditions": [{
            "left_operand_type": "INDICATOR",
            "left_operand_value": "rsi",
            "operator": "LT",
            "right_operand_type": "LOOKBACK",
            "right_operand_value": "rsi:-5"  # 5 bars ago
        }]
    }

    result = evaluate_conditions(df, condition_rsi_falling)
    print(f"✓ RSI falling signals: {result.sum()} / {len(df)} bars")
    print(f"  Format: 'rsi:-5' means RSI from 5 bars ago")
    print(f"  Logic: current RSI < RSI[-5]")

    # Example 3: Price Momentum (Close > Close from 10 bars ago)
    print("\n" + "-"*70)
    print("Example 3: Price Momentum (10-bar uptrend)")
    print("-"*70)

    condition_price_momentum = {
        "logic": "AND",
        "conditions": [{
            "left_operand_type": "OHLCV",
            "left_operand_value": "close",
            "operator": "GT",
            "right_operand_type": "LOOKBACK",
            "right_operand_value": "close:-10"  # 10 bars ago
        }]
    }

    result = evaluate_conditions(df, condition_price_momentum)
    print(f"✓ Uptrend signals: {result.sum()} / {len(df)} bars")
    print(f"  Format: 'close:-10' means close from 10 bars ago")
    print(f"  Logic: current close > close[-10]")

    # Example 4: Combined Conditions (ADX rising AND Price momentum)
    print("\n" + "-"*70)
    print("Example 4: Combined - ADX Rising + Price Momentum")
    print("-"*70)

    condition_combined = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "adx",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "adx:-3"
            },
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "close:-10"
            }
        ]
    }

    result = evaluate_conditions(df, condition_combined)
    print(f"✓ Combined signals: {result.sum()} / {len(df)} bars")
    print(f"  Both conditions must be true")

    # Example 5: Run a simple backtest with LOOKBACK
    print("\n" + "-"*70)
    print("Example 5: Backtest with LOOKBACK Entry Condition")
    print("-"*70)

    # Entry: ADX rising + Close > SMA
    df = compute_indicators(df, [
        {"indicator_type": "SMA", "alias": "sma_20", "params": {"period": 20, "source": "close"}}
    ])

    entry_conditions = {
        "logic": "AND",
        "conditions": [
            # ADX rising
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "adx",
                "operator": "GT",
                "right_operand_type": "LOOKBACK",
                "right_operand_value": "adx:-3"
            },
            # Price above SMA
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_20"
            }
        ]
    }

    exit_conditions = {
        "logic": "OR",
        "conditions": [
            # Close below SMA
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "LT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_20"
            }
        ]
    }

    entry_signal = evaluate_conditions(df, entry_conditions)
    exit_signal = evaluate_conditions(df, exit_conditions)

    print(f"Entry signals: {entry_signal.sum()}")
    print(f"Exit signals: {exit_signal.sum()}")

    trades, equity = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=10000.0,
        asset_class="STOCK",
        position_size_type="full_capital"
    )

    print(f"\n✓ Backtest Results:")
    print(f"  Trades: {len(trades)}")
    if len(trades) > 0:
        winning = [t for t in trades if t['pnl'] > 0]
        print(f"  Win rate: {len(winning)/len(trades)*100:.1f}%")
        print(f"  Final equity: ${equity.iloc[-1]:,.2f}")

    # Summary
    print("\n" + "="*70)
    print("  LOOKBACK FEATURE SUMMARY")
    print("="*70)
    print("\nFormat: 'column:offset'")
    print("  - Negative offset: lookback (e.g., '-3' = 3 bars ago)")
    print("  - Positive offset: lookahead (e.g., '+26' = 26 bars ahead)")
    print("\nWorks with:")
    print("  ✓ Any indicator (ADX, RSI, SMA, MACD, etc.)")
    print("  ✓ Any OHLCV column (close, open, high, low, volume)")
    print("  ✓ All operators (GT, LT, CROSSES_ABOVE, etc.)")
    print("  ✓ Both left and right operands")
    print("\nUse cases:")
    print("  - Trend detection (indicator rising/falling)")
    print("  - Momentum analysis (price vs past price)")
    print("  - Ichimoku Chikou validation")
    print("  - ADX strength confirmation")
    print("  - Any historical comparison")

    print("\n✅ LOOKBACK feature demonstration complete!")


if __name__ == "__main__":
    try:
        demo_lookback_feature()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
