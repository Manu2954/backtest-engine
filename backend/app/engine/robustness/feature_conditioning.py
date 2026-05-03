"""
Feature-Based Conditional Analysis

Extracts observable features at trade entry time and finds which feature
combinations predict trade success.

Key difference from regime detection:
- Regime detection: Labels bars as BULL/BEAR/CHOPPY (descriptive)
- Feature conditioning: Extracts raw measurable features (predictive)

Output: Actionable conditions like "Trade when vol ∈ [0.015, 0.025] AND r_squared > 0.7"
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class FeatureVector:
    """Features extracted at a specific point in time."""
    volatility: float  # Rolling std of returns
    trend_strength: float  # R² from OLS regression
    trend_slope: float  # OLS slope (directional signal)
    price_vs_sma50: float  # (price - SMA50) / SMA50
    returns_autocorr: float  # Lag-1 autocorrelation (mean reversion signal)
    rsi_level: float | None = None  # RSI at entry (if available)
    atr_pct: float | None = None  # ATR as % of price (if available)


def extract_features_at_index(
    df: pd.DataFrame,
    idx: int,
    lookback_window: int = 50,
) -> FeatureVector:
    """
    Extract observable features at a specific bar index.

    All features are computable in real-time (no lookahead).

    Args:
        df: OHLCV DataFrame with DatetimeIndex
        idx: Bar index to extract features at
        lookback_window: Bars to use for rolling calculations

    Returns:
        FeatureVector with all computed features
    """
    # Need enough history for rolling calculations
    start_idx = max(0, idx - lookback_window + 1)
    window_df = df.iloc[start_idx:idx + 1]

    if len(window_df) < 10:
        # Not enough data, return neutral features
        return FeatureVector(
            volatility=0.0,
            trend_strength=0.0,
            trend_slope=0.0,
            price_vs_sma50=0.0,
            returns_autocorr=0.0,
        )

    # Calculate log returns
    log_returns = np.log(window_df['close'] / window_df['close'].shift(1)).dropna()

    # Feature 1: Volatility (rolling std of returns)
    volatility = log_returns.std() if len(log_returns) > 1 else 0.0

    # Feature 2 & 3: Trend strength and slope (OLS regression)
    if len(window_df) >= 10:
        y = np.log(window_df['close'].values)
        x = np.arange(len(y))
        slope, intercept, r_value, _, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2
        trend_strength = r_squared
        trend_slope = slope
    else:
        trend_strength = 0.0
        trend_slope = 0.0

    # Feature 4: Price vs SMA50
    if len(window_df) >= 50:
        sma50 = window_df['close'].iloc[-50:].mean()
        current_price = window_df['close'].iloc[-1]
        price_vs_sma50 = (current_price - sma50) / sma50
    else:
        price_vs_sma50 = 0.0

    # Feature 5: Returns autocorrelation (mean reversion signal)
    if len(log_returns) >= 20:
        returns_autocorr = log_returns.autocorr(lag=1)
        if pd.isna(returns_autocorr):
            returns_autocorr = 0.0
    else:
        returns_autocorr = 0.0

    # Optional: RSI if available in df
    rsi_level = None
    if 'rsi' in df.columns or 'rsi_14' in df.columns:
        rsi_col = 'rsi' if 'rsi' in df.columns else 'rsi_14'
        rsi_level = float(df[rsi_col].iloc[idx]) if pd.notna(df[rsi_col].iloc[idx]) else None

    # Optional: ATR as % of price
    atr_pct = None
    if 'atr' in df.columns or 'atr_14' in df.columns:
        atr_col = 'atr' if 'atr' in df.columns else 'atr_14'
        atr_value = df[atr_col].iloc[idx]
        current_price = df['close'].iloc[idx]
        if pd.notna(atr_value) and current_price > 0:
            atr_pct = float(atr_value / current_price)

    return FeatureVector(
        volatility=round(volatility, 6),
        trend_strength=round(trend_strength, 4),
        trend_slope=round(trend_slope, 6),
        price_vs_sma50=round(price_vs_sma50, 4),
        returns_autocorr=round(returns_autocorr, 4),
        rsi_level=round(rsi_level, 2) if rsi_level is not None else None,
        atr_pct=round(atr_pct, 6) if atr_pct is not None else None,
    )


def extract_trade_features(
    trades: list[dict[str, Any]],
    df: pd.DataFrame,
    lookback_window: int = 50,
) -> list[dict[str, Any]]:
    """
    Extract features at entry time for each trade.

    Args:
        trades: List of trade dicts with 'entry_date', 'pnl_pct', etc.
        df: OHLCV DataFrame with DatetimeIndex
        lookback_window: Bars to use for rolling calculations

    Returns:
        List of trades with 'features' field added
    """
    enriched_trades = []

    for trade in trades:
        entry_date = trade.get("entry_date")
        if entry_date is None:
            continue

        # Find bar index for entry date
        try:
            idx = df.index.get_loc(pd.Timestamp(entry_date))
            if isinstance(idx, slice):
                idx = idx.start
        except KeyError:
            # Date not in index, skip
            continue

        # Extract features at entry
        features = extract_features_at_index(df, idx, lookback_window)

        # Add to trade
        trade_with_features = {
            **trade,
            "features": {
                "volatility": features.volatility,
                "trend_strength": features.trend_strength,
                "trend_slope": features.trend_slope,
                "price_vs_sma50": features.price_vs_sma50,
                "returns_autocorr": features.returns_autocorr,
            }
        }

        # Add optional features if available
        if features.rsi_level is not None:
            trade_with_features["features"]["rsi_level"] = features.rsi_level
        if features.atr_pct is not None:
            trade_with_features["features"]["atr_pct"] = features.atr_pct

        enriched_trades.append(trade_with_features)

    return enriched_trades


def bin_feature(values: list[float], n_bins: int = 4) -> tuple[list[int], list[tuple[float, float]]]:
    """
    Bin feature values into quantiles.

    Args:
        values: List of feature values
        n_bins: Number of bins (default 4 = quartiles)

    Returns:
        Tuple of (bin_indices, bin_ranges)
    """
    if len(values) < n_bins:
        # Not enough data, put all in one bin
        return [0] * len(values), [(min(values), max(values))]

    # Use quantile-based binning
    quantiles = np.linspace(0, 100, n_bins + 1)
    bin_edges = np.percentile(values, quantiles)

    # Ensure unique edges
    bin_edges = np.unique(bin_edges)
    if len(bin_edges) < 2:
        return [0] * len(values), [(min(values), max(values))]

    # Assign bins
    bin_indices = np.digitize(values, bin_edges[1:-1])

    # Create bin ranges
    bin_ranges = []
    for i in range(len(bin_edges) - 1):
        bin_ranges.append((round(bin_edges[i], 6), round(bin_edges[i + 1], 6)))

    return bin_indices.tolist(), bin_ranges


def analyze_feature_conditions(
    trades: list[dict[str, Any]],
    min_trades_per_bin: int = 10,
) -> dict[str, Any]:
    """
    Find which feature ranges predict trade success.

    Uses single-feature analysis first, then can be extended to
    multi-feature combinations.

    Args:
        trades: List of trades with 'features' and 'pnl_pct'
        min_trades_per_bin: Minimum trades to consider a bin reliable

    Returns:
        Dict with winning/losing conditions and feature importance
    """
    if not trades:
        return {
            "winning_conditions": [],
            "losing_conditions": [],
            "feature_importance": {},
            "total_trades": 0,
        }

    # Extract feature names (use first trade as reference)
    feature_names = list(trades[0]["features"].keys())

    # Single-feature analysis
    feature_results = {}

    for feature_name in feature_names:
        # Extract feature values and outcomes
        feature_values = []
        outcomes = []

        for trade in trades:
            feature_val = trade["features"].get(feature_name)
            pnl_pct = trade.get("pnl_pct", 0) * 100  # Convert to percentage
            if feature_val is not None and not np.isnan(feature_val):
                feature_values.append(feature_val)
                outcomes.append({"pnl_pct": pnl_pct, "is_win": pnl_pct > 0})

        if len(feature_values) < min_trades_per_bin:
            continue

        # Bin feature into quartiles
        bin_indices, bin_ranges = bin_feature(feature_values, n_bins=4)

        # Calculate metrics per bin
        bin_metrics = {}
        for bin_idx in range(len(bin_ranges)):
            bin_trades = [
                outcomes[i] for i in range(len(bin_indices))
                if bin_indices[i] == bin_idx
            ]

            if len(bin_trades) < min_trades_per_bin:
                continue

            pnls = [t["pnl_pct"] for t in bin_trades]
            wins = [t for t in bin_trades if t["is_win"]]

            bin_metrics[bin_idx] = {
                "feature_range": bin_ranges[bin_idx],
                "total_trades": len(bin_trades),
                "win_rate": len(wins) / len(bin_trades) * 100,
                "avg_pnl_pct": np.mean(pnls),
                "sharpe": np.mean(pnls) / np.std(pnls) * np.sqrt(252) if len(pnls) > 1 and np.std(pnls) > 0 else 0.0,
            }

        feature_results[feature_name] = {
            "bins": bin_metrics,
            "overall_mean": np.mean(feature_values),
            "overall_std": np.std(feature_values),
        }

    # Find best and worst conditions
    winning_conditions = []
    losing_conditions = []

    for feature_name, result in feature_results.items():
        for bin_idx, metrics in result["bins"].items():
            condition = {
                "feature": feature_name,
                "range": metrics["feature_range"],
                "win_rate": round(metrics["win_rate"], 1),
                "avg_pnl_pct": round(metrics["avg_pnl_pct"], 2),
                "sharpe": round(metrics["sharpe"], 2),
                "total_trades": metrics["total_trades"],
                "confidence": "HIGH" if metrics["total_trades"] >= 20 else "MEDIUM",
            }

            if metrics["win_rate"] >= 60:
                winning_conditions.append(condition)
            elif metrics["win_rate"] <= 40:
                losing_conditions.append(condition)

    # Sort by win rate
    winning_conditions.sort(key=lambda x: x["win_rate"], reverse=True)
    losing_conditions.sort(key=lambda x: x["win_rate"])

    # Calculate feature importance (variance in win rates across bins)
    feature_importance = {}
    for feature_name, result in feature_results.items():
        win_rates = [m["win_rate"] for m in result["bins"].values()]
        if len(win_rates) >= 2:
            # Higher variance = more important feature
            importance = np.std(win_rates) / 100.0  # Normalize to 0-1
            feature_importance[feature_name] = round(importance, 3)

    # Normalize importance scores
    if feature_importance:
        max_importance = max(feature_importance.values())
        if max_importance > 0:
            feature_importance = {
                k: round(v / max_importance, 3)
                for k, v in feature_importance.items()
            }

    return {
        "winning_conditions": winning_conditions[:10],  # Top 10
        "losing_conditions": losing_conditions[:10],  # Bottom 10
        "feature_importance": feature_importance,
        "total_trades": len(trades),
        "feature_statistics": {
            feature_name: {
                "mean": round(result["overall_mean"], 6),
                "std": round(result["overall_std"], 6),
            }
            for feature_name, result in feature_results.items()
        },
    }


def build_feature_conditioning_report(
    trades_with_features: list[dict[str, Any]],
    condition_analysis: dict[str, Any],
    overall_metrics: dict[str, Any],
) -> dict[str, Any]:
    """
    Build complete feature conditioning report.

    Args:
        trades_with_features: Trades with extracted features
        condition_analysis: Results from analyze_feature_conditions
        overall_metrics: Overall backtest metrics for comparison

    Returns:
        Complete report dict
    """
    # Generate actionable recommendation
    winning_conditions = condition_analysis["winning_conditions"]
    feature_importance = condition_analysis["feature_importance"]

    if not winning_conditions:
        recommendation = (
            "No strong feature-based patterns found. Strategy performance may be "
            "random or dependent on factors not captured by standard features."
        )
        risk_flags = ["No reliable winning conditions identified"]
    else:
        # Get top condition
        top_condition = winning_conditions[0]
        top_feature = top_condition["feature"]
        top_range = top_condition["range"]
        top_win_rate = top_condition["win_rate"]

        recommendation = (
            f"Strategy performs best when {top_feature} ∈ [{top_range[0]}, {top_range[1]}] "
            f"(win rate: {top_win_rate}%). "
        )

        # Add secondary conditions
        if len(winning_conditions) >= 2:
            second = winning_conditions[1]
            recommendation += (
                f"Secondary edge when {second['feature']} ∈ [{second['range'][0]}, {second['range'][1]}]. "
            )

        recommendation += (
            "Consider filtering trades based on these conditions in production."
        )

        # Risk flags
        risk_flags = []
        losing_conditions = condition_analysis["losing_conditions"]
        if losing_conditions:
            worst = losing_conditions[0]
            risk_flags.append(
                f"Avoid trading when {worst['feature']} ∈ [{worst['range'][0]}, {worst['range'][1]}] "
                f"(win rate: {worst['win_rate']}%)"
            )

        # Check if important features have both winning and losing zones
        for feature_name, importance in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:3]:
            has_winning = any(c["feature"] == feature_name for c in winning_conditions)
            has_losing = any(c["feature"] == feature_name for c in losing_conditions)
            if has_winning and has_losing:
                risk_flags.append(
                    f"{feature_name} is critical - strategy is highly sensitive to its value"
                )

    report = {
        "total_trades_analyzed": len(trades_with_features),
        "winning_conditions": winning_conditions,
        "losing_conditions": condition_analysis["losing_conditions"],
        "feature_importance": feature_importance,
        "feature_statistics": condition_analysis["feature_statistics"],
        "overall_backtest_metrics": overall_metrics,
        "assessment": {
            "recommendation": recommendation,
            "risk_flags": risk_flags,
            "most_important_feature": max(feature_importance.items(), key=lambda x: x[1])[0] if feature_importance else None,
        },
    }

    return report
