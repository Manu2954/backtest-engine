"""
Factory for creating segmentation strategy instances.
"""
from __future__ import annotations

from typing import Any, Literal

from app.engine.robustness.segmentation.base import SegmentationStrategy


StrategyName = Literal["l1_trend", "pelt_directional", "pelt_volatility"]


class SegmentationFactory:
    """Factory for creating segmentation strategy instances."""

    @staticmethod
    def create_strategy(
        strategy_name: StrategyName,
        **kwargs: Any,
    ) -> SegmentationStrategy:
        """
        Create a segmentation strategy instance.

        Args:
            strategy_name: Strategy identifier. Supported values:
                - "l1_trend": L1 Trend Filter (2 regimes: BULL/BEAR)
                - "pelt_directional": PELT with rolling_mean signal (4 regimes)
                - "pelt_volatility": PELT with returns_vol signal (4 regimes)
            **kwargs: Strategy-specific parameters:
                For "l1_trend":
                    - k: Smoothing parameter (default 0.015), range 0.01-0.03
                For "pelt_directional":
                    - r2_mode: "percentile" (default) or "fixed"
                    - r2_percentile: Percentile threshold (default 75)
                    - r2_fixed: Fixed threshold (default 0.3)
                For "pelt_volatility":
                    - (no specific parameters yet)

        Returns:
            SegmentationStrategy instance

        Raises:
            ValueError: If strategy_name is not recognized
        """
        # Import here to avoid circular imports
        from app.engine.robustness.segmentation.l1_trend_strategy import L1TrendStrategy
        from app.engine.robustness.segmentation.volatility_strategy import VolatilityStrategy
        from app.engine.robustness.segmentation.directional_strategy import DirectionalStrategy

        if strategy_name == "l1_trend":
            return L1TrendStrategy(
                k=kwargs.get("k", 0.015),
            )

        if strategy_name == "pelt_volatility":
            return VolatilityStrategy()

        if strategy_name == "pelt_directional":
            return DirectionalStrategy(
                r2_mode=kwargs.get("r2_mode", "percentile"),
                r2_percentile=kwargs.get("r2_percentile", 75),
                r2_fixed=kwargs.get("r2_fixed", 0.3),
            )

        raise ValueError(
            f"Unknown segmentation strategy: '{strategy_name}'. "
            f"Supported: 'l1_trend', 'pelt_directional', 'pelt_volatility'"
        )

    @staticmethod
    def get_default_strategy() -> SegmentationStrategy:
        """
        Get the default strategy (pelt_volatility for backward compatibility).

        Returns:
            VolatilityStrategy instance
        """
        from app.engine.robustness.segmentation.volatility_strategy import VolatilityStrategy
        return VolatilityStrategy()

    @staticmethod
    def get_available_strategies() -> list[str]:
        """Return list of available strategy names."""
        return ["l1_trend", "pelt_directional", "pelt_volatility"]
