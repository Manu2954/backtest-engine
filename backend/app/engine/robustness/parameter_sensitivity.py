"""
Parameter Sensitivity Analyzer for Phase 2 Robustness Analysis.

Tests strategy performance as indicator parameters vary by ±variation_pct.
Identifies fragile vs robust strategies based on metric stability.
"""
from __future__ import annotations

import copy
from typing import Any
from uuid import UUID

import numpy as np
from scipy import stats


def generate_parameter_variants(
    strategy_dict: dict[str, Any],
    variation_pct: float = 0.2
) -> list[dict[str, Any]]:
    """
    Generate strategy variants with parameter variations.

    For each indicator parameter that is numeric (period, length, etc.):
    - Create variant with param * (1 - variation_pct)
    - Create variant with param * (1 + variation_pct)

    Args:
        strategy_dict: Strategy data including indicators
        variation_pct: Percentage to vary parameters (0.2 = ±20%)

    Returns:
        List of strategy dicts with modified indicator params.
        Each dict includes 'variant_label' and 'variant_params' for tracking.

    Example:
        strategy with RSI(period=14) generates:
        - Variant 1: RSI(period=11)  # 14 * 0.8
        - Variant 2: RSI(period=17)  # 14 * 1.2
    """
    variants = []

    indicators = strategy_dict.get("indicators", [])

    for indicator_idx, indicator in enumerate(indicators):
        indicator_alias = indicator.get("alias")
        params = indicator.get("params", {})

        # Find numeric parameters
        for param_name, param_value in params.items():
            if not isinstance(param_value, (int, float)):
                continue  # Skip non-numeric params (e.g., source="close")

            if param_value <= 0:
                continue  # Skip zero or negative (can't vary meaningfully)

            # Generate lower variant
            lower_value = max(1, round(param_value * (1 - variation_pct)))
            if lower_value != param_value:  # Only if different
                variant = copy.deepcopy(strategy_dict)
                variant["indicators"][indicator_idx]["params"][param_name] = lower_value

                pct_change = ((lower_value - param_value) / param_value) * 100
                variant_label = f"{indicator_alias}.{param_name}: {param_value} → {lower_value} ({pct_change:+.1f}%)"
                variant_params = {
                    "indicator_index": indicator_idx,
                    "indicator_alias": indicator_alias,
                    "param_name": param_name,
                    "original_value": param_value,
                    "variant_value": lower_value,
                    "change_pct": pct_change
                }

                variants.append({
                    "strategy": variant,
                    "variant_label": variant_label,
                    "variant_params": variant_params
                })

            # Generate upper variant
            upper_value = round(param_value * (1 + variation_pct))
            if upper_value != param_value:  # Only if different
                variant = copy.deepcopy(strategy_dict)
                variant["indicators"][indicator_idx]["params"][param_name] = upper_value

                pct_change = ((upper_value - param_value) / param_value) * 100
                variant_label = f"{indicator_alias}.{param_name}: {param_value} → {upper_value} ({pct_change:+.1f}%)"
                variant_params = {
                    "indicator_index": indicator_idx,
                    "indicator_alias": indicator_alias,
                    "param_name": param_name,
                    "original_value": param_value,
                    "variant_value": upper_value,
                    "change_pct": pct_change
                }

                variants.append({
                    "strategy": variant,
                    "variant_label": variant_label,
                    "variant_params": variant_params
                })

    return variants


def calculate_stability_score(
    baseline_metrics: dict[str, float],
    variant_metrics: list[dict[str, float]],
    key_metrics: list[str] | None = None
) -> tuple[float, dict[str, float]]:
    """
    Calculate stability score (0.0-1.0) based on metric variation across variants.

    Higher score = more stable (robust strategy).
    Lower score = high variation (fragile strategy).

    Uses coefficient of variation (CV = std_dev / mean) for each metric,
    then averages across metrics.

    Args:
        baseline_metrics: Metrics from baseline strategy
        variant_metrics: List of metrics from each variant
        key_metrics: Which metrics to analyze (default: return, sharpe, win_rate)

    Returns:
        (overall_stability_score, per_metric_cv_dict)

    Interpretation:
        > 0.8: ROBUST (metrics vary < 20%)
        0.6-0.8: MODERATE (metrics vary 20-40%)
        < 0.6: FRAGILE (metrics vary > 40%)
    """
    if key_metrics is None:
        key_metrics = ["total_return_pct", "sharpe_ratio", "win_rate"]

    # Collect values per metric
    metric_values = {metric: [] for metric in key_metrics}

    # Add baseline
    for metric in key_metrics:
        if metric in baseline_metrics:
            metric_values[metric].append(baseline_metrics[metric])

    # Add variants
    for variant in variant_metrics:
        for metric in key_metrics:
            if metric in variant:
                metric_values[metric].append(variant[metric])

    # Calculate coefficient of variation per metric
    metric_cvs = {}
    valid_cvs = []

    for metric, values in metric_values.items():
        if len(values) < 2:
            continue  # Need at least 2 values

        arr = np.array(values)

        # Handle edge cases
        if np.all(arr == 0):
            cv = 0.0  # All zeros = perfectly stable
        elif np.mean(arr) == 0:
            cv = 1.0  # Mean is zero but values vary = unstable
        else:
            # Standard coefficient of variation
            cv = np.std(arr) / abs(np.mean(arr))

        metric_cvs[metric] = cv
        valid_cvs.append(cv)

    # Overall stability score: 1 - mean(CV)
    # Capped at [0, 1] range
    if valid_cvs:
        mean_cv = np.mean(valid_cvs)
        stability_score = max(0.0, min(1.0, 1.0 - mean_cv))
    else:
        stability_score = 0.0  # No valid metrics

    return stability_score, metric_cvs


