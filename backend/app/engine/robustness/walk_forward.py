"""
Walk-Forward Validation

Tests strategy performance across rolling time windows to detect period-dependency.
Unlike walk-forward optimization, this uses fixed parameters - just validates
if the same strategy works consistently across different market periods.

Key insight: Compute indicators once for full period, then slice into windows.
This avoids warmup loss per window.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd


@dataclass
class Window:
    """Represents a time window for validation."""
    index: int
    start_idx: int
    end_idx: int
    start_date: date
    end_date: date


def generate_windows(df: pd.DataFrame, window_count: int = 5) -> list[Window]:
    """
    Divide DataFrame into N equal windows by bar count.

    Args:
        df: DataFrame with DatetimeIndex (already trimmed for warmup)
        window_count: Number of windows to create (default: 5)

    Returns:
        List of Window objects with index ranges and dates

    Example:
        1000 bars, 5 windows → 200 bars each
        Window 1: bars 0-199
        Window 2: bars 200-399
        ...
    """
    if df.empty:
        return []

    total_bars = len(df)

    if total_bars < window_count:
        raise ValueError(
            f"Not enough bars ({total_bars}) for {window_count} windows. "
            f"Need at least {window_count} bars."
        )

    bars_per_window = total_bars // window_count
    remainder = total_bars % window_count

    windows = []
    start_idx = 0

    for i in range(window_count):
        # Distribute remainder bars across first N windows
        extra = 1 if i < remainder else 0
        end_idx = start_idx + bars_per_window + extra - 1

        # Clamp to valid range
        end_idx = min(end_idx, total_bars - 1)

        windows.append(Window(
            index=i + 1,
            start_idx=start_idx,
            end_idx=end_idx,
            start_date=df.index[start_idx].date(),
            end_date=df.index[end_idx].date(),
        ))

        start_idx = end_idx + 1

    return windows


def calculate_consistency_score(
    window_results: list[dict[str, Any]],
    min_trades: int = 10,
) -> tuple[float, dict[str, float]]:
    """
    Calculate consistency score across windows.

    Uses coefficient of variation (CV) like parameter sensitivity.
    Lower CV = more consistent = higher score.

    Args:
        window_results: List of window result dicts with 'metrics'
        min_trades: Minimum trades to include window in calculation (default: 10)

    Returns:
        Tuple of (overall_score, per_metric_cvs)
        Score is 0.0-1.0 where 1.0 = perfectly consistent

    Note:
        Windows with fewer than min_trades are excluded from calculation.
    """
    # Filter windows by trade count
    valid_windows = [
        w for w in window_results
        if w.get("metrics", {}).get("total_trades", 0) >= min_trades
    ]

    if len(valid_windows) < 2:
        # Can't calculate CV with less than 2 data points
        return 0.0, {}

    # Metrics to evaluate
    metrics = ["total_return_pct", "sharpe_ratio", "win_rate"]
    metric_cvs = {}

    for metric in metrics:
        values = [
            w["metrics"].get(metric, 0.0)
            for w in valid_windows
            if w.get("metrics") and w["metrics"].get(metric) is not None
        ]

        if len(values) < 2:
            continue

        mean_val = sum(values) / len(values)
        if mean_val == 0:
            # Avoid division by zero
            metric_cvs[metric] = 1.0  # Max variability
            continue

        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        cv = abs(std_dev / mean_val)

        # Cap CV at 1.0 for score calculation
        metric_cvs[metric] = min(cv, 1.0)

    if not metric_cvs:
        return 0.0, {}

    # Overall score = 1 - mean(CVs)
    mean_cv = sum(metric_cvs.values()) / len(metric_cvs)
    score = max(0.0, 1.0 - mean_cv)

    return round(score, 3), {k: round(v, 3) for k, v in metric_cvs.items()}


def assess_walk_forward_results(
    window_results: list[dict[str, Any]],
    consistency_score: float,
    min_trades: int = 10,
) -> dict[str, Any]:
    """
    Generate assessment based on walk-forward results.

    Args:
        window_results: List of window result dicts
        consistency_score: Calculated consistency score (0-1)
        min_trades: Minimum trades for reliable metrics (default: 10)

    Returns:
        Assessment dict with level, risk_flags, and recommendation
    """
    # Count metrics
    total_windows = len(window_results)
    profitable_windows = sum(
        1 for w in window_results
        if w.get("metrics", {}).get("total_return_pct", 0) > 0
    )
    sufficient_sample_windows = sum(
        1 for w in window_results
        if w.get("metrics", {}).get("total_trades", 0) >= min_trades
    )
    insufficient_sample_windows = total_windows - sufficient_sample_windows

    # Determine level
    if consistency_score >= 0.8 and profitable_windows >= total_windows * 0.8:
        level = "ROBUST"
    elif consistency_score >= 0.6 and profitable_windows >= total_windows * 0.6:
        level = "MODERATE"
    else:
        level = "FRAGILE"

    # Generate risk flags
    risk_flags = []

    if profitable_windows < total_windows * 0.5:
        risk_flags.append(
            f"Strategy was unprofitable in {total_windows - profitable_windows}/{total_windows} windows"
        )

    if insufficient_sample_windows > total_windows * 0.4:
        risk_flags.append(
            f"{insufficient_sample_windows}/{total_windows} windows had insufficient trades for reliable metrics"
        )

    if consistency_score < 0.5:
        risk_flags.append(
            "High variance in performance across time periods - strategy may be regime-dependent"
        )

    # Find worst window
    worst_window = None
    worst_return = float('inf')
    for w in window_results:
        ret = w.get("metrics", {}).get("total_return_pct", 0)
        if ret < worst_return:
            worst_return = ret
            worst_window = w.get("period", "Unknown")

    if worst_return < -10:
        risk_flags.append(
            f"Significant loss ({worst_return:.1f}%) in period: {worst_window}"
        )

    # Generate recommendation
    if level == "ROBUST":
        recommendation = (
            "Strategy shows consistent performance across different time periods. "
            "Results suggest the strategy is not overfit to a specific market regime."
        )
    elif level == "MODERATE":
        recommendation = (
            "Strategy shows moderate consistency across time periods. "
            "Consider investigating underperforming windows to understand regime dependency. "
            "May benefit from adding market regime filters."
        )
    else:
        recommendation = (
            "Strategy shows inconsistent performance across time periods. "
            "High variance suggests possible overfitting or strong regime dependency. "
            "Not recommended for live trading without significant improvements."
        )

    return {
        "level": level,
        "risk_flags": risk_flags,
        "recommendation": recommendation,
    }


def build_walk_forward_report(
    window_results: list[dict[str, Any]],
    consistency_score: float,
    metric_cvs: dict[str, float],
    assessment: dict[str, Any],
    min_trades: int = 10,
) -> dict[str, Any]:
    """
    Build the complete walk-forward validation report.

    Args:
        window_results: List of per-window results
        consistency_score: Overall consistency score
        metric_cvs: Per-metric coefficient of variation
        assessment: Assessment dict (level, flags, recommendation)
        min_trades: Minimum trades for sufficient sample (default: 10)

    Returns:
        Complete report dict matching API schema
    """
    total_windows = len(window_results)
    sufficient_sample_windows = sum(
        1 for w in window_results
        if w.get("metrics", {}).get("total_trades", 0) >= min_trades
    )
    profitable_windows = sum(
        1 for w in window_results
        if w.get("metrics", {}).get("total_return_pct", 0) > 0
    )

    # Calculate ranges
    returns = [
        w.get("metrics", {}).get("total_return_pct", 0)
        for w in window_results
    ]
    sharpes = [
        w.get("metrics", {}).get("sharpe_ratio", 0)
        for w in window_results
    ]

    # Find best/worst windows
    best_window = None
    worst_window = None
    best_return = float('-inf')
    worst_return = float('inf')

    for w in window_results:
        ret = w.get("metrics", {}).get("total_return_pct", 0)
        period = w.get("period", "Unknown")
        if ret > best_return:
            best_return = ret
            best_window = period
        if ret < worst_return:
            worst_return = ret
            worst_window = period

    return {
        "windows": window_results,
        "summary": {
            "total_windows": total_windows,
            "sufficient_sample_windows": sufficient_sample_windows,
            "profitable_windows": profitable_windows,
            "profitable_ratio": round(profitable_windows / total_windows, 2) if total_windows > 0 else 0,
            "consistency_score": consistency_score,
            "per_metric_cv": metric_cvs,
            "return_range": {
                "min": round(min(returns), 2) if returns else 0,
                "max": round(max(returns), 2) if returns else 0,
            },
            "sharpe_range": {
                "min": round(min(sharpes), 2) if sharpes else 0,
                "max": round(max(sharpes), 2) if sharpes else 0,
            },
            "best_window": best_window,
            "worst_window": worst_window,
        },
        "assessment": assessment,
    }
