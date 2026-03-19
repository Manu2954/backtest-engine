from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.report_generator import generate_attribution_report  # noqa: E402


def make_trade_log_with_attribution():
    """Create sample trade log with attribution data."""
    return [
        {
            "pnl": 100.0,
            "pnl_pct": 5.0,
            "entry_signal_strength": 0.85,
            "alpha": 3.0,
            "entry_conditions_met": ["cond-1", "cond-2"],
        },
        {
            "pnl": -50.0,
            "pnl_pct": -2.5,
            "entry_signal_strength": 0.25,
            "alpha": -1.5,
            "entry_conditions_met": ["cond-1"],
        },
        {
            "pnl": 75.0,
            "pnl_pct": 3.75,
            "entry_signal_strength": 0.65,
            "alpha": 2.0,
            "entry_conditions_met": ["cond-2", "cond-3"],
        },
        {
            "pnl": 25.0,
            "pnl_pct": 1.25,
            "entry_signal_strength": 0.90,
            "alpha": 1.0,
            "entry_conditions_met": ["cond-1", "cond-2", "cond-3"],
        },
        {
            "pnl": -20.0,
            "pnl_pct": -1.0,
            "entry_signal_strength": 0.15,
            "alpha": -0.5,
            "entry_conditions_met": ["cond-3"],
        },
    ]


def test_generate_attribution_report_basic():
    """Test basic attribution report generation."""
    trade_log = make_trade_log_with_attribution()

    report = generate_attribution_report(trade_log)

    assert report is not None
    assert "total_alpha" in report
    assert "alpha_percentage" in report
    assert "signal_strength" in report
    assert "condition_frequency" in report


def test_generate_attribution_report_total_alpha():
    """Test total alpha calculation."""
    trade_log = make_trade_log_with_attribution()

    report = generate_attribution_report(trade_log)

    # Total alpha = 3.0 + (-1.5) + 2.0 + 1.0 + (-0.5) = 4.0
    assert report["total_alpha"] == pytest.approx(4.0, abs=0.01)


def test_generate_attribution_report_alpha_percentage():
    """Test alpha percentage calculation."""
    trade_log = make_trade_log_with_attribution()

    report = generate_attribution_report(trade_log)

    # Total pnl_pct = 5.0 + (-2.5) + 3.75 + 1.25 + (-1.0) = 6.5
    # Alpha percentage = 4.0 / 6.5 * 100 = 61.54%
    assert report["alpha_percentage"] == pytest.approx(61.54, abs=0.1)


def test_generate_attribution_report_signal_strength_bins():
    """Test signal strength binning."""
    trade_log = make_trade_log_with_attribution()

    report = generate_attribution_report(trade_log)

    signal_strength = report["signal_strength"]

    # Strong (>= 0.7): trades 0 (0.85) and 3 (0.90)
    assert signal_strength["strong"]["count"] == 2
    assert signal_strength["strong"]["win_rate"] == 100.0  # Both won

    # Medium (0.3 - 0.7): trade 2 (0.65)
    assert signal_strength["medium"]["count"] == 1
    assert signal_strength["medium"]["win_rate"] == 100.0

    # Weak (< 0.3): trades 1 (0.25) and 4 (0.15)
    assert signal_strength["weak"]["count"] == 2
    assert signal_strength["weak"]["win_rate"] == 0.0  # Both lost


def test_generate_attribution_report_win_rates():
    """Test win rate calculation per signal strength bin."""
    trade_log = [
        {"pnl": 100.0, "entry_signal_strength": 0.85, "alpha": 3.0, "entry_conditions_met": []},
        {"pnl": -50.0, "entry_signal_strength": 0.75, "alpha": -1.5, "entry_conditions_met": []},
        {"pnl": 75.0, "entry_signal_strength": 0.80, "alpha": 2.0, "entry_conditions_met": []},
        {"pnl": 25.0, "entry_signal_strength": 0.90, "alpha": 1.0, "entry_conditions_met": []},
    ]

    report = generate_attribution_report(trade_log)

    # Strong bin: 4 trades, 3 wins, 1 loss → 75% win rate
    assert report["signal_strength"]["strong"]["count"] == 4
    assert report["signal_strength"]["strong"]["win_rate"] == 75.0


def test_generate_attribution_report_avg_alpha():
    """Test average alpha calculation per bin."""
    trade_log = make_trade_log_with_attribution()

    report = generate_attribution_report(trade_log)

    # Strong (0.85, 0.90): alphas = 3.0, 1.0 → avg = 2.0
    assert report["signal_strength"]["strong"]["avg_alpha"] == pytest.approx(2.0, abs=0.01)

    # Medium (0.65): alpha = 2.0 → avg = 2.0
    assert report["signal_strength"]["medium"]["avg_alpha"] == pytest.approx(2.0, abs=0.01)

    # Weak (0.25, 0.15): alphas = -1.5, -0.5 → avg = -1.0
    assert report["signal_strength"]["weak"]["avg_alpha"] == pytest.approx(-1.0, abs=0.01)


