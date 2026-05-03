"""
Volatility-based segmentation strategy.

Signal: [log_returns, rolling_vol]
Good for: Detecting volatility regime shifts (calm vs turbulent periods)
Limitation: May miss trend reversals if volatility stays similar

Labeling: Based on volatility level relative to median
- HIGH_VOL: High volatility regime
- LOW_VOL: Low volatility regime
- TRANSITION: Mixed volatility
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import ruptures as rpt

from app.engine.robustness.segmentation.base import (
    SegmentationStrategy,
    LabeledSegment,
)


class VolatilityStrategy(SegmentationStrategy):
    """
    Segmentation strategy based on volatility regimes.

    Detects changepoints where volatility characteristics shift.
    Labels segments as HIGH_VOL, LOW_VOL, or TRANSITION based on
    average volatility relative to the overall median.
    """

    # Regime types for volatility strategy
    HIGH_VOL = "HIGH_VOL"
    LOW_VOL = "LOW_VOL"
    TRANSITION = "TRANSITION"

    def __init__(self, vol_window: int = 20):
        """
        Initialize volatility strategy.

        Args:
            vol_window: Window for rolling volatility calculation
        """
        self.vol_window = vol_window

    def get_strategy_name(self) -> str:
        return "volatility"

    def get_regime_types(self) -> list[str]:
        return [self.HIGH_VOL, self.LOW_VOL, self.TRANSITION]

    def _compute_log_returns(self, df: pd.DataFrame) -> pd.Series:
        """Compute log returns from close prices."""
        return np.log(df["close"] / df["close"].shift(1))

    def _compute_rolling_volatility(self, log_returns: pd.Series) -> pd.Series:
        """Compute rolling volatility (std of log returns)."""
        return log_returns.rolling(window=self.vol_window, min_periods=self.vol_window).std()

    def detect_changepoints(
        self,
        df: pd.DataFrame,
        penalty: float | None = None,
        min_segment_length: int = 20,
        **kwargs,
    ) -> list[int]:
        """
        Detect volatility regime changepoints using PELT.

        Signal: [log_returns, rolling_vol]
        """
        # Compute signals
        log_returns = self._compute_log_returns(df)
        rolling_vol = self._compute_rolling_volatility(log_returns)

        # Create multivariate signal
        signal = pd.DataFrame({
            "log_returns": log_returns,
            "rolling_vol": rolling_vol,
        }).dropna()

        if len(signal) < min_segment_length * 2:
            return [0, len(df)]

        # Normalize features for PELT
        signal_normalized = (signal - signal.mean()) / signal.std()
        signal_array = signal_normalized.values

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
        Compute volatility-focused features for a segment.

        Features:
        - mean_vol: Average rolling volatility
        - std_vol: Volatility of volatility
        - mean_return: Average daily return
        - max_drawdown: Maximum drawdown in segment
        """
        segment = df.iloc[start_idx:end_idx]

        if len(segment) < 3:
            return {
                "mean_vol": 0.0,
                "std_vol": 0.0,
                "mean_return": 0.0,
                "max_drawdown": 0.0,
            }

        log_returns = self._compute_log_returns(segment)
        rolling_vol = self._compute_rolling_volatility(log_returns)

        # Mean and std of volatility
        valid_vol = rolling_vol.dropna()
        mean_vol = valid_vol.mean() if len(valid_vol) > 0 else 0.0
        std_vol = valid_vol.std() if len(valid_vol) > 1 else 0.0

        # Returns
        returns = segment["close"].pct_change().dropna()
        mean_return = returns.mean() * 100 if len(returns) > 0 else 0.0

        # Max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100 if len(drawdown) > 0 else 0.0

        return {
            "mean_vol": float(mean_vol),
            "std_vol": float(std_vol),
            "mean_return": float(mean_return),
            "max_drawdown": float(max_drawdown),
        }

    def label_segments(
        self,
        df: pd.DataFrame,
        changepoints: list[int],
    ) -> list[LabeledSegment]:
        """
        Label segments based on volatility level.

        Rules:
        - mean_vol > overall_median * 1.2 → HIGH_VOL
        - mean_vol < overall_median * 0.8 → LOW_VOL
        - Otherwise → TRANSITION
        """
        # Extract features for all segments
        segment_features = []
        for i in range(len(changepoints) - 1):
            start_idx = changepoints[i]
            end_idx = changepoints[i + 1]
            features = self.compute_segment_features(df, start_idx, end_idx)
            segment_features.append(features)

        # Compute overall median volatility
        all_vols = [f["mean_vol"] for f in segment_features if f["mean_vol"] > 0]
        median_vol = np.median(all_vols) if all_vols else 0.0

        # Label each segment
        labeled_segments = []
        for i, features in enumerate(segment_features):
            start_idx = changepoints[i]
            end_idx = changepoints[i + 1]

            mean_vol = features["mean_vol"]

            if median_vol > 0:
                if mean_vol > median_vol * 1.2:
                    regime = self.HIGH_VOL
                elif mean_vol < median_vol * 0.8:
                    regime = self.LOW_VOL
                else:
                    regime = self.TRANSITION
            else:
                regime = self.TRANSITION

            # Strength: how far from median (normalized)
            if median_vol > 0:
                strength = abs(mean_vol - median_vol) / median_vol
                strength = min(1.0, strength)  # Cap at 1.0
            else:
                strength = 0.0

            labeled_segments.append(LabeledSegment(
                start_idx=start_idx,
                end_idx=end_idx,
                regime=regime,
                features=features,
                strength=round(strength, 4),
            ))

        return labeled_segments
