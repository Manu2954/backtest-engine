"""
OpenBB provider for market data.

Uses OpenBB Platform to fetch historical OHLCV data.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from app.providers.base import DataProvider


class OpenBBProvider(DataProvider):
    """OpenBB Platform data provider."""

    def __init__(self, provider: str = "yfinance"):
        """
        Initialize OpenBB provider.

        Args:
            provider: Underlying OpenBB provider to use (e.g., 'yfinance', 'fmp', 'polygon')
                     Default is 'yfinance' which requires no API key.
        """
        self.openbb_provider = provider

    def get_provider_name(self) -> str:
        """Return provider name."""
        return f"openbb:{self.openbb_provider}"

    async def fetch_ohlcv(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
        asset_class: str = "STOCK",
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from OpenBB Platform.

        Args:
            ticker: Ticker symbol (e.g., "AAPL", "BTC-USD")
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Time interval (default: "1d")
                     Note: OpenBB uses 'timeseries_period' parameter.
                     Supported values depend on the underlying provider.
                     Common: "1d" (daily), "1h" (hourly), "1m" (1-minute)
            asset_class: Asset class (default: "STOCK")
                        - "STOCK": Use obb.equity.price.historical()
                        - "CRYPTO": Use obb.crypto.price.historical()

        Returns:
            DataFrame with columns: date, open, high, low, close, volume

        Raises:
            ValueError: If ticker is invalid or no data returned
            RuntimeError: If OpenBB API fails
        """
        try:
            from openbb import obb

            # Map common interval formats to OpenBB timeseries_period
            # OpenBB typically uses: 1m, 5m, 15m, 30m, 1h, 4h, 1d
            interval_map = {
                "1min": "1m",
                "5min": "5m",
                "15min": "15m",
                "30min": "30m",
                "60min": "1h",
                "1h": "1h",
                "4h": "4h",
                "1d": "1d",
                "1day": "1d",
            }

            # Use mapped interval or pass through if already in correct format
            obb_interval = interval_map.get(interval, interval)

            # Select appropriate OpenBB endpoint based on asset class
            asset = asset_class.upper()

            if asset == "STOCK":
                # Fetch equity data
                result = obb.equity.price.historical(
                    symbol=ticker,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    provider=self.openbb_provider,
                    timeseries_period=obb_interval if obb_interval != "1d" else None,
                )
            elif asset == "CRYPTO":
                # Fetch crypto data
                result = obb.crypto.price.historical(
                    symbol=ticker,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    provider=self.openbb_provider,
                    timeseries_period=obb_interval if obb_interval != "1d" else None,
                )
            else:
                raise ValueError(f"Unsupported asset class: {asset}. Use 'STOCK' or 'CRYPTO'")

            if not result or not hasattr(result, "results") or not result.results:
                raise ValueError(f"No data returned for ticker '{ticker}'")

            # Convert to DataFrame
            records = []
            for bar in result.results:
                records.append({
                    "date": bar.date,
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": float(bar.volume) if bar.volume else 0.0,
                })

            df = pd.DataFrame(records)

            if df.empty:
                raise ValueError(f"No data returned for ticker '{ticker}'")

            # Convert date column to datetime
            df["date"] = pd.to_datetime(df["date"])

            # Set date as index
            df.set_index("date", inplace=True)

            # Sort by date (ascending)
            df.sort_index(inplace=True)

            return df

        except ImportError as e:
            raise RuntimeError(
                "OpenBB is not installed. Install with: pip install openbb"
            ) from e
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise RuntimeError(
                f"OpenBB fetch failed for '{ticker}' (provider={self.openbb_provider}, asset={asset_class}): {e}"
            ) from e
