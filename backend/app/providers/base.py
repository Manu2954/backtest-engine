"""
Base provider interface.

Defines the contract that all data providers must implement.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd


class DataProvider(ABC):
    """Abstract base class for market data providers."""

    @abstractmethod
    async def fetch_ohlcv(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a ticker symbol.

        Args:
            ticker: Ticker symbol (e.g., "AAPL", "BTC-USD")
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Time interval/resolution (default: "1d" for daily)
                     Supported values depend on provider:
                     - "1m", "5m", "15m", "30m", "60m" (intraday)
                     - "1h", "4h" (hourly)
                     - "1d" (daily)
                     - "1wk" (weekly)
                     - "1mo" (monthly)

        Returns:
            DataFrame with columns: date, open, high, low, close, volume
            Index: datetime index
            All column names lowercase

        Raises:
            ValueError: If ticker is invalid or data is unavailable
            RuntimeError: If provider API fails
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider (e.g., 'yfinance', 'openbb')."""
        pass
