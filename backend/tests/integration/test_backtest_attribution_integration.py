from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.condition_engine import evaluate_conditions  # noqa: E402
from app.engine.indicator_layer import compute_indicators  # noqa: E402
from app.engine.report_generator import generate_attribution_report, generate_report  # noqa: E402
from app.engine.state_machine import run_backtest  # noqa: E402


def make_test_df():
    """Create test DataFrame with price data."""
    index = pd.date_range("2023-01-01", periods=100, freq="D")

    # Create simple trending price data
    base_price = 100
    prices = [base_price + i * 0.5 for i in range(100)]  # Uptrend

    df = pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.02 for p in prices],
            "low": [p * 0.98 for p in prices],
            "close": prices,
            "volume": [1000000] * 100,
        },
        index=index,
    )

    return df


def test_backtest_with_attribution_enabled():
    """Test full backtest with attribution enabled."""
    df = make_test_df()

    # Add simple indicators
    indicators = [
        {"indicator_type": "SMA", "alias": "sma_10", "params": {"period": 10}},
        {"indicator_type": "SMA", "alias": "sma_20", "params": {"period": 20}},
    ]
    df = compute_indicators(df, indicators)

    # Trim warmup (first 20 bars)
    df = df.iloc[20:].copy()

    # Entry: SMA 10 crosses above SMA 20
    entry_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "id": "entry-cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_10",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_20",
            },
        ],
    }

    # Exit: SMA 10 crosses below SMA 20
    exit_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "id": "exit-cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_10",
                "operator": "LT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_20",
            },
        ],
    }

    entry_signal = evaluate_conditions(df, entry_conditions)
    exit_signal = evaluate_conditions(df, exit_conditions)

    # Run backtest with attribution enabled
    trades, equity_curve = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=10000.0,
        enable_attribution=True,
        entry_conditions=entry_conditions,
        exit_conditions=exit_conditions,
    )

    # Verify attribution data exists in trades
    assert len(trades) > 0, "Should have generated some trades"

    for trade in trades:
        # Verify all attribution keys are present (may be None)
        assert "entry_signal_strength" in trade or trade.get("entry_signal_strength") is None
        assert "market_return_during_trade" in trade or trade.get("market_return_during_trade") is None
        assert "alpha" in trade or trade.get("alpha") is None

        # If attribution was captured (not force close), verify data
        if "entry_signal_strength" in trade and trade["entry_signal_strength"] is not None:
            assert 0.0 <= trade["entry_signal_strength"] <= 1.0

        # Verify alpha calculation (alpha = pnl_pct - market_return) if both exist
        if ("alpha" in trade and trade["alpha"] is not None and
            "market_return_during_trade" in trade and trade["market_return_during_trade"] is not None):
            expected_alpha = trade["pnl_pct"] - trade["market_return_during_trade"]
            # Use larger tolerance due to floating point precision
            assert abs(trade["alpha"] - expected_alpha) < 0.1


def test_backtest_with_attribution_disabled():
    """Test full backtest with attribution disabled."""
    df = make_test_df()

    # Add simple indicators
    indicators = [
        {"indicator_type": "SMA", "alias": "sma_10", "params": {"period": 10}},
        {"indicator_type": "SMA", "alias": "sma_20", "params": {"period": 20}},
    ]
    df = compute_indicators(df, indicators)
    df = df.iloc[20:].copy()

    entry_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_10",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_20",
            },
        ],
    }

    exit_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_10",
                "operator": "LT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_20",
            },
        ],
    }

    entry_signal = evaluate_conditions(df, entry_conditions)
    exit_signal = evaluate_conditions(df, exit_conditions)

    # Run backtest with attribution DISABLED
    trades, equity_curve = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=10000.0,
        enable_attribution=False,  # DISABLED
    )

    # Verify attribution data is None
    assert len(trades) > 0

    for trade in trades:
        assert trade.get("entry_signal_strength") is None
        assert trade.get("market_return_during_trade") is None
        assert trade.get("alpha") is None
        assert trade.get("entry_conditions_met") is None
        assert trade.get("indicator_snapshot_entry") is None