def assess_robustness_level(stability_score: float) -> str:
    """
    Classify robustness level based on stability score.

    Args:
        stability_score: 0.0-1.0 score from calculate_stability_score

    Returns:
        "ROBUST", "MODERATE", or "FRAGILE"
    """
    if stability_score >= 0.8:
        return "ROBUST"
    elif stability_score >= 0.6:
        return "MODERATE"
    else:
        return "FRAGILE"


def generate_risk_flags(
    baseline_metrics: dict[str, float],
    variant_metrics: list[dict[str, float]],
    metric_cvs: dict[str, float]
) -> list[str]:
    """
    Generate specific risk warnings based on analysis results.

    Args:
        baseline_metrics: Baseline strategy metrics
        variant_metrics: Variant metrics
        metric_cvs: Coefficient of variation per metric

    Returns:
        List of risk flag strings
    """
    flags = []

    # Check for high variation in critical metrics
    if metric_cvs.get("total_return_pct", 0) > 0.5:
        flags.append("Return varies >50% across parameter changes")

    if metric_cvs.get("sharpe_ratio", 0) > 0.4:
        flags.append("Sharpe ratio highly parameter-dependent")

    if metric_cvs.get("win_rate", 0) > 0.3:
        flags.append("Win rate unstable across variants")

    # Check if any variant has negative returns while baseline is positive
    baseline_return = baseline_metrics.get("total_return_pct", 0)
    if baseline_return > 0:
        negative_variants = [
            v for v in variant_metrics
            if v.get("total_return_pct", 0) < 0
        ]
        if negative_variants:
            pct = (len(negative_variants) / len(variant_metrics)) * 100
            flags.append(f"{len(negative_variants)} variants ({pct:.0f}%) have negative returns")

    # Check if Sharpe drops below 1.0 for any variant
    baseline_sharpe = baseline_metrics.get("sharpe_ratio", 0)
    if baseline_sharpe > 1.0:
        poor_sharpe_variants = [
            v for v in variant_metrics
            if v.get("sharpe_ratio", 0) < 1.0
        ]
        if poor_sharpe_variants:
            flags.append(f"{len(poor_sharpe_variants)} variants have Sharpe < 1.0")

    return flags


def generate_recommendation(
    robustness_level: str,
    risk_flags: list[str],
    stability_score: float
) -> str:
    """
    Generate actionable recommendation based on analysis.

    Args:
        robustness_level: ROBUST, MODERATE, or FRAGILE
        risk_flags: List of risk warnings
        stability_score: Overall stability score

    Returns:
        Recommendation string
    """
    if robustness_level == "ROBUST" and not risk_flags:
        return (
            "Strategy is robust to parameter changes. Metrics remain stable across variants. "
            "Safe to deploy with confidence."
        )
    elif robustness_level == "ROBUST" and risk_flags:
        return (
            "Strategy shows good parameter stability overall, but some concerns exist. "
            "Review risk flags before deployment. Consider additional robustness tests."
        )
    elif robustness_level == "MODERATE":
        return (
            "Strategy has moderate parameter sensitivity. Performance varies 20-40% across variants. "
            "Use with caution. Consider: (1) Tighter parameter ranges, (2) Additional filters, "
            "(3) Reduced position sizing, (4) Further testing on different time periods."
        )
    else:  # FRAGILE
        return (
            "Strategy is highly parameter-dependent (fragile). Small parameter changes cause large "
            "performance swings. This suggests overfitting to specific parameter values. "
            "DO NOT DEPLOY. Recommendation: Simplify strategy or find more robust parameter ranges."
        )
