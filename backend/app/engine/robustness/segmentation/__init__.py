"""
Pluggable segmentation strategies for regime detection.

Each strategy implements:
- detect_changepoints(): Find regime boundaries
- label_segments(): Classify segments into regimes

Available strategies:
- L1TrendStrategy: L1 Trend Filter (2 regimes: BULL/BEAR)
- DirectionalStrategy: PELT rolling_mean (4 regimes)
- VolatilityStrategy: PELT returns_vol (4 regimes)
"""
from app.engine.robustness.segmentation.base import SegmentationStrategy
from app.engine.robustness.segmentation.factory import SegmentationFactory
from app.engine.robustness.segmentation.l1_trend_strategy import L1TrendStrategy
from app.engine.robustness.segmentation.volatility_strategy import VolatilityStrategy
from app.engine.robustness.segmentation.directional_strategy import DirectionalStrategy

__all__ = [
    "SegmentationStrategy",
    "SegmentationFactory",
    "L1TrendStrategy",
    "VolatilityStrategy",
    "DirectionalStrategy",
]
