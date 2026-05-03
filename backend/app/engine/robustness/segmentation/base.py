"""
Base class for segmentation strategies.

Defines the contract that all segmentation strategies must implement.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass
class SegmentInfo:
    """Information about a detected segment."""
    start_idx: int
    end_idx: int  # Exclusive
    features: dict[str, float]


@dataclass
class LabeledSegment:
    """A segment with regime label and optional strength."""
    start_idx: int
    end_idx: int  # Exclusive
    regime: str
    features: dict[str, float]
    strength: float | None = None  # 0.0-1.0 for directional, None for sideways


class SegmentationStrategy(ABC):
    """
    Abstract base class for segmentation strategies.

    Each strategy defines:
    1. How to detect changepoints (boundaries between regimes)
    2. How to extract features from segments
    3. How to label segments into regime types

    This separation allows different strategies to use different
    signals for detection and different rules for classification.
    """

    @abstractmethod
    def detect_changepoints(
        self,
        df: pd.DataFrame,
        penalty: float | None = None,
        min_segment_length: int = 20,
        **kwargs,
    ) -> list[int]:
        """
        Detect regime changepoints in price data.

        Args:
            df: DataFrame with OHLCV data (must have 'close' column)
            penalty: PELT penalty parameter. If None, uses default.
            min_segment_length: Minimum bars per segment
            **kwargs: Strategy-specific parameters

        Returns:
            List of changepoint indices (including 0 and len(df))
        """
        pass

    @abstractmethod
    def compute_segment_features(
        self,
        df: pd.DataFrame,
        start_idx: int,
        end_idx: int,
    ) -> dict[str, float]:
        """
        Compute features for a single segment.

        Args:
            df: Full DataFrame
            start_idx: Segment start index
            end_idx: Segment end index (exclusive)

        Returns:
            Dict of feature name -> value
        """
        pass

    @abstractmethod
    def label_segments(
        self,
        df: pd.DataFrame,
        changepoints: list[int],
    ) -> list[LabeledSegment]:
        """
        Label segments with regime types.

        Args:
            df: Full DataFrame
            changepoints: List of changepoint indices

        Returns:
            List of LabeledSegment with regime labels and strength
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of this strategy (e.g., 'volatility', 'directional')."""
        pass

    @abstractmethod
    def get_regime_types(self) -> list[str]:
        """Return list of possible regime labels this strategy produces."""
        pass
