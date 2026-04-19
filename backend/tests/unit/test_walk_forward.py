"""
Unit tests for walk-forward validation logic.
"""
from datetime import date

import pandas as pd
import pytest

from app.engine.robustness.walk_forward import (
    Window,
    generate_windows,
    calculate_consistency_score,
    assess_walk_forward_results,
    build_walk_forward_report,
)


# =============================================================================
# generate_windows tests
# =============================================================================

def test_generate_windows_equal_split():
    """Windows split evenly when bars divisible by window_count."""
    # 100 bars, 5 windows = 20 bars each
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    df = pd.DataFrame({"close": range(100)}, index=dates)

    windows = generate_windows(df, window_count=5)

    assert len(windows) == 5
    assert windows[0].start_idx == 0
    assert windows[0].end_idx == 19  # 0-19 = 20 bars
    assert windows[1].start_idx == 20
    assert windows[1].end_idx == 39
    assert windows[4].start_idx == 80
    assert windows[4].end_idx == 99


def test_generate_windows_uneven_bars():
    """Extra bars distributed across first windows."""
    # 103 bars, 5 windows: 21, 21, 21, 20, 20
    dates = pd.date_range("2020-01-01", periods=103, freq="D")
    df = pd.DataFrame({"close": range(103)}, index=dates)

    windows = generate_windows(df, window_count=5)

    assert len(windows) == 5
    # First 3 windows get 21 bars (extra remainder distributed)
    assert windows[0].end_idx - windows[0].start_idx + 1 == 21
    assert windows[1].end_idx - windows[1].start_idx + 1 == 21
    assert windows[2].end_idx - windows[2].start_idx + 1 == 21
    # Last 2 windows get 20 bars
    assert windows[3].end_idx - windows[3].start_idx + 1 == 20
    assert windows[4].end_idx - windows[4].start_idx + 1 == 20

    # Verify total coverage
    total_bars = sum(w.end_idx - w.start_idx + 1 for w in windows)
    assert total_bars == 103


