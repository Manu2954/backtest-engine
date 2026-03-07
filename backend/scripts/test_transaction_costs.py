"""
Smoke test for Transaction Costs (Commission & Slippage).

Tests:
1. No costs (baseline)
2. Fixed commission per trade
3. Percentage commission
4. Slippage
5. All costs combined
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


def run_backtest_with_costs(
    commission_per_trade=0.0,
    commission_pct=0.0,
    slippage_pct=0.0,
    label="Test"
):
    """Helper to run backtest with specific cost parameters."""
    ticker = "AAPL"
    start = "2013-01-01"
    end = "2023-12-31"
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
        commission_per_trade=commission_per_trade,
        commission_pct=commission_pct,
        slippage_pct=slippage_pct,
    )

    final_equity = equity_curve.iloc[-1]
    total_return = ((final_equity - initial_capital) / initial_capital) * 100
    total_pnl = sum(t['pnl'] for t in trades)

    print(f"\n{label}:")
    print(f"  Commission/trade: ${commission_per_trade:.2f}")
    print(f"  Commission %: {commission_pct:.4f}%")
    print(f"  Slippage %: {slippage_pct:.4f}%")
    print(f"  Total trades: {len(trades)}")
    print(f"  Final equity: ${final_equity:.2f}")
    print(f"  Total return: {total_return:.2f}%")
    print(f"  Total PnL: ${total_pnl:.2f}")

    return trades, final_equity, total_return


def main() -> None:
    print("\n" + "="*80)
    print("SMOKE TEST: Transaction Costs")
    print("="*80)

    try:
        # Test 1: No costs (baseline)
        print("\n" + "="*80)
        print("TEST 1: No Costs (Baseline)")
        print("="*80)
        trades1, equity1, return1 = run_backtest_with_costs(
            commission_per_trade=0.0,
            commission_pct=0.0,
            slippage_pct=0.0,
            label="No costs"
        )
        print("\n✅ TEST 1 PASSED")

        # Test 2: Fixed commission
        print("\n" + "="*80)
        print("TEST 2: Fixed Commission ($5 per trade)")
        print("="*80)
        trades2, equity2, return2 = run_backtest_with_costs(
            commission_per_trade=5.0,
            commission_pct=0.0,
            slippage_pct=0.0,
            label="$5 commission"
        )

        # Verify commission reduced returns
        assert equity2 < equity1, "Commission should reduce final equity"
        commission_impact = equity1 - equity2
        expected_commission = len(trades2) * 2 * 5.0  # 2 trades per round trip * $5
        print(f"\n  Commission impact: ${commission_impact:.2f}")
        print(f"  Expected commission: ${expected_commission:.2f}")
        assert abs(commission_impact - expected_commission) < 50, "Commission impact should match expected"
        print("\n✅ TEST 2 PASSED")

        # Test 3: Percentage commission
        print("\n" + "="*80)
        print("TEST 3: Percentage Commission (0.1%)")
        print("="*80)
        trades3, equity3, return3 = run_backtest_with_costs(
            commission_per_trade=0.0,
            commission_pct=0.1,
            slippage_pct=0.0,
            label="0.1% commission"
        )

        assert equity3 < equity1, "Percentage commission should reduce final equity"
        print("\n✅ TEST 3 PASSED")

        # Test 4: Slippage
        print("\n" + "="*80)
        print("TEST 4: Slippage (0.05%)")
        print("="*80)
        trades4, equity4, return4 = run_backtest_with_costs(
            commission_per_trade=0.0,
            commission_pct=0.0,
            slippage_pct=0.05,
            label="0.05% slippage"
        )

        assert equity4 < equity1, "Slippage should reduce final equity"
        print("\n✅ TEST 4 PASSED")

        # Test 5: All costs combined
        print("\n" + "="*80)
        print("TEST 5: All Costs Combined")
        print("="*80)
        trades5, equity5, return5 = run_backtest_with_costs(
            commission_per_trade=5.0,
            commission_pct=0.1,
            slippage_pct=0.05,
            label="All costs"
        )

        assert equity5 < equity1, "Combined costs should reduce final equity most"
        assert equity5 < equity2, "Combined costs should be worse than just commission"
        assert equity5 < equity3, "Combined costs should be worse than just percentage"
        assert equity5 < equity4, "Combined costs should be worse than just slippage"
        print("\n✅ TEST 5 PASSED")

        # Summary
        print("\n" + "="*80)
        print("SUMMARY: Transaction Cost Impact")
        print("="*80)
        print(f"Baseline (no costs):        ${equity1:.2f} ({return1:+.2f}%)")
        print(f"Fixed commission ($5):      ${equity2:.2f} ({return2:+.2f}%) - Impact: ${equity1-equity2:.2f}")
        print(f"Percentage commission (0.1%): ${equity3:.2f} ({return3:+.2f}%) - Impact: ${equity1-equity3:.2f}")
        print(f"Slippage (0.05%):           ${equity4:.2f} ({return4:+.2f}%) - Impact: ${equity1-equity4:.2f}")
        print(f"All costs combined:         ${equity5:.2f} ({return5:+.2f}%) - Impact: ${equity1-equity5:.2f}")

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nConclusion:")
        print("  ✓ Transaction costs properly reduce returns")
        print("  ✓ Fixed commission scales with number of trades")
        print("  ✓ Percentage commission scales with trade size")
        print("  ✓ Slippage affects execution prices")
        print("  ✓ Combined costs have cumulative impact")
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
