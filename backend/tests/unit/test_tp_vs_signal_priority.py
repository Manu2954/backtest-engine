"""
Test cases to verify TP vs signal exit priority in the state machine.

The expected behavior is:
- When a position has both a pending exit (from signal) AND TP is hit on the fill bar,
  TP should take priority and exit at TP price, not at open price.

Current behavior (potential bug):
- Pending exit fills at open price first
- Then _check_stops is called, but position is already closed
- So TP never has a chance to override signal exit
"""

import pandas as pd
import pytest
from app.engine.state_machine import run_backtest


def create_test_df(bars: list[dict]) -> pd.DataFrame:
    """Create a DataFrame from a list of OHLCV bar dicts."""
    df = pd.DataFrame(bars)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df


class TestTPvsSignalPriority:
    """Test cases for TP vs signal exit priority."""

    def test_case_1_tp_should_win(self):
        """
        Test case 1: TP should win over signal exit when TP price is hit.

        Scenario:
        - Entry price: 100
        - Dynamic TP: 5% (TP price = 105)
        - Bar N: exit signal fires (pending_exit = True)
        - Bar N+1: open = 102, high = 106 (TP hit!), close = 104

        Expected: Exit at TP price 105, reason = "take_profit"
        """
        bars = [
            {"date": "2024-01-01", "open": 100, "high": 100, "low": 100, "close": 100},  # Entry signal bar
            {"date": "2024-01-02", "open": 100, "high": 101, "low": 99, "close": 100},   # Entry fills at open=100
            {"date": "2024-01-03", "open": 101, "high": 102, "low": 100, "close": 101},  # In position
            {"date": "2024-01-04", "open": 102, "high": 103, "low": 101, "close": 102},  # Exit signal fires here
            {"date": "2024-01-05", "open": 102, "high": 106, "low": 101, "close": 104},  # TP should hit at 105
        ]
        df = create_test_df(bars)

        # Entry signal on bar 0 (fills bar 1)
        entry_signal = pd.Series([True, False, False, False, False], index=df.index)
        # Exit signal on bar 3 (pending exit set, would fill bar 4)
        exit_signal = pd.Series([False, False, False, True, False], index=df.index)

        trades, equity = run_backtest(
            df=df,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            initial_capital=10000.0,
            asset_class="CRYPTO",  # Allow fractional
            take_profit_pct=5.0,   # TP at 105
        )

        assert len(trades) == 1, f"Expected 1 trade, got {len(trades)}"
        trade = trades[0]

        print(f"\n=== Test Case 1: TP Should Win ===")
        print(f"Entry price: {trade['entry_price']}")
        print(f"Exit price: {trade['exit_price']}")
        print(f"Exit reason: {trade['exit_reason']}")
        print(f"Expected exit reason: take_profit")
        print(f"Expected exit price: ~105")

        # Expected: TP should win
        assert trade["exit_reason"] == "take_profit", (
            f"Expected exit_reason='take_profit', got '{trade['exit_reason']}'"
        )
        # Exit price should be at TP level (105), possibly with slippage
        assert abs(trade["exit_price"] - 105.0) < 1.0, (
            f"Expected exit_price ~105, got {trade['exit_price']}"
        )

    def test_case_2_signal_should_win(self):
        """
        Test case 2: Signal should win when TP is NOT hit.

        Scenario:
        - Entry price: 100
        - Dynamic TP: 5% (TP price = 105)
        - Bar N: exit signal fires (pending_exit = True)
        - Bar N+1: open = 102, high = 103 (TP NOT hit), close = 101

        Expected: Exit at open price 102, reason = "signal"
        """
        bars = [
            {"date": "2024-01-01", "open": 100, "high": 100, "low": 100, "close": 100},  # Entry signal bar
            {"date": "2024-01-02", "open": 100, "high": 101, "low": 99, "close": 100},   # Entry fills at open=100
            {"date": "2024-01-03", "open": 101, "high": 102, "low": 100, "close": 101},  # In position
            {"date": "2024-01-04", "open": 102, "high": 103, "low": 101, "close": 102},  # Exit signal fires here
            {"date": "2024-01-05", "open": 102, "high": 103, "low": 100, "close": 101},  # TP NOT hit (high=103 < 105)
        ]
        df = create_test_df(bars)

        entry_signal = pd.Series([True, False, False, False, False], index=df.index)
        exit_signal = pd.Series([False, False, False, True, False], index=df.index)

        trades, equity = run_backtest(
            df=df,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            initial_capital=10000.0,
            asset_class="CRYPTO",
            take_profit_pct=5.0,   # TP at 105
        )

        assert len(trades) == 1, f"Expected 1 trade, got {len(trades)}"
        trade = trades[0]

        print(f"\n=== Test Case 2: Signal Should Win ===")
        print(f"Entry price: {trade['entry_price']}")
        print(f"Exit price: {trade['exit_price']}")
        print(f"Exit reason: {trade['exit_reason']}")
        print(f"Expected exit reason: signal")
        print(f"Expected exit price: ~102 (open)")

        # Expected: Signal should win since TP not hit
        assert trade["exit_reason"] == "signal", (
            f"Expected exit_reason='signal', got '{trade['exit_reason']}'"
        )
        # Exit price should be at open (102)
        assert abs(trade["exit_price"] - 102.0) < 1.0, (
            f"Expected exit_price ~102, got {trade['exit_price']}"
        )

    def test_case_3_counter_trade_tp(self):
        """
        Test case 3: Counter-trade with TP should exit at TP price.

        Scenario:
        - LONG enters at 100, exits at 95 (5% loss via signal)
        - Counter SHORT enters at 95 with TP = 7.5% (5% * 1.5)
        - SHORT TP price = 95 * (1 - 7.5%) = 87.875
        - Next bar: open = 95, low = 85 (TP hit!), close = 90, AND short_exit_signal = True

        Expected: TP exits at 87.875 (price reached before signal fill)
        """
        bars = [
            {"date": "2024-01-01", "open": 100, "high": 100, "low": 100, "close": 100},  # LONG entry signal
            {"date": "2024-01-02", "open": 100, "high": 101, "low": 99, "close": 100},   # LONG entry fills at 100
            {"date": "2024-01-03", "open": 98, "high": 99, "low": 94, "close": 95},      # Price drops, LONG exit signal
            {"date": "2024-01-04", "open": 95, "high": 96, "low": 94, "close": 95},      # LONG exits at 95 (loss), counter SHORT enters at 95
            {"date": "2024-01-05", "open": 95, "high": 96, "low": 85, "close": 90},      # SHORT TP hit at ~87.875, signal also present
        ]
        df = create_test_df(bars)

        # LONG signals
        entry_signal = pd.Series([True, False, False, False, False], index=df.index)
        exit_signal = pd.Series([False, False, True, False, False], index=df.index)

        # SHORT signals (for counter-trade exit)
        short_entry_signal = pd.Series([False, False, False, False, False], index=df.index)  # No manual short entry
        short_exit_signal = pd.Series([False, False, False, False, True], index=df.index)    # Signal on bar 4

        trades, equity = run_backtest(
            df=df,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            initial_capital=10000.0,
            asset_class="CRYPTO",
            short_entry_signal=short_entry_signal,
            short_exit_signal=short_exit_signal,
            enable_counter_trades=True,
            counter_tp_multiplier=1.5,
        )

        print(f"\n=== Test Case 3: Counter-Trade TP ===")
        print(f"Number of trades: {len(trades)}")
        for i, t in enumerate(trades):
            print(f"Trade {i+1}: direction={t['direction']}, entry={t['entry_price']}, "
                  f"exit={t['exit_price']}, reason={t['exit_reason']}, pnl={t['pnl']:.2f}")

        # Should have 2 trades: LONG (loss) + SHORT (counter-trade)
        assert len(trades) >= 2, f"Expected at least 2 trades, got {len(trades)}"

        long_trade = [t for t in trades if t["direction"] == "LONG"][0]
        short_trades = [t for t in trades if t["direction"] == "SHORT"]

        # LONG should have exited with signal (loss)
        assert long_trade["exit_reason"] == "signal", (
            f"Expected LONG exit_reason='signal', got '{long_trade['exit_reason']}'"
        )

        if short_trades:
            short_trade = short_trades[0]
            # SHORT should have TP = 5% loss * 1.5 = 7.5%
            # TP price for SHORT at entry 95 = 95 * (1 - 7.5%) = 87.875
            expected_tp_price = 95.0 * (1.0 - 0.075)  # 87.875

            print(f"SHORT expected TP price: {expected_tp_price:.4f}")
            print(f"SHORT actual exit price: {short_trade['exit_price']:.4f}")
            print(f"SHORT exit reason: {short_trade['exit_reason']}")

            # Expected: TP should win for counter-trade
            assert short_trade["exit_reason"] == "take_profit", (
                f"Expected SHORT exit_reason='take_profit', got '{short_trade['exit_reason']}'"
            )
            assert abs(short_trade["exit_price"] - expected_tp_price) < 1.0, (
                f"Expected SHORT exit_price ~{expected_tp_price:.4f}, got {short_trade['exit_price']}"
            )

    def test_case_3b_counter_trade_signal_on_prior_bar(self):
        """
        Test case 3b: Counter-trade with TP, but exit signal is on PRIOR bar (pending exit).

        This variant shows the bug: when short_exit_signal fires on bar 4 (before TP bar),
        the pending exit fills at open on bar 5, BEFORE TP check runs.

        Scenario:
        - LONG enters at 100, exits at 95 (5% loss via signal)
        - Counter SHORT enters at 95 with TP = 7.5% (5% * 1.5)
        - SHORT TP price = 95 * (1 - 7.5%) = 87.875
        - Bar 5: SHORT exit signal fires (pending_exit = True)
        - Bar 6: open = 92, low = 85 (TP hit!), close = 90

        Expected: TP exits at 87.875
        Actual (bug): Signal exits at open price 92
        """
        bars = [
            {"date": "2024-01-01", "open": 100, "high": 100, "low": 100, "close": 100},  # LONG entry signal
            {"date": "2024-01-02", "open": 100, "high": 101, "low": 99, "close": 100},   # LONG entry fills at 100
            {"date": "2024-01-03", "open": 98, "high": 99, "low": 94, "close": 95},      # Price drops, LONG exit signal
            {"date": "2024-01-04", "open": 95, "high": 96, "low": 94, "close": 95},      # LONG exits at 95 (loss), counter SHORT enters at 95
            {"date": "2024-01-05", "open": 93, "high": 94, "low": 91, "close": 92},      # SHORT in position, exit signal fires
            {"date": "2024-01-06", "open": 92, "high": 93, "low": 85, "close": 90},      # Pending exit fills here, but TP should hit at 87.875
        ]
        df = create_test_df(bars)

        # LONG signals
        entry_signal = pd.Series([True, False, False, False, False, False], index=df.index)
        exit_signal = pd.Series([False, False, True, False, False, False], index=df.index)

        # SHORT signals - exit signal fires on bar 4 (0-indexed), TP bar is bar 5
        short_entry_signal = pd.Series([False, False, False, False, False, False], index=df.index)
        short_exit_signal = pd.Series([False, False, False, False, True, False], index=df.index)  # Signal fires bar 4

        trades, equity = run_backtest(
            df=df,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            initial_capital=10000.0,
            asset_class="CRYPTO",
            short_entry_signal=short_entry_signal,
            short_exit_signal=short_exit_signal,
            enable_counter_trades=True,
            counter_tp_multiplier=1.5,
        )

        print(f"\n=== Test Case 3b: Counter-Trade with Pending Exit ===")
        print(f"Number of trades: {len(trades)}")
        for i, t in enumerate(trades):
            print(f"Trade {i+1}: direction={t['direction']}, entry={t['entry_price']}, "
                  f"exit={t['exit_price']}, reason={t['exit_reason']}, pnl={t['pnl']:.2f}")

        short_trades = [t for t in trades if t["direction"] == "SHORT"]
        if short_trades:
            short_trade = short_trades[0]
            # Counter-trade enters at bar 5's open (93), not bar 4
            # TP% = 5% loss * 1.5 = 7.5%
            # TP price = 93 * (1 - 0.075) = 86.025
            expected_tp_price = short_trade["entry_price"] * (1.0 - 0.075)

            print(f"SHORT expected TP price: {expected_tp_price:.4f}")
            print(f"SHORT actual exit price: {short_trade['exit_price']:.4f}")
            print(f"SHORT exit reason: {short_trade['exit_reason']}")

            # This assertion documents the EXPECTED behavior (TP wins)
            # It will FAIL with current code (signal wins)
            assert short_trade["exit_reason"] == "take_profit", (
                f"BUG: Expected SHORT exit_reason='take_profit', got '{short_trade['exit_reason']}'"
            )
            assert abs(short_trade["exit_price"] - expected_tp_price) < 1.0, (
                f"BUG: Expected SHORT exit_price ~{expected_tp_price:.4f}, got {short_trade['exit_price']}"
            )

    def test_case_1_dynamic_tp_should_win(self):
        """
        Test case 1 variant: Dynamic TP (from column) should win over signal.

        Using dynamic_tp_pct_column instead of static take_profit_pct.
        """
        bars = [
            {"date": "2024-01-01", "open": 100, "high": 100, "low": 100, "close": 100, "dynamic_tp": 5.0},
            {"date": "2024-01-02", "open": 100, "high": 101, "low": 99, "close": 100, "dynamic_tp": 5.0},
            {"date": "2024-01-03", "open": 101, "high": 102, "low": 100, "close": 101, "dynamic_tp": 5.0},
            {"date": "2024-01-04", "open": 102, "high": 103, "low": 101, "close": 102, "dynamic_tp": 5.0},
            {"date": "2024-01-05", "open": 102, "high": 106, "low": 101, "close": 104, "dynamic_tp": 5.0},
        ]
        df = create_test_df(bars)

        entry_signal = pd.Series([True, False, False, False, False], index=df.index)
        exit_signal = pd.Series([False, False, False, True, False], index=df.index)

        trades, equity = run_backtest(
            df=df,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            initial_capital=10000.0,
            asset_class="CRYPTO",
            dynamic_tp_pct_column="dynamic_tp",  # Use dynamic TP
        )

        assert len(trades) == 1, f"Expected 1 trade, got {len(trades)}"
        trade = trades[0]

        print(f"\n=== Test Case 1 (Dynamic TP): TP Should Win ===")
        print(f"Entry price: {trade['entry_price']}")
        print(f"Exit price: {trade['exit_price']}")
        print(f"Exit reason: {trade['exit_reason']}")
        print(f"Expected exit reason: take_profit")
        print(f"Expected exit price: ~105")

        # Expected: TP should win
        assert trade["exit_reason"] == "take_profit", (
            f"Expected exit_reason='take_profit', got '{trade['exit_reason']}'"
        )
        assert abs(trade["exit_price"] - 105.0) < 1.0, (
            f"Expected exit_price ~105, got {trade['exit_price']}"
        )


