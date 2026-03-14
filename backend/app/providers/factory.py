"""
Provider factory for creating data provider instances.
"""
from __future__ import annotations

from app.providers.base import DataProvider
from app.providers.binance_provider import BinanceProvider
from app.providers.yfinance_provider import YFinanceProvider


class ProviderFactory:
    """Factory for creating data provider instances."""

    @staticmethod
    def create_provider(provider_name: str, timezone: str = "Asia/Kolkata") -> DataProvider:
        """
        Create a data provider instance.

        Args:
            provider_name: Provider identifier. Supported values:
                - "yfinance": Yahoo Finance (stocks and crypto)
                - "binance": Binance (crypto only)
                - Future: "polygon", "fmp"
            timezone: Timezone for date range interpretation (default: "Asia/Kolkata" = IST)

        Returns:
            DataProvider instance

        Raises:
            ValueError: If provider_name is not recognized
        """
        if provider_name == "yfinance":
            return YFinanceProvider(timezone=timezone)

        if provider_name == "binance":
            return BinanceProvider(timezone=timezone)

        raise ValueError(
            f"Unknown provider: '{provider_name}'. "
            f"Supported: 'yfinance', 'binance'"
        )

    @staticmethod
    def get_default_provider(timezone: str = "Asia/Kolkata") -> DataProvider:
        """
        Get the default provider (yfinance).

        Args:
            timezone: Timezone for date range interpretation (default: "Asia/Kolkata" = IST)

        Returns:
            YFinanceProvider instance
        """
        return YFinanceProvider(timezone=timezone)
