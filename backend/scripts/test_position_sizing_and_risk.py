"""
Smoke test for Position Sizing and Risk Management features.

Tests:
1. Position sizing - full_capital mode
2. Position sizing - percent_capital mode
3. Position sizing - fixed_amount mode
4. Stop loss triggering
5. Take profit triggering
6. Exit reason tracking
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


def test_full_capital():
    """Test default behavior - use all capital."""
    print("\n" + "="*80)
    print("TEST 1: Full Capital Position Sizing (Default)")
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
        position_size_type="full_capital",
        position_size_value=100.0,
    )

    print(f"Total trades: {len(trades)}")
    print(f"Final equity: ${equity_curve.iloc[-1]:.2f}")

    if len(trades) > 0:
        first_trade = trades[0]
        print(f"\nFirst trade:")
        print(f"  Entry: {first_trade['entry_date'].date()} @ ${first_trade['entry_price']:.2f}")
        print(f"  Shares: {first_trade['shares']:.0f}")
        print(f"  Exit reason: {first_trade['exit_reason']}")
        print(f"  PnL: ${first_trade['pnl']:.2f}")

    assert len(trades) > 0, "Should have at least 1 trade"
    print("\n✅ TEST 1 PASSED\n")


def test_percent_capital():
    """Test percent_capital mode - use only 50% per trade."""
    print("\n" + "="*80)
    print("TEST 2: Percent Capital Position Sizing (50%)")
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
        position_size_type="percent_capital",
        position_size_value=50.0,  # Use only 50% of capital
    )

    print(f"Total trades: {len(trades)}")
    print(f"Final equity: ${equity_curve.iloc[-1]:.2f}")

    if len(trades) > 0:
        first_trade = trades[0]
        position_value = first_trade['shares'] * first_trade['entry_price']
        print(f"\nFirst trade:")
        print(f"  Entry: {first_trade['entry_date'].date()} @ ${first_trade['entry_price']:.2f}")
        print(f"  Shares: {first_trade['shares']:.0f}")
        print(f"  Position value: ${position_value:.2f}")
        print(f"  Expected ~50% of capital: ${initial_capital * 0.5:.2f}")
        print(f"  Exit reason: {first_trade['exit_reason']}")

        # Verify position is approximately 50% of initial capital
        assert position_value < initial_capital * 0.6, "Position should be <= 50% of capital"

    assert len(trades) > 0, "Should have at least 1 trade"
    print("\n✅ TEST 2 PASSED\n")


def test_fixed_amount():
    """Test fixed_amount mode - always invest $5000."""
    print("\n" + "="*80)
    print("TEST 3: Fixed Amount Position Sizing ($5000 per trade)")
    print("="*80)

    ticker = "AAPL"
    start = "2023-01-01"
    end = "2023-12-31"
    initial_capital = 20000.0
    fixed_amount = 5000.0

    df = fetch_ohlcv(ticker, start, end, "1d", "STOCK")

    indicators = [
        {"indicator_type": "SMA", "alias": "sma_20", "params": {"period": 20, "source": "close"}},
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)

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
        position_size_type="fixed_amount",
        position_size_value=fixed_amount,
    )

    print(f"Total trades: {len(trades)}")
    print(f"Final equity: ${equity_curve.iloc[-1]:.2f}")

    if len(trades) > 0:
        first_trade = trades[0]
        position_value = first_trade['shares'] * first_trade['entry_price']
        print(f"\nFirst trade:")
        print(f"  Entry: {first_trade['entry_date'].date()} @ ${first_trade['entry_price']:.2f}")
        print(f"  Shares: {first_trade['shares']:.0f}")
        print(f"  Position value: ${position_value:.2f}")
        print(f"  Target fixed amount: ${fixed_amount:.2f}")
        print(f"  Exit reason: {first_trade['exit_reason']}")

        # Verify position is approximately the fixed amount
        assert abs(position_value - fixed_amount) < 500, "Position should be close to $5000"

    assert len(trades) > 0, "Should have at least 1 trade"
    print("\n✅ TEST 3 PASSED\n")


def test_stop_loss():
    """Test stop loss - should exit when price drops 3%."""
    print("\n" + "="*80)
    print("TEST 4: Stop Loss (3% loss)")
    print("="*80)

    ticker = "AAPL"
    start = "2023-01-01"
    end = "2023-12-31"
    initial_capital = 10000.0

    df = fetch_ohlcv(ticker, start, end, "1d", "STOCK")

    indicators = [
        {"indicator_type": "RSI", "alias": "rsi_14", "params": {"period": 14, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)

    # Simple entry: RSI below 30 (oversold)
    entry_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "30",
            }
        ],
    }

    # Exit: RSI above 70 (overbought)
    exit_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "70",
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
        stop_loss_pct=3.0,  # 3% stop loss
    )

    print(f"Total trades: {len(trades)}")
    print(f"Final equity: ${equity_curve.iloc[-1]:.2f}")

    # Count trades by exit reason
    exit_reasons = {}
    for trade in trades:
        reason = trade['exit_reason']
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    print(f"\nExit reasons breakdown:")
    for reason, count in exit_reasons.items():
        print(f"  {reason}: {count}")

    # Show first stop_loss trade if any
    stop_loss_trades = [t for t in trades if t['exit_reason'] == 'stop_loss']
    if stop_loss_trades:
        sl_trade = stop_loss_trades[0]
        pct_change = ((sl_trade['exit_price'] - sl_trade['entry_price']) / sl_trade['entry_price']) * 100
        print(f"\nFirst stop loss trade:")
        print(f"  Entry: ${sl_trade['entry_price']:.2f}")
        print(f"  Exit: ${sl_trade['exit_price']:.2f}")
        print(f"  Change: {pct_change:.2f}%")
        print(f"  PnL: ${sl_trade['pnl']:.2f}")

        # Verify it's approximately -3%
        assert pct_change <= -2.5, "Stop loss should trigger around -3%"

    print("\n✅ TEST 4 PASSED\n")


def test_take_profit():
    """Test take profit - should exit when price gains 5%."""
    print("\n" + "="*80)
    print("TEST 5: Take Profit (5% gain)")
    print("="*80)

    ticker = "AAPL"
    start = "2023-01-01"
    end = "2023-12-31"
    initial_capital = 10000.0

    df = fetch_ohlcv(ticker, start, end, "1d", "STOCK")

    indicators = [
        {"indicator_type": "RSI", "alias": "rsi_14", "params": {"period": 14, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)

    # Simple entry: RSI below 30 (oversold)
    entry_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "30",
            }
        ],
    }

    # Exit: RSI above 70 (overbought)
    exit_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "70",
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
        take_profit_pct=5.0,  # 5% take profit
    )

    print(f"Total trades: {len(trades)}")
    print(f"Final equity: ${equity_curve.iloc[-1]:.2f}")

    # Count trades by exit reason
    exit_reasons = {}
    for trade in trades:
        reason = trade['exit_reason']
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    print(f"\nExit reasons breakdown:")
    for reason, count in exit_reasons.items():
        print(f"  {reason}: {count}")

    # Show first take_profit trade if any
    take_profit_trades = [t for t in trades if t['exit_reason'] == 'take_profit']
    if take_profit_trades:
        tp_trade = take_profit_trades[0]
        pct_change = ((tp_trade['exit_price'] - tp_trade['entry_price']) / tp_trade['entry_price']) * 100
        print(f"\nFirst take profit trade:")
        print(f"  Entry: ${tp_trade['entry_price']:.2f}")
        print(f"  Exit: ${tp_trade['exit_price']:.2f}")
        print(f"  Change: {pct_change:.2f}%")
        print(f"  PnL: ${tp_trade['pnl']:.2f}")

        # Verify it's approximately +5%
        assert pct_change >= 4.5, "Take profit should trigger around +5%"

    print("\n✅ TEST 5 PASSED\n")


def test_combined_risk_management():
    """Test both stop loss and take profit together."""
    print("\n" + "="*80)
    print("TEST 6: Combined Stop Loss (3%) + Take Profit (8%)")
    print("="*80)

    ticker = "AAPL"
    start = "2013-01-01"
    end = "2025-12-31"
    initial_capital = 10000.0

    df = fetch_ohlcv(ticker, start, end, "1d", "STOCK")

    indicators = [
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
        {"indicator_type": "SMA", "alias": "sma_200", "params": {"period": 200, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)

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

    entry_signal = evaluate_conditions(df, entry_group)
    exit_signal = evaluate_conditions(df, exit_group)

    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=initial_capital,
        asset_class="STOCK",
        position_size_type="percent_capital",
        position_size_value=50.0,
        stop_loss_pct=3.0,
        take_profit_pct=8.0,
        periodic_contribution={"frequency":"monthly", "amount": 2000}
    )

    print(f"Total trades: {len(trades)}")
    # for trade in trades:
    #     print(
    #         f"Entry {trade['entry_date'].date()} @ {trade['entry_price']:.2f} \n "
    #         f"Exit {trade['exit_date'].date()} @ {trade['exit_price']:.2f} \n "
    #         f"PnL {trade['pnl']:.2f} \n "
    #         f"Shares {trade['shares']:.2f} \n"
    #         f"Total capital = {equity_curve.at[trade['exit_date']]}\n"
    #         "-------------------------------------------------------------"
    #     )
    print(f"Final equity: ${equity_curve.iloc[-1]:.2f}")

    # Count trades by exit reason
    exit_reasons = {}
    for trade in trades:
        reason = trade['exit_reason']
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    print(f"\nExit reasons breakdown:")
    for reason, count in exit_reasons.items():
        print(f"  {reason}: {count}")

    # Verify we have exit_reason for all trades
    assert all('exit_reason' in t for t in trades), "All trades should have exit_reason"

    # Verify exit reasons are valid
    valid_reasons = {'signal', 'stop_loss', 'take_profit', 'force_close'}
    for trade in trades:
        assert trade['exit_reason'] in valid_reasons, f"Invalid exit reason: {trade['exit_reason']}"

    print("\n✅ TEST 6 PASSED\n")


def main() -> None:
    print("\n" + "="*80)
    print("SMOKE TEST: Position Sizing & Risk Management")
    print("="*80)

    try:
        test_full_capital()
        test_percent_capital()
        test_fixed_amount()
        test_stop_loss()
        test_take_profit()
        test_combined_risk_management()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nSummary:")
        print("  ✓ Position sizing (full_capital, percent_capital, fixed_amount)")
        print("  ✓ Stop loss triggering and tracking")
        print("  ✓ Take profit triggering and tracking")
        print("  ✓ Exit reason recording")
        print("  ✓ Combined risk management")
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
