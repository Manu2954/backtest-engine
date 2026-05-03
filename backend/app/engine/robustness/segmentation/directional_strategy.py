"""
Directional segmentation strategy.

Signal: rolling_mean(log_returns)
Good for: Detecting trend reversals (up→down, down→up)
Limitation: May miss volatility regime changes within same trend

Labeling: Based on OLS slope and R² (trend quality)
- BULL: Positive trend with good fit
- BEAR: Negative trend with good fit
- CHOPPY: Poor trend fit, high volatility
- RANGING: Poor trend fit, low volatility
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import ruptures as rpt
from scipy import stats

from app.engine.robustness.segmentation.base import (
    SegmentationStrategy,
    LabeledSegment,
)


class DirectionalStrategy(SegmentationStrategy):
    """
    Segmentation strategy based on trend direction.

    Detects changepoints where trend direction changes.
    Labels segments as BULL, BEAR, CHOPPY, or RANGING based on
    OLS regression slope and R² quality metrics.
    """

    # Regime types for directional strategy
    BULL = "BULL"
    BEAR = "BEAR"
    CHOPPY = "CHOPPY"
    RANGING = "RANGING"

    # Thresholds
    SLOPE_TOLERANCE = 1e-6
    DEFAULT_R2_PERCENTILE = 75  # Top 25% considered directional
    DEFAULT_R2_FIXED = 0.3  # Fixed threshold when mode is "fixed"

    def __init__(
        self,
        vol_window: int = 20,
        r2_mode: str = "percentile",
        r2_percentile: float = 75,
        r2_fixed: float = 0.3,
    ):
        """
        Initialize directional strategy.

        Args:
            vol_window: Window for rolling mean calculation
            r2_mode: "percentile" (adaptive) or "fixed" threshold mode
            r2_percentile: Percentile value when mode is "percentile" (default 75 = top 25%)
            r2_fixed: Fixed R² threshold when mode is "fixed" (default 0.3)
        """
        self.vol_window = vol_window
        self.r2_mode = r2_mode
        self.r2_percentile = r2_percentile
        self.r2_fixed = r2_fixed

    def get_strategy_name(self) -> str:
        return "directional"

    def get_regime_types(self) -> list[str]:
        return [self.BULL, self.BEAR, self.CHOPPY, self.RANGING]

    def _compute_log_returns(self, df: pd.DataFrame) -> pd.Series:
        """Compute log returns from close prices."""
        return np.log(df["close"] / df["close"].shift(1))

    def detect_changepoints(
        self,
        df: pd.DataFrame,
        penalty: float | None = None,
        min_segment_length: int = 20,
        **kwargs,
    ) -> list[int]:
        """
        Detect trend reversal changepoints using PELT.

        Signal: rolling_mean(log_returns)
        """
        # Compute rolling mean of returns
        log_returns = self._compute_log_returns(df)
        rolling_mean = log_returns.rolling(window=self.vol_window, min_periods=self.vol_window).mean()

        # Drop NaN and reshape for PELT
        signal = rolling_mean.dropna()

        if len(signal) < min_segment_length * 2:
            return [0, len(df)]

        # Normalize for PELT
        signal_normalized = (signal - signal.mean()) / signal.std()
        signal_array = signal_normalized.values.reshape(-1, 1)

        # Default penalty
        n = len(signal_array)
        if penalty is None:
            penalty = np.log(n)

        # Run PELT with RBF kernel
        algo = rpt.Pelt(model="rbf", min_size=min_segment_length).fit(signal_array)
        changepoints = algo.predict(pen=penalty)

        # Adjust indices for dropped NaN rows
        offset = len(df) - len(signal)
        changepoints = [cp + offset for cp in changepoints]

        # Ensure we have start and end
        if changepoints[0] != 0:
            changepoints = [0] + changepoints
        if changepoints[-1] != len(df):
            changepoints[-1] = len(df)

        return changepoints

    def compute_segment_features(
        self,
        df: pd.DataFrame,
        start_idx: int,
        end_idx: int,
    ) -> dict[str, float]:
        """
        Compute trend-focused features for a segment.

        Features:
        - slope: Normalized OLS slope (% per bar)
        - r_squared: Coefficient of determination (trend quality)
        - mean_return: Average daily return %
        - std_return: Standard deviation of returns %
        - trend_score: slope * r_squared (combined metric)
        """
        segment = df.iloc[start_idx:end_idx]

        if len(segment) < 3:
            return {
                "slope": 0.0,
                "r_squared": 0.0,
                "mean_return": 0.0,
                "std_return": 0.0,
                "trend_score": 0.0,
            }

        # OLS regression on close prices
        y = segment["close"].values
        x = np.arange(len(y))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # Normalize slope by mean price (percentage slope per bar)
        mean_price = y.mean()
        slope_pct = (slope / mean_price) * 100 if mean_price != 0 else 0.0

        # R²
        r_squared = r_value ** 2

        # Compute returns for mean and std
        returns = segment["close"].pct_change().dropna()

        if len(returns) == 0:
            mean_return = 0.0
            std_return = 0.0
        else:
            mean_return = returns.mean() * 100
            std_return = returns.std() * 100

        # Combined trend score
        trend_score = slope_pct * r_squared

        return {
            "slope": float(slope_pct),
            "r_squared": float(r_squared),
            "mean_return": float(mean_return),
            "std_return": float(std_return),
            "trend_score": float(trend_score),
        }

    def label_segments(
        self,
        df: pd.DataFrame,
        changepoints: list[int],
    ) -> list[LabeledSegment]:
        """
        Label segments based on trend quality (R²) and direction (slope).

        R² threshold modes:
        - "percentile": Adaptive threshold based on data distribution (default)
        - "fixed": Fixed threshold (default 0.3)

        Rules:
        - R² >= threshold AND slope > 0 → BULL
        - R² >= threshold AND slope < 0 → BEAR
        - R² < threshold AND std_return > median → CHOPPY
        - R² < threshold AND std_return <= median → RANGING

        Strength (for BULL/BEAR):
        - Relative position of trend_score among same-direction segments
        """
        # Extract features for all segments
        segment_features = []
        for i in range(len(changepoints) - 1):
            start_idx = changepoints[i]
            end_idx = changepoints[i + 1]
            features = self.compute_segment_features(df, start_idx, end_idx)
            segment_features.append(features)

        if not segment_features:
            return []

        # Compute R² threshold based on mode
        all_r2 = [f["r_squared"] for f in segment_features]
        if self.r2_mode == "percentile":
            r2_threshold = np.percentile(all_r2, self.r2_percentile)
        else:
            r2_threshold = self.r2_fixed

        # Compute median std_return for CHOPPY vs RANGING split
        all_stds = [f["std_return"] for f in segment_features]
        median_std = np.median(all_stds)

        # Collect trend scores for strength calculation (using computed threshold)
        bull_scores = [
            f["trend_score"]
            for f in segment_features
            if f["r_squared"] >= r2_threshold and f["slope"] > self.SLOPE_TOLERANCE
        ]
        bear_scores = [
            f["trend_score"]
            for f in segment_features
            if f["r_squared"] >= r2_threshold and f["slope"] < -self.SLOPE_TOLERANCE
        ]

        # Label each segment
        labeled_segments = []
        for i, features in enumerate(segment_features):
            start_idx = changepoints[i]
            end_idx = changepoints[i + 1]

            slope = features["slope"]
            r_squared = features["r_squared"]
            std_return = features["std_return"]
            trend_score = features["trend_score"]

            # Determine regime using computed threshold
            if r_squared >= r2_threshold and abs(slope) > self.SLOPE_TOLERANCE:
                # Directional regime
                if slope > 0:
                    regime = self.BULL
                    strength = self._compute_strength(trend_score, bull_scores)
                else:
                    regime = self.BEAR
                    strength = self._compute_strength(trend_score, bear_scores)
            else:
                # Sideways regime
                if std_return > median_std:
                    regime = self.CHOPPY
                else:
                    regime = self.RANGING
                strength = None

            labeled_segments.append(LabeledSegment(
                start_idx=start_idx,
                end_idx=end_idx,
                regime=regime,
                features=features,
                strength=strength,
            ))

        return labeled_segments

    def _compute_strength(
        self,
        trend_score: float,
        same_dir_scores: list[float],
    ) -> float:
        """
        Compute strength (0.0-1.0) relative to peers in same direction.
        """
        if len(same_dir_scores) <= 1:
            return 1.0

        dir_min = min(same_dir_scores)
        dir_max = max(same_dir_scores)
        range_val = dir_max - dir_min

        if range_val < 1e-9:
            return 1.0

        strength = (trend_score - dir_min) / range_val
        return round(max(0.0, min(1.0, strength)), 4)
