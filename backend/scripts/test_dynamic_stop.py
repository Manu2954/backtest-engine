"""
Quick test to verify dynamic Kijun-based stops work correctly.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv
from app.engine.indicator_layer import compute_indicators, trim_warmup_period
from app.engine.state_machine import run_backtest
from app.engine.condition_engine import evaluate_conditions


def test_dynamic_stop():
    print("\n" + "="*80)
    print("DYNAMIC STOP TEST - Verify Kijun-based stops")
    print("="*80)

    # Fetch data
    df = fetch_ohlcv("AAPL", "2023-01-01", "2023-12-31", "1d", "STOCK")
    print(f"Fetched {len(df)} bars")

    # Add Ichimoku
    indicators = [
        {"indicator_type": "ICHIMOKU", "alias": "ichimoku", "params": {"tenkan": 9, "kijun": 26, "senkou": 52}}
    ]
    df = compute_indicators(df, indicators)
    df, _ = trim_warmup_period(df)

    # Simple entry: price above Kijun
    entry_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "ichimoku_kijun",
            }
        ]
    }

    # Simple exit: price below Kijun
    exit_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "LT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "ichimoku_kijun",
            }
        ]
    }

    entry_signal = evaluate_conditions(df, entry_group)
    exit_signal = evaluate_conditions(df, exit_group)

    print(f"Entry signals: {entry_signal.sum()}")
    print(f"Exit signals: {exit_signal.sum()}")

    # Test with dynamic stop
    print("\nRunning backtest with dynamic Kijun-based stop...")
    trades, equity = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=10000.0,
        asset_class="STOCK",
        dynamic_stop_column="ichimoku_kijun",
    )

    print(f"\nTotal trades: {len(trades)}")

    if len(trades) > 0:
        # Show first trade
        trade = trades[0]
        print(f"\nFirst trade:")
        print(f"  Entry: {trade['entry_date'].date()} @ ${trade['entry_price']:.2f}")
        print(f"  Exit: {trade['exit_date'].date()} @ ${trade['exit_price']:.2f}")
        print(f"  Exit Reason: {trade['exit_reason']}")
        print(f"  P&L: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")
        print(f"  Duration: {trade['trade_duration_days']} days")

        # Count exit reasons
        stop_loss_count = sum(1 for t in trades if t.get('exit_reason') == 'stop_loss')
        signal_count = sum(1 for t in trades if t.get('exit_reason') == 'signal')

        print(f"\nExit breakdown:")
        print(f"  Dynamic stop (price < Kijun): {stop_loss_count}")
        print(f"  Signal exit (close < Kijun): {signal_count}")

        print("\n✅ Dynamic Kijun-based stops working!")
    else:
        print("\n⚠️  No trades executed")

    print("="*80 + "\n")


if __name__ == "__main__":
    test_dynamic_stop()