def test_generate_windows_dates_correct():
    """Window dates match DataFrame index."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    df = pd.DataFrame({"close": range(100)}, index=dates)

    windows = generate_windows(df, window_count=4)

    assert windows[0].start_date == date(2020, 1, 1)
    assert windows[0].end_date == date(2020, 1, 25)  # 25 bars (100/4)


def test_generate_windows_insufficient_bars():
    """Raises error when fewer bars than windows."""
    dates = pd.date_range("2020-01-01", periods=3, freq="D")
    df = pd.DataFrame({"close": range(3)}, index=dates)

    with pytest.raises(ValueError, match="Not enough bars"):
        generate_windows(df, window_count=5)


def test_generate_windows_empty_df():
    """Returns empty list for empty DataFrame."""
    df = pd.DataFrame()
    windows = generate_windows(df, window_count=5)
    assert windows == []


def test_generate_windows_minimum_bars():
    """Works with exactly window_count bars."""
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame({"close": range(5)}, index=dates)

    windows = generate_windows(df, window_count=5)

    assert len(windows) == 5
    # Each window has exactly 1 bar
    for w in windows:
        assert w.end_idx - w.start_idx + 1 == 1


# =============================================================================
# calculate_consistency_score tests
# =============================================================================

def test_consistency_score_perfect():
    """Identical metrics across windows = score near 1.0."""
    window_results = [
        {"metrics": {"total_return_pct": 10.0, "sharpe_ratio": 1.5, "win_rate": 60.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": 10.0, "sharpe_ratio": 1.5, "win_rate": 60.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": 10.0, "sharpe_ratio": 1.5, "win_rate": 60.0, "total_trades": 20}},
    ]

    score, cvs = calculate_consistency_score(window_results)

    assert score == 1.0  # Zero variance = perfect score
    assert cvs["total_return_pct"] == 0.0
    assert cvs["sharpe_ratio"] == 0.0
    assert cvs["win_rate"] == 0.0


def test_consistency_score_variable():
    """High variance = lower score."""
    window_results = [
        {"metrics": {"total_return_pct": 50.0, "sharpe_ratio": 2.0, "win_rate": 70.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": 10.0, "sharpe_ratio": 0.5, "win_rate": 40.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": -20.0, "sharpe_ratio": -0.5, "win_rate": 30.0, "total_trades": 20}},
    ]

    score, cvs = calculate_consistency_score(window_results)

    assert score < 0.5  # High variance = low score
    assert cvs["total_return_pct"] > 0.5  # High CV


def test_consistency_score_excludes_low_trade_windows():
    """Windows with low trade count excluded from calculation."""
    window_results = [
        {"metrics": {"total_return_pct": 10.0, "sharpe_ratio": 1.5, "win_rate": 60.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": 10.0, "sharpe_ratio": 1.5, "win_rate": 60.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": -50.0, "sharpe_ratio": -2.0, "win_rate": 10.0, "total_trades": 5}},  # Excluded (<10 trades)
    ]

    score, cvs = calculate_consistency_score(window_results, min_trades=10)

    assert score == 1.0  # Only windows with 20 trades considered (identical)


def test_consistency_score_insufficient_windows():
    """Returns 0 if less than 2 valid windows."""
    window_results = [
        {"metrics": {"total_return_pct": 10.0, "total_trades": 20}},
    ]

    score, cvs = calculate_consistency_score(window_results)

    assert score == 0.0
    assert cvs == {}


# =============================================================================
# assess_walk_forward_results tests
# =============================================================================

def test_assessment_robust():
    """High consistency + mostly profitable = ROBUST."""
    window_results = [
        {"metrics": {"total_return_pct": 15.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": 12.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": 18.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": 14.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": 16.0, "total_trades": 20}},
    ]

    assessment = assess_walk_forward_results(window_results, consistency_score=0.85)

    assert assessment["level"] == "ROBUST"
    assert len(assessment["risk_flags"]) == 0


def test_assessment_moderate():
    """Medium consistency or profitability = MODERATE."""
    window_results = [
        {"metrics": {"total_return_pct": 20.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": 15.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": -5.0, "total_trades": 20}},  # One loss
        {"metrics": {"total_return_pct": 10.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": 8.0, "total_trades": 20}},
    ]

    assessment = assess_walk_forward_results(window_results, consistency_score=0.65)

    assert assessment["level"] == "MODERATE"


def test_assessment_fragile():
    """Low consistency or profitability = FRAGILE."""
    window_results = [
        {"metrics": {"total_return_pct": 30.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": -10.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": -15.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": 5.0, "total_trades": 5}},
        {"metrics": {"total_return_pct": -8.0, "total_trades": 20}},
    ]

    assessment = assess_walk_forward_results(window_results, consistency_score=0.4)

    assert assessment["level"] == "FRAGILE"
    assert len(assessment["risk_flags"]) > 0


def test_assessment_flags_unprofitable_windows():
    """Risk flag when many windows unprofitable."""
    window_results = [
        {"metrics": {"total_return_pct": 10.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": -5.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": -8.0, "total_trades": 20}},
        {"metrics": {"total_return_pct": -3.0, "total_trades": 20}},
    ]

    assessment = assess_walk_forward_results(window_results, consistency_score=0.5)

    assert any("unprofitable" in flag.lower() for flag in assessment["risk_flags"])


def test_assessment_flags_insufficient_trades():
    """Risk flag when many windows have insufficient trades."""
    window_results = [
        {"metrics": {"total_return_pct": 10.0, "total_trades": 5}},
        {"metrics": {"total_return_pct": 15.0, "total_trades": 5}},
        {"metrics": {"total_return_pct": 12.0, "total_trades": 5}},
        {"metrics": {"total_return_pct": 8.0, "total_trades": 20}},
    ]

    assessment = assess_walk_forward_results(window_results, consistency_score=0.7)

    assert any("insufficient trades" in flag.lower() for flag in assessment["risk_flags"])


# =============================================================================
# build_walk_forward_report tests
# =============================================================================

def test_build_report_structure():
    """Report has all required fields."""
    window_results = [
        {"period": "2020-01 to 2020-06", "metrics": {"total_return_pct": 15.0, "sharpe_ratio": 1.5, "total_trades": 20}},
        {"period": "2020-07 to 2020-12", "metrics": {"total_return_pct": 10.0, "sharpe_ratio": 1.0, "total_trades": 20}},
    ]
    assessment = {"level": "ROBUST", "risk_flags": [], "recommendation": "Good strategy"}

    report = build_walk_forward_report(window_results, 0.85, {"total_return_pct": 0.1}, assessment)

    assert "windows" in report
    assert "summary" in report
    assert "assessment" in report

    summary = report["summary"]
    assert "total_windows" in summary
    assert "sufficient_sample_windows" in summary
    assert "profitable_windows" in summary
    assert "profitable_ratio" in summary
    assert "consistency_score" in summary
    assert "return_range" in summary
    assert "sharpe_range" in summary
    assert "best_window" in summary
    assert "worst_window" in summary


def test_build_report_best_worst_windows():
    """Best and worst windows correctly identified."""
    window_results = [
        {"period": "2020-H1", "metrics": {"total_return_pct": 25.0, "sharpe_ratio": 2.0, "total_trades": 20}},
        {"period": "2020-H2", "metrics": {"total_return_pct": -10.0, "sharpe_ratio": -0.5, "total_trades": 20}},
        {"period": "2021-H1", "metrics": {"total_return_pct": 15.0, "sharpe_ratio": 1.2, "total_trades": 20}},
    ]
    assessment = {"level": "MODERATE", "risk_flags": [], "recommendation": ""}

    report = build_walk_forward_report(window_results, 0.6, {}, assessment)

    assert report["summary"]["best_window"] == "2020-H1"
    assert report["summary"]["worst_window"] == "2020-H2"
    assert report["summary"]["return_range"]["min"] == -10.0
    assert report["summary"]["return_range"]["max"] == 25.0
