"""
L1 Trend Filter segmentation strategy.

Method: L1 Trend Filtering (λ = k × n)
Good for: Stable trend detection with clean breakpoints
Regimes: BULL / BEAR only (2 states - inherently directional)

Labeling: Based on slope direction of filtered trend
- BULL: Positive slope (uptrend)
- BEAR: Negative slope (downtrend)

No CHOPPY/RANGING states because L1 detects slope changes,
meaning every segment has a directional trend by definition.

Reference: "l1 Trend Filtering" (Kim et al., 2009)
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from app.engine.robustness.segmentation.base import (
    SegmentationStrategy,
    LabeledSegment,
)


class L1TrendStrategy(SegmentationStrategy):
    """
    Segmentation strategy based on L1 Trend Filtering.

    Detects changepoints where trend slope changes direction.
    Labels segments as BULL or BEAR based on slope sign.

    Unlike PELT strategies, L1 produces only 2 regime types because
    it inherently detects directional trends. There is no concept of
    "sideways" or "consolidation" in L1 - every segment has a trend direction.
    """

    # Regime types for L1 trend strategy
    BULL = "BULL"
    BEAR = "BEAR"

    # Default parameters
    DEFAULT_K = 0.015  # From batch testing: k=0.015 is optimal
    SLOPE_THRESHOLD = 1e-6  # Minimum slope change to consider significant

    def __init__(self, k: float = DEFAULT_K):
        """
        Initialize L1 trend filter strategy.

        Args:
            k: Smoothing parameter (λ = k × n). Range: 0.01-0.03
               - Lower k = more segments (sensitive)
               - Higher k = fewer segments (smooth)
               Default 0.015 from batch testing.
        """
        self.k = k

    def get_strategy_name(self) -> str:
        return "l1_trend"

    def get_regime_types(self) -> list[str]:
        return [self.BULL, self.BEAR]

    def _l1_trend_filter(self, y: np.ndarray) -> np.ndarray:
        """
        Apply L1 trend filtering using cvxpy.

        Solves: minimize ||y - x||² + λ * ||D²x||₁
        where D² is the second-order difference operator.

        Args:
            y: Input signal (log prices)

        Returns:
            Filtered trend x
        """
        try:
            import cvxpy as cp
        except ImportError:
            raise ImportError(
                "cvxpy is required for L1 trend filtering. "
                "Install with: pip install cvxpy"
            )

        n = len(y)
        lambda_param = self.k * n

        # Decision variable
        x = cp.Variable(n)

        # Second-order difference matrix
        D2 = np.zeros((n - 2, n))
        for i in range(n - 2):
            D2[i, i] = 1
            D2[i, i + 1] = -2
            D2[i, i + 2] = 1

        # Objective: data fit + L1 penalty on curvature
        objective = cp.Minimize(
            cp.sum_squares(y - x) + lambda_param * cp.norm(D2 @ x, 1)
        )

        # Solve optimization problem
        prob = cp.Problem(objective)

        # Suppress cvxpy numerical warnings
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=RuntimeWarning)
            prob.solve(solver=cp.CLARABEL, verbose=False)

        if prob.status not in ["optimal", "optimal_inaccurate"]:
            raise RuntimeError(f"L1 trend filtering failed with status: {prob.status}")

        return x.value

    def _detect_slope_changes(self, trend: np.ndarray) -> list[int]:
        """
        Detect indices where slope changes sign.

        Args:
            trend: Filtered trend from L1

        Returns:
            List of breakpoint indices (not including 0 or n)
        """
        slope = np.diff(trend)
        breakpoints = []

        for i in range(1, len(slope)):
            # Check for sign change
            if slope[i - 1] * slope[i] < 0:
                # Verify magnitude is significant
                if abs(slope[i] - slope[i - 1]) > self.SLOPE_THRESHOLD:
                    breakpoints.append(i)

        return breakpoints

    def detect_changepoints(
        self,
        df: pd.DataFrame,
        penalty: float | None = None,
        min_segment_length: int = 20,
        **kwargs,
    ) -> list[int]:
        """
        Detect trend changepoints using L1 filtering.

        Note: penalty and min_segment_length parameters are ignored
        (kept for interface compatibility). L1 implicitly controls
        segmentation through the k parameter.

        Args:
            df: DataFrame with 'close' column
            penalty: Ignored (not applicable to L1)
            min_segment_length: Ignored (not applicable to L1)
            **kwargs: Ignored

        Returns:
            List of changepoint indices (including 0 and len(df))
        """
        if len(df) < 50:
            # Too few bars for L1
            return [0, len(df)]

        # Compute log prices
        log_prices = np.log(df["close"].values)

        # Apply L1 trend filter
        trend = self._l1_trend_filter(log_prices)

        # Detect slope change points
        breakpoints = self._detect_slope_changes(trend)

        # Add boundaries and return
        return [0] + breakpoints + [len(df)]

    def compute_segment_features(
        self,
        df: pd.DataFrame,
        start_idx: int,
        end_idx: int,
    ) -> dict[str, float]:
        """
        Compute features for a segment.

        For L1, we compute:
        - slope: Average slope of the filtered trend
        - price_change_pct: Actual price change percentage
        - volatility: Standard deviation of returns

        Args:
            df: Full DataFrame
            start_idx: Segment start index
            end_idx: Segment end index (exclusive)

        Returns:
            Dict of features
        """
        segment = df.iloc[start_idx:end_idx]

        if len(segment) < 2:
            return {
                "slope": 0.0,
                "price_change_pct": 0.0,
                "volatility": 0.0,
            }

        # Compute log prices for this segment
        log_prices = np.log(segment["close"].values)

        # Apply L1 filter to segment
        trend = self._l1_trend_filter(log_prices)

        # Compute average slope
        slope = (trend[-1] - trend[0]) / len(trend) if len(trend) > 1 else 0.0

        # Actual price change
        start_price = segment["close"].iloc[0]
        end_price = segment["close"].iloc[-1]
        price_change_pct = ((end_price / start_price) - 1) * 100

        # Volatility (returns std dev)
        returns = segment["close"].pct_change().dropna()
        volatility = returns.std() * 100 if len(returns) > 0 else 0.0

        return {
            "slope": float(slope),
            "price_change_pct": float(price_change_pct),
            "volatility": float(volatility),
        }

    def label_segments(
        self,
        df: pd.DataFrame,
        changepoints: list[int],
    ) -> list[LabeledSegment]:
        """
        Label segments as BULL or BEAR based on slope direction.

        L1 segments are inherently directional - they exist because
        of slope changes. Therefore, we only have 2 regime types.

        Args:
            df: Full DataFrame
            changepoints: List of changepoint indices

        Returns:
            List of LabeledSegment with BULL or BEAR labels
        """
        if len(changepoints) < 2:
            return []

        # Compute trend for entire dataset once
        log_prices = np.log(df["close"].values)
        trend = self._l1_trend_filter(log_prices)

        labeled_segments = []

        for i in range(len(changepoints) - 1):
            start_idx = changepoints[i]
            end_idx = changepoints[i + 1]

            # Extract segment trend
            seg_trend = trend[start_idx:end_idx]

            if len(seg_trend) < 2:
                # Segment too short, skip
                continue

            # Compute slope for labeling
            slope = (seg_trend[-1] - seg_trend[0]) / len(seg_trend)

            # Label based on slope direction
            regime = self.BULL if slope > 0 else self.BEAR

            # Compute segment strength (normalized absolute slope)
            # Higher absolute slope = stronger trend
            strength = min(abs(slope) * 100, 1.0)  # Cap at 1.0

            # Extract features for this segment
            features = self.compute_segment_features(df, start_idx, end_idx)

            labeled_segments.append(
                LabeledSegment(
                    start_idx=start_idx,
                    end_idx=end_idx,
                    regime=regime,
                    features=features,
                    strength=strength,
                )
            )

        return labeled_segments
