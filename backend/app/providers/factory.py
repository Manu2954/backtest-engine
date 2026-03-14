"""
Provider factory for creating data provider instances.
"""
from __future__ import annotations

from app.providers.base import DataProvider
from app.providers.openbb_provider import OpenBBProvider
from app.providers.yfinance_provider import YFinanceProvider


class ProviderFactory:
    """Factory for creating data provider instances."""

    @staticmethod
    def create_provider(provider_name: str) -> DataProvider:
        """
        Create a data provider instance.

        Args:
            provider_name: Provider identifier. Supported values:
                - "yfinance": Yahoo Finance (legacy)
                - "openbb:yfinance": OpenBB with yfinance backend
                - "openbb:fmp": OpenBB with Financial Modeling Prep
                - "openbb:polygon": OpenBB with Polygon.io
                - "openbb:<any>": OpenBB with specified backend

        Returns:
            DataProvider instance

        Raises:
            ValueError: If provider_name is not recognized
        """
        if provider_name == "yfinance":
            return YFinanceProvider()

        if provider_name.startswith("openbb:"):
            # Extract the OpenBB backend provider
            backend = provider_name.split(":", 1)[1]
            return OpenBBProvider(provider=backend)

        raise ValueError(
            f"Unknown provider: '{provider_name}'. "
            f"Supported: 'yfinance', 'openbb:yfinance', 'openbb:fmp', 'openbb:polygon'"
        )

    @staticmethod
    def get_default_provider() -> DataProvider:
        """
        Get the default provider (yfinance for backward compatibility).

        Returns:
            YFinanceProvider instance
        """
        return YFinanceProvider()
