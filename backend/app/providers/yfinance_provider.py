"""
Yahoo Finance provider using yfinance library.

This is the existing/legacy provider, refactored to match the DataProvider interface.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import yfinance as yf

from app.providers.base import DataProvider


class YFinanceProvider(DataProvider):
    """Yahoo Finance data provider using yfinance library."""

    def get_provider_name(self) -> str:
        """Return provider name."""
        return "yfinance"

    async def fetch_ohlcv(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
        asset_class: str = "STOCK",
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Yahoo Finance.

        Args:
            ticker: Ticker symbol (e.g., "AAPL", "BTC-USD")
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Time interval (default: "1d")
                     Supported: "1m", "2m", "5m", "15m", "30m", "60m", "90m",
                               "1h", "1d", "5d", "1wk", "1mo", "3mo"
            asset_class: Asset class (default: "STOCK")
                        Note: yfinance handles both stocks and crypto through same API,
                        just use appropriate ticker format (e.g., "BTC-USD" for crypto)

        Returns:
            DataFrame with columns: date, open, high, low, close, volume

        Raises:
            ValueError: If ticker is invalid or no data returned
            RuntimeError: If yfinance API fails
        """
        try:
            # Download data using yfinance
            df = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                interval=interval,
                progress=False,
                auto_adjust=True,  # Adjust for splits/dividends
            )

            if df.empty:
                raise ValueError(f"No data returned for ticker '{ticker}'")

            # Handle MultiIndex columns (happens with yfinance)
            if isinstance(df.columns, pd.MultiIndex):
                # For single ticker, yfinance may still return MultiIndex
                # Try to find the level with OHLCV column names
                for level_idx in range(df.columns.nlevels):
                    level_values = [str(v).lower() for v in df.columns.get_level_values(level_idx)]
                    if any(col in level_values for col in ["open", "high", "low", "close", "volume"]):
                        df.columns = level_values
                        break
                else:
                    # If not found, take the last level
                    df.columns = [str(v).lower() for v in df.columns.get_level_values(-1)]

            # Reset index to make date a column
            df = df.reset_index()

            # Standardize column names to lowercase (if not already done)
            if not isinstance(df.columns, pd.MultiIndex):
                df.columns = [str(col).lower() for col in df.columns]

            # Handle both 'date' and 'datetime' columns (intraday uses 'datetime')
            if "datetime" in df.columns:
                df.rename(columns={"datetime": "date"}, inplace=True)

            # Ensure required columns exist
            required = ["date", "open", "high", "low", "close", "volume"]
            missing = [col for col in required if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {missing}. Found columns: {list(df.columns)}")

            # Keep only required columns
            df = df[required]

            # Set date as index
            df.set_index("date", inplace=True)

            return df

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise RuntimeError(f"yfinance fetch failed for '{ticker}': {e}") from e
