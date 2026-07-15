"""
Binance provider for cryptocurrency data.

Uses Binance public API for OHLCV data (no API key required).
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pandas as pd

from app.providers.base import DataProvider

# DATA-007 FIX: Use spot API by default, futures API when explicitly requested
# Futures prices include funding rates and can diverge significantly from spot
BINANCE_SPOT_URL = "https://api.binance.com/api/v3"
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1"
BINANCE_INTERVAL_MS = {
    "1m": 1 * 60 * 1000,
    "3m": 3 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "2h": 2 * 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "6h": 6 * 60 * 60 * 1000,
    "8h": 8 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "3d": 3 * 24 * 60 * 60 * 1000,
    "1w": 7 * 24 * 60 * 60 * 1000,
    "1mo": 30 * 24 * 60 * 60 * 1000,
}


class BinanceProvider(DataProvider):
    """Binance cryptocurrency data provider."""

    def __init__(self, timezone: str = "Asia/Kolkata", market_type: str = "SPOT"):
        """
        Initialize Binance provider.

        Args:
            timezone: Timezone for date range interpretation (default: "Asia/Kolkata" = IST)
                     Binance API operates in UTC, but dates will be converted from this timezone.
            market_type: Market type - "SPOT" (default) or "FUTURES"
                        SPOT uses api.binance.com, FUTURES uses fapi.binance.com
        """
        self.timezone = ZoneInfo(timezone)
        self.market_type = market_type.upper()
        if self.market_type not in ("SPOT", "FUTURES"):
            raise ValueError(f"Invalid market_type: {market_type}. Must be SPOT or FUTURES.")
        self.base_url = BINANCE_SPOT_URL if self.market_type == "SPOT" else BINANCE_FUTURES_URL

    def get_provider_name(self) -> str:
        """Return provider name."""
        return "binance"

    def _normalize_symbol(self, ticker: str) -> str:
        """
        Normalize ticker symbol to Binance format.

        Args:
            ticker: Ticker symbol (e.g., "BTC-USD", "BTCUSDT", "BTC/USDT")

        Returns:
            Binance symbol format (e.g., "BTCUSDT")
        """
        symbol = ticker.upper().replace("-", "").replace("/", "").strip()
        return symbol

    async def fetch_ohlcv(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
        asset_class: str = "CRYPTO",
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Binance API.

        Args:
            ticker: Ticker symbol (e.g., "BTCUSDT", "BTC-USD", "BTC/USDT")
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Time interval (default: "1d")
                     Supported: "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h",
                               "6h", "8h", "12h", "1d", "3d", "1w", "1mo"
            asset_class: Asset class (must be "CRYPTO" for Binance)

        Returns:
            DataFrame with columns: date, open, high, low, close, volume

        Raises:
            ValueError: If ticker is invalid, no data returned, or asset_class is not CRYPTO
            RuntimeError: If Binance API fails
        """
        if asset_class.upper() != "CRYPTO":
            raise ValueError(
                f"BinanceProvider only supports CRYPTO asset class, got '{asset_class}'"
            )

        if interval not in BINANCE_INTERVAL_MS:
            raise ValueError(
                f"Unsupported interval: '{interval}'. "
                f"Supported: {list(BINANCE_INTERVAL_MS.keys())}"
            )

        try:
            symbol = self._normalize_symbol(ticker)

            # Convert dates to timestamps (interpreting input dates as local timezone)
            # If datetime has time component, use it; otherwise use start of day
            if isinstance(start_date, datetime):
                start_dt = start_date
            else:
                start_dt = datetime.combine(start_date, datetime.min.time())

            # Make timezone-aware if not already
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=self.timezone)

            # Handle end_date similarly
            if isinstance(end_date, datetime):
                end_dt = end_date
            else:
                end_dt = datetime.combine(end_date, datetime.min.time())
                # DATA-005 FIX: Don't add 1 day here - caller (data_layer) already
                # handles inclusive date ranges. Adding here causes 2-day over-fetch.

            # Make timezone-aware if not already
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=self.timezone)

            # Convert to UTC timestamps (Binance uses UTC)
            start_ms = int(start_dt.astimezone(ZoneInfo("UTC")).timestamp() * 1000)
            end_ms = int(end_dt.astimezone(ZoneInfo("UTC")).timestamp() * 1000)
            interval_ms = BINANCE_INTERVAL_MS[interval]

            # Fetch data in batches (Binance limits to 1000 bars per request)
            # Rate limiting: 600 requests per minute (stay well below Binance's 1200/min limit)
            rows = []
            request_count = 0
            rate_limit_start = time.time()

            with httpx.Client(timeout=20.0) as client:
                current_start = start_ms
                while current_start < end_ms:
                    # Rate limiting: max 600 requests per 60 seconds
                    if request_count >= 600:
                        elapsed = time.time() - rate_limit_start
                        if elapsed < 60:
                            sleep_time = 60 - elapsed
                            time.sleep(sleep_time)
                        # Reset counter
                        request_count = 0
                        rate_limit_start = time.time()

                    params = {
                        "symbol": symbol,
                        "interval": interval,
                        "startTime": current_start,
                        "endTime": end_ms,
                        "limit": 1000,
                    }
                    response = client.get(f"{self.base_url}/klines", params=params)
                    response.raise_for_status()
                    data = response.json()
                    request_count += 1

                    if not data:
                        break

                    rows.extend(data)
                    last_open_time = data[-1][0]
                    current_start = last_open_time + interval_ms

                    # Small delay between requests to be a good API citizen
                    time.sleep(0.1)

            if not rows:
                raise ValueError(f"No data returned for ticker '{ticker}'")

            # Convert to DataFrame
            df = pd.DataFrame(
                rows,
                columns=[
                    "open_time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "close_time",
                    "quote_asset_volume",
                    "number_of_trades",
                    "taker_buy_base",
                    "taker_buy_quote",
                    "ignore",
                ],
            )

            # Convert timestamp to datetime (Binance returns UTC timestamps)
            # DATA-001 FIX: Keep as naive UTC (don't convert to local timezone)
            # All providers should return naive UTC for consistent date alignment
            df["date"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)

            # Remove timezone info to keep as naive UTC
            df["date"] = df["date"].dt.tz_localize(None)

            # Select and convert required columns
            df = df[["date", "open", "high", "low", "close", "volume"]]
            df = df.astype(
                {
                    "open": float,
                    "high": float,
                    "low": float,
                    "close": float,
                    "volume": float,
                }
            )

            # Set date as index
            df.set_index("date", inplace=True)

            # Sort by date
            df.sort_index(inplace=True)

            return df

        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Binance API error for '{ticker}': {e.response.status_code} {e.response.text}"
            ) from e
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise RuntimeError(f"Binance fetch failed for '{ticker}': {e}") from e
