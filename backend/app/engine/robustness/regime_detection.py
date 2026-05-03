"""
Regime Detection

Detects market regimes using pluggable segmentation strategies.

Architecture:
    Strategy selects detection + labeling method
    → PELT finds boundaries
    → Strategy-specific feature extraction
    → Strategy-specific labeling
    → Analysis functions (trades by regime, dependency, etc.)

Strategies:
    - "volatility": Detects vol shifts → labels HIGH_VOL, LOW_VOL, TRANSITION
    - "directional": Detects trend reversals → labels BULL, BEAR, CHOPPY, RANGING

Usage:
    segments, labels = detect_regimes(df, strategy="directional")
    regime_metrics = analyze_trades_by_regime(trades, labels)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd

from app.engine.robustness.segmentation import SegmentationFactory
from app.engine.robustness.segmentation.base import LabeledSegment


StrategyName = Literal["l1_trend", "pelt_directional", "pelt_volatility"]


@dataclass
class Segment:
    """A contiguous regime segment with metadata."""
    start_idx: int
    end_idx: int
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    regime: str
    bar_count: int
    features: dict[str, float]
    strength: float | None = None


def detect_regimes(
    df: pd.DataFrame,
    strategy: StrategyName = "pelt_volatility",
    penalty: float | None = None,
    min_segment_length: int = 20,
    vol_window: int = 20,
    k: float = 0.015,  # For l1_trend strategy only
) -> tuple[list[Segment], pd.Series]:
    """
    Main entry point: Detect market regimes in price data.

    Args:
        df: DataFrame with OHLCV data (must have 'close' column and DatetimeIndex)
        strategy: Segmentation strategy:
            - "l1_trend": L1 Trend Filter (2 regimes: BULL/BEAR)
            - "pelt_directional": PELT rolling_mean (4 regimes)
            - "pelt_volatility": PELT returns_vol (4 regimes)
        penalty: PELT penalty. If None, uses np.log(n). Ignored for l1_trend.
        min_segment_length: Minimum bars per segment. Ignored for l1_trend.
        vol_window: Window for rolling calculations (PELT strategies only)
        k: L1 smoothing parameter (l1_trend strategy only), range 0.01-0.03

    Returns:
        Tuple of:
        - List of Segment objects
        - Series of regime labels indexed by date
    """
    if len(df) < min_segment_length * 2:
        # Not enough data - return single segment
        strategy_impl = SegmentationFactory.create_strategy(strategy)
        default_regime = strategy_impl.get_regime_types()[0]

        regime_labels = pd.Series(
            [default_regime] * len(df),
            index=df.index,
        )
        segments = [Segment(
            start_idx=0,
            end_idx=len(df) - 1,
            start_date=df.index[0],
            end_date=df.index[-1],
            regime=default_regime,
            bar_count=len(df),
            features={},
            strength=None,
        )]
        return segments, regime_labels

    # Create strategy instance with parameters
    strategy_kwargs = {}
    if strategy == "l1_trend":
        strategy_kwargs["k"] = k
    elif strategy == "pelt_directional":
        # Add directional-specific kwargs if needed in future
        pass

    strategy_impl = SegmentationFactory.create_strategy(strategy, **strategy_kwargs)

    # Update vol_window if strategy supports it
    if hasattr(strategy_impl, 'vol_window'):
        strategy_impl.vol_window = vol_window

    # Step 1: Detect changepoints
    changepoints = strategy_impl.detect_changepoints(
        df,
        penalty=penalty,
        min_segment_length=min_segment_length,
    )

    # Step 2: Label segments using strategy-specific rules
    labeled_segments = strategy_impl.label_segments(df, changepoints)

    # Step 3: Build Segment objects with dates
    segments = _build_segments(df, labeled_segments)

    # Step 4: Create per-bar regime labels
    regime_labels = pd.Series(index=df.index, dtype=str)
    for segment in segments:
        regime_labels.iloc[segment.start_idx:segment.end_idx + 1] = segment.regime

    return segments, regime_labels


def _build_segments(
    df: pd.DataFrame,
    labeled_segments: list[LabeledSegment],
) -> list[Segment]:
    """Convert LabeledSegment to Segment with date metadata."""
    segments = []

    for ls in labeled_segments:
        # end_idx in LabeledSegment is exclusive, convert to inclusive for Segment
        end_idx_inclusive = ls.end_idx - 1

        # Round features for cleaner output
        rounded_features = {
            k: round(v, 4) if isinstance(v, float) else v
            for k, v in ls.features.items()
        }

        segment = Segment(
            start_idx=ls.start_idx,
            end_idx=end_idx_inclusive,
            start_date=df.index[ls.start_idx],
            end_date=df.index[end_idx_inclusive],
            regime=ls.regime,
            bar_count=ls.end_idx - ls.start_idx,
            features=rounded_features,
            strength=ls.strength,
        )
        segments.append(segment)

    return segments


# =============================================================================
# Legacy functions for backward compatibility
# =============================================================================

def detect_changepoints(
    df: pd.DataFrame,
    strategy: StrategyName = "volatility",
    penalty: float | None = None,
    min_segment_length: int = 20,
    vol_window: int = 20,
) -> list[int]:
    """
    Detect regime changepoints using selected strategy.

    This is a convenience function that delegates to the strategy.
    For full control, use SegmentationFactory directly.
    """
    strategy_impl = SegmentationFactory.create_strategy(strategy)
    if hasattr(strategy_impl, 'vol_window'):
        strategy_impl.vol_window = vol_window

    return strategy_impl.detect_changepoints(
        df,
        penalty=penalty,
        min_segment_length=min_segment_length,
    )


def extract_segment_features(
    df: pd.DataFrame,
    changepoints: list[int],
    strategy: StrategyName = "volatility",
) -> list[dict[str, float]]:
    """
    Extract features for each segment using selected strategy.

    This is a convenience function for testing/debugging.
    """
    strategy_impl = SegmentationFactory.create_strategy(strategy)

    features = []
    for i in range(len(changepoints) - 1):
        start_idx = changepoints[i]
        end_idx = changepoints[i + 1]
        feat = strategy_impl.compute_segment_features(df, start_idx, end_idx)
        feat["segment_id"] = i
        features.append(feat)

    return features


# =============================================================================
# Analysis functions (strategy-agnostic)
# =============================================================================

def get_regime_at_date(
    regime_labels: pd.Series,
    date: pd.Timestamp,
) -> str:
    """
    Get regime label for a specific date.

    Args:
        regime_labels: Series of regime labels
        date: Date to look up

    Returns:
        Regime label string
    """
    if date in regime_labels.index:
        return regime_labels.loc[date]

    # Find closest date
    idx = regime_labels.index.get_indexer([date], method="ffill")[0]
    if idx >= 0:
        return regime_labels.iloc[idx]

    # Default fallback
    return regime_labels.iloc[0] if len(regime_labels) > 0 else "UNKNOWN"


def analyze_trades_by_regime(
    trades: list[dict[str, Any]],
    regime_labels: pd.Series,
) -> dict[str, dict[str, Any]]:
    """
    Group trades by regime at entry and calculate metrics.

    Args:
        trades: List of trade dicts with 'entry_date', 'exit_date', 'pnl_pct', etc.
        regime_labels: Series of regime labels

    Returns:
        Dict with metrics per regime
    """
    # Get unique regimes from labels
    unique_regimes = regime_labels.unique().tolist()

    # Initialize results for all regimes
    regime_trades: dict[str, list] = {regime: [] for regime in unique_regimes}

    for trade in trades:
        entry_date = trade.get("entry_date")
        if entry_date is None:
            continue

        regime = get_regime_at_date(regime_labels, pd.Timestamp(entry_date))
        if regime in regime_trades:
            regime_trades[regime].append(trade)

    # Calculate metrics per regime
    results = {}
    for regime, trades_list in regime_trades.items():
        if not trades_list:
            results[regime] = {
                "total_trades": 0,
                "total_return_pct": 0.0,
                "win_rate": 0.0,
                "avg_pnl_pct": 0.0,
                "sharpe_ratio": 0.0,
            }
            continue

        # pnl_pct from state_machine is a decimal (0.05 = 5%), convert to percentage
        pnl_pcts = [t.get("pnl_pct", 0) * 100 for t in trades_list]
        wins = [p for p in pnl_pcts if p > 0]

        total_return = sum(pnl_pcts)
        win_rate = len(wins) / len(pnl_pcts) * 100 if pnl_pcts else 0
        avg_pnl = np.mean(pnl_pcts) if pnl_pcts else 0

        # Simplified Sharpe (annualized assuming daily)
        if len(pnl_pcts) > 1 and np.std(pnl_pcts) > 0:
            sharpe = np.mean(pnl_pcts) / np.std(pnl_pcts) * np.sqrt(252)
        else:
            sharpe = 0.0

        results[regime] = {
            "total_trades": len(trades_list),
            "total_return_pct": round(total_return, 2),
            "win_rate": round(win_rate, 2),
            "avg_pnl_pct": round(avg_pnl, 2),
            "sharpe_ratio": round(sharpe, 2),
        }

    return results


def analyze_cross_regime_trades(
    trades: list[dict[str, Any]],
    regime_labels: pd.Series,
) -> dict[str, Any]:
    """
    Analyze trades that span multiple regimes.

    A trade that enters in BULL but exits in BEAR held through a regime
    transition - this is valuable information about the strategy's
    holding period relative to regime duration.

    Args:
        trades: List of trade dicts with 'entry_date', 'exit_date', 'pnl_pct'
        regime_labels: Series of regime labels

    Returns:
        Dict with cross-regime trade analysis:
        - total_trades: Total number of trades analyzed
        - cross_regime_trades: Number of trades spanning multiple regimes
        - cross_regime_pct: Percentage of trades that span regimes
        - cross_regime_avg_pnl: Average P&L of cross-regime trades
        - same_regime_avg_pnl: Average P&L of same-regime trades
        - transitions: Dict of transition counts (e.g., {"BULL->BEAR": 5})
    """
    if not trades:
        return {
            "total_trades": 0,
            "cross_regime_trades": 0,
            "cross_regime_pct": 0.0,
            "cross_regime_avg_pnl": 0.0,
            "same_regime_avg_pnl": 0.0,
            "transitions": {},
        }

    cross_regime = []
    same_regime = []
    transitions: dict[str, int] = {}

    for trade in trades:
        entry_date = trade.get("entry_date")
        exit_date = trade.get("exit_date")
        pnl_pct = trade.get("pnl_pct", 0) * 100  # Convert to percentage

        if entry_date is None or exit_date is None:
            continue

        entry_regime = get_regime_at_date(regime_labels, pd.Timestamp(entry_date))
        exit_regime = get_regime_at_date(regime_labels, pd.Timestamp(exit_date))

        if entry_regime != exit_regime:
            cross_regime.append(pnl_pct)
            transition_key = f"{entry_regime}->{exit_regime}"
            transitions[transition_key] = transitions.get(transition_key, 0) + 1
        else:
            same_regime.append(pnl_pct)

    total = len(cross_regime) + len(same_regime)
    cross_pct = (len(cross_regime) / total * 100) if total > 0 else 0.0

    return {
        "total_trades": total,
        "cross_regime_trades": len(cross_regime),
        "cross_regime_pct": round(cross_pct, 1),
        "cross_regime_avg_pnl": round(np.mean(cross_regime), 2) if cross_regime else 0.0,
        "same_regime_avg_pnl": round(np.mean(same_regime), 2) if same_regime else 0.0,
        "transitions": transitions,
    }


def calculate_regime_distribution(
    regime_labels: pd.Series,
) -> dict[str, float]:
    """
    Calculate percentage of time in each regime.

    Args:
        regime_labels: Series of regime labels

    Returns:
        Dict with percentage per regime
    """
    total = len(regime_labels)
    if total == 0:
        return {}

    counts = regime_labels.value_counts()

    return {
        regime: round(count / total * 100, 2)
        for regime, count in counts.items()
    }


def assess_regime_dependency(
    regime_metrics: dict[str, dict[str, Any]],
) -> tuple[str, float]:
    """
    Assess how dependent strategy is on regime.

    Uses coefficient of variation of returns across regimes.

    Args:
        regime_metrics: Metrics per regime from analyze_trades_by_regime

    Returns:
        Tuple of (dependency level, CV score)
        - INDEPENDENT: CV < 0.3
        - MODERATE: CV 0.3-0.6
        - DEPENDENT: CV > 0.6
    """
    returns = [
        m["total_return_pct"]
        for m in regime_metrics.values()
        if m["total_trades"] > 0
    ]

    if len(returns) < 2:
        return "INDEPENDENT", 0.0

    mean_return = np.mean(returns)
    std_return = np.std(returns)

    if mean_return == 0:
        cv = 1.0 if std_return > 0 else 0.0
    else:
        cv = abs(std_return / mean_return)

    cv = min(cv, 1.0)  # Cap at 1.0

    if cv < 0.3:
        level = "INDEPENDENT"
    elif cv < 0.6:
        level = "MODERATE"
    else:
        level = "DEPENDENT"

    return level, round(cv, 3)


def build_regime_report(
    segments: list[Segment],
    regime_labels: pd.Series,
    regime_metrics: dict[str, dict[str, Any]],
    regime_distribution: dict[str, float],
    dependency_level: str,
    dependency_score: float,
    cross_regime_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build complete regime detection report.

    Args:
        segments: List of Segment objects
        regime_labels: Per-bar regime labels
        regime_metrics: Metrics per regime
        regime_distribution: Percentage time in each regime
        dependency_level: INDEPENDENT/MODERATE/DEPENDENT
        dependency_score: CV score
        cross_regime_analysis: Optional cross-regime trade analysis

    Returns:
        Complete report dict
    """
    # Find best and worst regimes
    regimes_with_trades = {
        r: m for r, m in regime_metrics.items()
        if m["total_trades"] > 0
    }

    best_regime = None
    worst_regime = None

    if regimes_with_trades:
        best_regime = max(
            regimes_with_trades.keys(),
            key=lambda r: regimes_with_trades[r]["total_return_pct"]
        )
        worst_regime = min(
            regimes_with_trades.keys(),
            key=lambda r: regimes_with_trades[r]["total_return_pct"]
        )

    # Generate risk flags
    risk_flags = []

    for regime, metrics in regime_metrics.items():
        if metrics["total_trades"] > 0 and metrics["total_return_pct"] < -10:
            risk_flags.append(
                f"Strategy loses money in {regime} markets ({metrics['total_return_pct']:.1f}%)"
            )

    if best_regime and worst_regime and regimes_with_trades:
        best_wr = regimes_with_trades[best_regime]["win_rate"]
        worst_wr = regimes_with_trades[worst_regime]["win_rate"]
        if best_wr - worst_wr > 20:
            risk_flags.append(
                f"Win rate varies significantly: {best_wr:.0f}% ({best_regime}) vs {worst_wr:.0f}% ({worst_regime})"
            )

    if dependency_level == "DEPENDENT":
        risk_flags.append(
            "High variance in performance across regimes - strategy is regime-dependent"
        )

    # Add cross-regime risk flags
    if cross_regime_analysis:
        cross_pct = cross_regime_analysis.get("cross_regime_pct", 0)
        if cross_pct > 30:
            risk_flags.append(
                f"{cross_pct:.0f}% of trades span multiple regimes - strategy holds through regime transitions"
            )

        # Check if cross-regime trades perform worse
        cross_avg = cross_regime_analysis.get("cross_regime_avg_pnl", 0)
        same_avg = cross_regime_analysis.get("same_regime_avg_pnl", 0)
        if cross_avg < same_avg - 2 and cross_regime_analysis.get("cross_regime_trades", 0) > 5:
            risk_flags.append(
                f"Cross-regime trades underperform: {cross_avg:.1f}% avg vs {same_avg:.1f}% for same-regime trades"
            )

    # Generate recommendation
    if dependency_level == "INDEPENDENT":
        recommendation = (
            "Strategy performs consistently across market regimes. "
            "Results suggest the strategy is not dependent on specific market conditions."
        )
    elif dependency_level == "MODERATE":
        recommendation = (
            "Strategy shows some variation across market regimes. "
            "Consider investigating performance in underperforming regimes. "
            "May benefit from regime-specific position sizing."
        )
    else:
        recommendation = (
            "Strategy is highly dependent on market regime. "
            f"Performs best in {best_regime} markets. "
            "Consider adding regime filters or developing separate strategies per regime."
        )

    # Add cross-regime specific recommendation
    if cross_regime_analysis and cross_regime_analysis.get("cross_regime_pct", 0) > 30:
        recommendation += (
            " Note: Many trades span regime transitions - consider shorter holding periods "
            "or regime-aware exit conditions."
        )

    report = {
        "segments": [
            {
                "start_date": str(s.start_date),
                "end_date": str(s.end_date),
                "regime": s.regime,
                "bar_count": s.bar_count,
                "features": s.features,
                "strength": s.strength,
            }
            for s in segments
        ],
        "regimes": {
            regime: {
                "percent_of_time": regime_distribution.get(regime, 0),
                **metrics,
            }
            for regime, metrics in regime_metrics.items()
        },
        "summary": {
            "total_bars": len(regime_labels),
            "total_segments": len(segments),
            "regime_distribution": regime_distribution,
            "dependency_score": dependency_score,
            "dependency_level": dependency_level,
            "best_regime": best_regime,
            "worst_regime": worst_regime,
        },
        "assessment": {
            "level": dependency_level,
            "risk_flags": risk_flags,
            "recommendation": recommendation,
        },
    }

    # Add cross-regime analysis if provided
    if cross_regime_analysis:
        report["cross_regime_analysis"] = cross_regime_analysis

    return report
