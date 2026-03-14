"""
Provider factory for creating data provider instances.
"""
from __future__ import annotations

from app.providers.base import DataProvider
from app.providers.yfinance_provider import YFinanceProvider


class ProviderFactory:
    """Factory for creating data provider instances."""

    @staticmethod
    def create_provider(provider_name: str) -> DataProvider:
        """
        Create a data provider instance.

        Args:
            provider_name: Provider identifier. Supported values:
                - "yfinance": Yahoo Finance (default)
                - Future: "polygon", "binance", "fmp"

        Returns:
            DataProvider instance

        Raises:
            ValueError: If provider_name is not recognized
        """
        if provider_name == "yfinance":
            return YFinanceProvider()

        raise ValueError(
            f"Unknown provider: '{provider_name}'. "
            f"Supported: 'yfinance'"
        )

    @staticmethod
    def get_default_provider() -> DataProvider:
        """
        Get the default provider (yfinance).

        Returns:
            YFinanceProvider instance
        """
        return YFinanceProvider()