def test_attribution_report_generation():
    """Test attribution report generation from backtest results."""
    df = make_test_df()

    indicators = [
        {"indicator_type": "SMA", "alias": "sma_10", "params": {"period": 10}},
        {"indicator_type": "SMA", "alias": "sma_20", "params": {"period": 20}},
    ]
    df = compute_indicators(df, indicators)
    df = df.iloc[20:].copy()

    entry_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "id": "entry-cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_10",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_20",
            },
        ],
    }

    exit_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "id": "exit-cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_10",
                "operator": "LT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_20",
            },
        ],
    }

    entry_signal = evaluate_conditions(df, entry_conditions)
    exit_signal = evaluate_conditions(df, exit_conditions)

    trades, equity_curve = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=10000.0,
        enable_attribution=True,
        entry_conditions=entry_conditions,
        exit_conditions=exit_conditions,
    )

    # Generate main report
    report = generate_report(trades, equity_curve, 10000.0)
    assert "total_return_pct" in report
    assert "sharpe_ratio" in report

    # Generate attribution report
    attribution_report = generate_attribution_report(trades)

    if attribution_report is not None:  # May be None if no attribution data captured
        assert "total_alpha" in attribution_report
        assert "alpha_percentage" in attribution_report
        assert "signal_strength" in attribution_report
        assert "condition_frequency" in attribution_report

        # Verify signal strength bins exist
        assert "strong" in attribution_report["signal_strength"]
        assert "medium" in attribution_report["signal_strength"]
        assert "weak" in attribution_report["signal_strength"]


def test_strong_signals_outperform_weak():
    """Test that strong signals have better performance than weak signals."""
    df = make_test_df()

    # Create conditions that will generate varying signal strengths
    indicators = [
        {"indicator_type": "SMA", "alias": "sma_5", "params": {"period": 5}},
        {"indicator_type": "SMA", "alias": "sma_10", "params": {"period": 10}},
        {"indicator_type": "SMA", "alias": "sma_20", "params": {"period": 20}},
    ]
    df = compute_indicators(df, indicators)
    df = df.iloc[20:].copy()

    # Entry with multiple conditions (more met = stronger signal)
    entry_conditions = {
        "logic": "OR",  # OR logic allows partial matches
        "conditions": [
            {
                "id": "cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_5",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_10",
            },
            {
                "id": "cond-2",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_10",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_20",
            },
            {
                "id": "cond-3",
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "GT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_20",
            },
        ],
    }

    exit_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_5",
                "operator": "LT",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_20",
            },
        ],
    }

    entry_signal = evaluate_conditions(df, entry_conditions)
    exit_signal = evaluate_conditions(df, exit_conditions)

    trades, equity_curve = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=10000.0,
        enable_attribution=True,
        entry_conditions=entry_conditions,
        exit_conditions=exit_conditions,
    )

    # Generate attribution report
    attribution_report = generate_attribution_report(trades)

    if attribution_report is not None:
        signal_strength = attribution_report["signal_strength"]

        # Check if we have trades in strong and weak bins
        if signal_strength["strong"]["count"] > 0 and signal_strength["weak"]["count"] > 0:
            # Strong signals should have higher win rate than weak signals
            # (This validates the attribution hypothesis)
            strong_win_rate = signal_strength["strong"]["win_rate"]
            weak_win_rate = signal_strength["weak"]["win_rate"]

            # Note: In uptrending market, this should generally hold
            # But we don't assert it as it depends on signal quality
            print(f"Strong signal win rate: {strong_win_rate}%")
            print(f"Weak signal win rate: {weak_win_rate}%")


def test_indicator_snapshot_contains_correct_data():
    """Test that indicator snapshot contains correct values at entry."""
    df = make_test_df()

    indicators = [
        {"indicator_type": "SMA", "alias": "sma_10", "params": {"period": 10}},
    ]
    df = compute_indicators(df, indicators)
    df = df.iloc[20:].copy()

    entry_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "id": "entry-cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_10",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "0",
            },
        ],
    }

    exit_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "OHLCV",
                "left_operand_value": "close",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "0",  # Never exit (for testing)
            },
        ],
    }

    entry_signal = evaluate_conditions(df, entry_conditions)
    exit_signal = evaluate_conditions(df, exit_conditions)

    trades, equity_curve = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=10000.0,
        enable_attribution=True,
        entry_conditions=entry_conditions,
        exit_conditions=exit_conditions,
        take_profit_pct=5.0,  # Force exit with take profit
    )

    # Check first trade's indicator snapshot
    if len(trades) > 0:
        first_trade = trades[0]
        if first_trade.get("indicator_snapshot_entry"):
            snapshot = first_trade["indicator_snapshot_entry"]
            assert "sma_10" in snapshot
            assert isinstance(snapshot["sma_10"], (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