def test_generate_attribution_report_condition_frequency():
    """Test condition frequency counting."""
    trade_log = make_trade_log_with_attribution()

    report = generate_attribution_report(trade_log)

    condition_freq = report["condition_frequency"]

    # cond-1: trades 0, 1, 3 = 3 times
    assert condition_freq["cond-1"] == 3

    # cond-2: trades 0, 2, 3 = 3 times
    assert condition_freq["cond-2"] == 3

    # cond-3: trades 2, 3, 4 = 3 times
    assert condition_freq["cond-3"] == 3


def test_generate_attribution_report_no_attribution_data():
    """Test when trade log has no attribution data."""
    trade_log = [
        {"pnl": 100.0, "pnl_pct": 5.0},  # No attribution fields
        {"pnl": -50.0, "pnl_pct": -2.5},
    ]

    report = generate_attribution_report(trade_log)

    # Should return None when no attribution data
    assert report is None


def test_generate_attribution_report_empty_trade_log():
    """Test with empty trade log."""
    trade_log = []

    report = generate_attribution_report(trade_log)

    # Should return None for empty trade log
    assert report is None


def test_generate_attribution_report_partial_attribution():
    """Test when only some trades have attribution data."""
    trade_log = [
        {"pnl": 100.0, "entry_signal_strength": 0.85, "alpha": 3.0, "entry_conditions_met": ["cond-1"]},
        {"pnl": -50.0, "pnl_pct": -2.5},  # No attribution
        {"pnl": 75.0, "entry_signal_strength": 0.65, "alpha": 2.0, "entry_conditions_met": ["cond-2"]},
    ]

    report = generate_attribution_report(trade_log)

    # Should only analyze trades with attribution data
    assert report is not None
    assert report["total_alpha"] == pytest.approx(5.0, abs=0.01)
    assert report["signal_strength"]["strong"]["count"] == 1
    assert report["signal_strength"]["medium"]["count"] == 1


def test_generate_attribution_report_empty_bins():
    """Test when some signal strength bins are empty."""
    trade_log = [
        {"pnl": 100.0, "entry_signal_strength": 0.85, "alpha": 3.0, "entry_conditions_met": []},
        {"pnl": 75.0, "entry_signal_strength": 0.90, "alpha": 2.0, "entry_conditions_met": []},
    ]

    report = generate_attribution_report(trade_log)

    # Only strong bin has trades
    assert report["signal_strength"]["strong"]["count"] == 2
    assert report["signal_strength"]["medium"]["count"] == 0
    assert report["signal_strength"]["weak"]["count"] == 0

    # Empty bins should have 0 stats
    assert report["signal_strength"]["medium"]["win_rate"] == 0.0
    assert report["signal_strength"]["weak"]["win_rate"] == 0.0


def test_generate_attribution_report_zero_total_pnl():
    """Test when total pnl_pct is zero (breakeven)."""
    trade_log = [
        {"pnl": 100.0, "pnl_pct": 5.0, "entry_signal_strength": 0.85, "alpha": 3.0, "entry_conditions_met": []},
        {"pnl": -100.0, "pnl_pct": -5.0, "entry_signal_strength": 0.75, "alpha": -3.0, "entry_conditions_met": []},
    ]

    report = generate_attribution_report(trade_log)

    # Total pnl_pct = 0, alpha percentage should be 0 (not divide by zero)
    assert report["total_alpha"] == 0.0
    assert report["alpha_percentage"] == 0.0


def test_generate_attribution_report_missing_alpha():
    """Test when some trades missing alpha field."""
    trade_log = [
        {"pnl": 100.0, "pnl_pct": 5.0, "entry_signal_strength": 0.85, "alpha": 3.0, "entry_conditions_met": []},
        {"pnl": 75.0, "pnl_pct": 3.75, "entry_signal_strength": 0.75, "entry_conditions_met": []},  # No alpha
    ]

    report = generate_attribution_report(trade_log)

    # Should only sum alphas that exist
    assert report["total_alpha"] == 3.0


def test_generate_attribution_report_empty_conditions():
    """Test when entry_conditions_met is empty list."""
    trade_log = [
        {"pnl": 100.0, "entry_signal_strength": 0.85, "alpha": 3.0, "entry_conditions_met": []},
    ]

    report = generate_attribution_report(trade_log)

    # Should still generate report, condition_frequency will be empty
    assert report is not None
    assert report["condition_frequency"] == {}


def test_generate_attribution_report_nan_handling():
    """Test that NaN values are handled correctly."""
    trade_log = [
        {"pnl": 100.0, "pnl_pct": 5.0, "entry_signal_strength": 0.85, "alpha": float('nan'), "entry_conditions_met": []},
    ]

    report = generate_attribution_report(trade_log)

    # NaN should be treated as 0.0
    assert report["total_alpha"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