class TestTPCheckTiming:
    """Test the timing of TP checks vs pending exit fills."""

    def test_tp_check_order_in_state_machine(self):
        """
        Verify the order of operations in the state machine.

        Current order (potential bug):
        1. Fill pending entry
        2. Fill pending exit (at open price) <-- signal exit happens here
        3. Check stops (TP would trigger here, but position already closed)

        Expected order:
        1. Fill pending entry
        2. Check if TP/SL hit on this bar (before pending exit fill)
        3. If TP/SL hit: exit at TP/SL price, cancel pending exit
        4. Else: fill pending exit at open price
        """
        # This test documents the current behavior
        bars = [
            {"date": "2024-01-01", "open": 100, "high": 100, "low": 100, "close": 100},
            {"date": "2024-01-02", "open": 100, "high": 101, "low": 99, "close": 100},
            {"date": "2024-01-03", "open": 102, "high": 103, "low": 101, "close": 102},  # Exit signal
            {"date": "2024-01-04", "open": 102, "high": 108, "low": 101, "close": 104},  # TP hit at 105
        ]
        df = create_test_df(bars)

        entry_signal = pd.Series([True, False, False, False], index=df.index)
        exit_signal = pd.Series([False, False, True, False], index=df.index)

        trades, equity = run_backtest(
            df=df,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            initial_capital=10000.0,
            asset_class="CRYPTO",
            take_profit_pct=5.0,
        )

        trade = trades[0]
        print(f"\n=== TP Check Timing Test ===")
        print(f"Exit reason: {trade['exit_reason']}")
        print(f"Exit price: {trade['exit_price']}")

        # Document actual behavior
        if trade["exit_reason"] == "signal":
            print("WARNING: Signal exit happened before TP check - this may be a bug")
            print("The engine fills pending exit at open BEFORE checking TP on the same bar")
        else:
            print("TP correctly took priority over pending signal exit")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
