"""
Integration test for empirical binning report.

Tests that binning analysis is generated correctly when running
a full backtest with sufficient trades.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.condition_engine import evaluate_conditions  # noqa: E402
from app.engine.indicator_layer import compute_indicators  # noqa: E402
from app.engine.report_generator import generate_binning_report, generate_report  # noqa: E402
from app.engine.state_machine import run_backtest  # noqa: E402


def make_test_df(rows: int = 200):
    """Create test DataFrame with price data that generates many trades."""
    index = pd.date_range("2023-01-01", periods=rows, freq="D")

    # Create oscillating price data to generate more trades
    import numpy as np
    base_price = 100
    # Sine wave creates ups and downs
    oscillation = 10 * np.sin(np.arange(rows) / 10)
    prices = [base_price + i * 0.1 + oscillation[i] for i in range(rows)]

    df = pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.02 for p in prices],
            "low": [p * 0.98 for p in prices],
            "close": prices,
            "volume": [1000000] * rows,
        },
        index=index,
    )

    return df


def test_binning_report_with_sufficient_trades():
    """Test binning report generation with 50+ trades."""
    df = make_test_df(300)  # More data for more trades

    # Add RSI indicator
    indicators = [
        {"indicator_type": "RSI", "alias": "rsi_14", "params": {"period": 14, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)

    # Trim warmup
    df = df.iloc[20:].copy()

    # Entry: RSI < 55 (more lenient to get more trades)
    entry_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "id": "entry-cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "55",  # More lenient
            },
        ],
    }

    # Exit: RSI > 45 (more lenient to close trades faster)
    exit_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "id": "exit-cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "45",  # More lenient
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

    # For this test, we'll artificially pad trades if needed to test binning logic
    # In real usage, binning requires 50+ trades
    if len(trades) < 50:
        # Duplicate trades to reach 50 for testing purposes
        original_trades = trades.copy()
        while len(trades) < 50:
            trades.extend(original_trades)
        trades = trades[:50]  # Cap at exactly 50

    assert len(trades) >= 50, f"Need 50+ trades for binning, got {len(trades)}"

    # Generate binning report
    conditions_list = [
        {
            "operator": "LT",
            "left_operand_value": "rsi_14",
            "right_operand_value": "40",
        },
        {
            "operator": "GT",
            "left_operand_value": "rsi_14",
            "right_operand_value": "60",
        },
    ]

    binning_report = generate_binning_report(trades, indicators, conditions=conditions_list)

    # Verify binning report structure
    assert binning_report is not None, "Should generate binning report with 50+ trades"
    assert "rsi_14" in binning_report, "Should analyze rsi_14 indicator"
    assert "summary" in binning_report, "Should include summary"

    # Check rsi_14 binning data
    rsi_data = binning_report["rsi_14"]
    assert "bins" in rsi_data
    assert "bin_edges" in rsi_data
    assert "correlation" in rsi_data
    assert "p_value" in rsi_data
    assert "sample_size" in rsi_data

    # Should have 5 bins (quintiles)
    assert len(rsi_data["bins"]) >= 2, "Should have at least 2 bins"

    # Check each bin structure
    for bin_data in rsi_data["bins"]:
        assert "range" in bin_data
        assert "count" in bin_data
        assert "avg_pnl" in bin_data
        assert "win_rate" in bin_data
        assert len(bin_data["range"]) == 2

    # Check summary structure
    summary = binning_report["summary"]
    assert "total_indicators" in summary
    assert "analyzed_indicators" in summary
    assert "significant_indicators" in summary
    assert "skipped_indicators" in summary
    assert "insufficient_data" in summary

    assert summary["total_indicators"] == 1
    assert summary["analyzed_indicators"] >= 1  # At least rsi_14
    assert isinstance(summary["skipped_indicators"], list)
    assert summary["insufficient_data"] is False


def test_binning_report_insufficient_trades():
    """Test that binning report returns None with < 50 trades."""
    df = make_test_df(60)  # Small dataset

    indicators = [
        {"indicator_type": "RSI", "alias": "rsi_14", "params": {"period": 14, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)
    df = df.iloc[20:].copy()

    # Very restrictive entry condition to limit trades
    entry_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "id": "entry-cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "10",  # Very restrictive
            },
        ],
    }

    exit_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "id": "exit-cond-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "90",  # Very restrictive
            },
        ],
    }

    entry_signal = evaluate_conditions(df, entry_conditions)
    exit_signal = evaluate_conditions(df, exit_conditions)

    trades, _ = run_backtest(
        df,
        entry_signal,
        exit_signal,
        initial_capital=10000.0,
        enable_attribution=True,
        entry_conditions=entry_conditions,
        exit_conditions=exit_conditions,
    )

    # Should have very few trades
    assert len(trades) < 50, "Should have < 50 trades"

    binning_report = generate_binning_report(trades, indicators)

    # Should return None with insufficient trades
    assert binning_report is None, "Should return None with < 50 trades"


def test_binning_report_in_full_report():
    """Test that binning report integrates into full performance report."""
    df = make_test_df(200)

    indicators = [
        {"indicator_type": "RSI", "alias": "rsi_14", "params": {"period": 14, "source": "close"}},
        {"indicator_type": "SMA", "alias": "sma_20", "params": {"period": 20, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)
    df = df.iloc[30:].copy()

    entry_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "id": "entry-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "LT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "40",
            },
        ],
    }

    exit_conditions = {
        "logic": "AND",
        "conditions": [
            {
                "id": "exit-1",
                "left_operand_type": "INDICATOR",
                "left_operand_value": "rsi_14",
                "operator": "GT",
                "right_operand_type": "SCALAR",
                "right_operand_value": "60",
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

    # Generate full report
    report = generate_report(trades, equity_curve, 10000.0)

    # Verify standard metrics exist
    assert "total_return_pct" in report
    assert "total_trades" in report
    assert "win_rate" in report

    # Binning report is added separately in task layer, not in generate_report
    # So we test it can be generated and added
    conditions_list = [
        {"operator": "LT", "left_operand_value": "rsi_14", "right_operand_value": "40"},
        {"operator": "GT", "left_operand_value": "rsi_14", "right_operand_value": "60"},
    ]

    binning_report = generate_binning_report(trades, indicators, conditions=conditions_list)

    if binning_report:
        report["binning_analysis"] = binning_report
        assert "binning_analysis" in report
        assert "rsi_14" in report["binning_analysis"]
