from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import httpx
import msgpack
import pandas as pd
import redis
import yfinance as yf
from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.ohlcv import OhlcvBar

REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")
STOCK_RESOLUTIONS = {
    "1m",
    "2m",
    "5m",
    "15m",
    "30m",
    "60m",
    "90m",
    "1h",
    "1d",
    "5d",
    "1wk",
    "1mo",
    "3mo",
}
STOCK_INTRADAY_RESOLUTIONS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"}
CRYPTO_RESOLUTIONS = {
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1mo",
}
BINANCE_URL = "https://api.binance.com/api/v3"
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


def _to_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return pd.to_datetime(value).date()
    raise TypeError(f"Unsupported date type: {type(value)!r}")


def _redis_client() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=False)


def get_cache_key(ticker: str, resolution: str, start: date, end: date) -> str:
    ticker_key = ticker.upper().strip()
    return f"ohlcv:{ticker_key}:{resolution}:{start.isoformat()}:{end.isoformat()}"


def serialize_df(df: pd.DataFrame) -> bytes:
    payload: dict[str, Any] = {
        "index": [ts.isoformat() for ts in df.index],
        "columns": list(df.columns),
        "data": df.to_numpy().tolist(),
    }
    return msgpack.packb(payload, use_bin_type=True)


def deserialize_df(blob: bytes) -> pd.DataFrame:
    payload = msgpack.unpackb(blob, raw=False)
    df = pd.DataFrame(payload["data"], columns=payload["columns"])
    df.index = pd.to_datetime(payload["index"], errors="coerce")
    df.index.name = "date"
    return df


def store_cache(key: str, df: pd.DataFrame, ttl_seconds: int) -> None:
    client = _redis_client()
    payload = serialize_df(df)
    client.setex(name=key, time=ttl_seconds, value=payload)


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        levels = [
            [str(value).lower() for value in df.columns.get_level_values(i)]
            for i in range(df.columns.nlevels)
        ]
        chosen_level = None
        for idx, level in enumerate(levels):
            if set(REQUIRED_COLUMNS).issubset(set(level)):
                chosen_level = idx
                break
        if chosen_level is None:
            chosen_level = df.columns.nlevels - 1
        df.columns = levels[chosen_level]
    else:
        df.columns = [str(col).lower() for col in df.columns]

    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")

    df = df[list(REQUIRED_COLUMNS)]

    if isinstance(df.index, pd.DatetimeIndex):
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
    df = df.sort_index()
    df = df.dropna(subset=list(REQUIRED_COLUMNS))
    df.index.name = "date"
    return df


def merge_cached_range(*_args: Any, **_kwargs: Any) -> pd.DataFrame:
    """
    Placeholder for future range-merge behavior.

    When implemented, this will combine cached OHLCV segments with newly fetched
    data to satisfy requests that partially overlap the cache.
    """
    raise NotImplementedError("Range-merge caching is deferred to a later milestone.")


def _binance_symbol(ticker: str) -> str:
    symbol = ticker.upper().replace("-", "").replace("/", "").strip()
    return symbol


def _fetch_binance_ohlcv(
    symbol: str, start: date, end: date, resolution: str
) -> pd.DataFrame:
    if resolution not in CRYPTO_RESOLUTIONS:
        raise ValueError(f"Unsupported crypto resolution: {resolution}")

    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time())
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    interval_ms = BINANCE_INTERVAL_MS[resolution]

    rows: list[list[Any]] = []
    with httpx.Client(timeout=20.0) as client:
        while start_ms < end_ms:
            params = {
                "symbol": symbol,
                "interval": resolution,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000,
            }
            response = client.get(f"{BINANCE_URL}/klines", params=params)
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            rows.extend(data)
            last_open = data[-1][0]
            start_ms = last_open + interval_ms

    if not rows:
        return pd.DataFrame()

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
    df["date"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.set_index("date")[["open", "high", "low", "close", "volume"]].astype(float)
    return df


def _to_datetime_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time())
    return start_dt, end_dt


async def _load_db_ohlcv(
    session: AsyncSession,
    ticker: str,
    asset: str,
    resolution: str,
    start: date,
    end: date,
) -> pd.DataFrame:
    start_dt, end_dt = _to_datetime_bounds(start, end)
    stmt = (
        select(
            OhlcvBar.ts,
            OhlcvBar.open,
            OhlcvBar.high,
            OhlcvBar.low,
            OhlcvBar.close,
            OhlcvBar.volume,
        )
        .where(
            and_(
                OhlcvBar.ticker == ticker.upper(),
                OhlcvBar.asset_class == asset,
                OhlcvBar.resolution == resolution,
                OhlcvBar.ts >= start_dt,
                OhlcvBar.ts < end_dt,
            )
        )
        .order_by(OhlcvBar.ts.asc())
    )
    result = await session.execute(stmt)
    rows = result.all()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df = df.set_index("date")
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    return df


async def _store_db_ohlcv(
    session: AsyncSession,
    df: pd.DataFrame,
    ticker: str,
    asset: str,
    resolution: str,
    own_session: bool,
) -> None:
    if df.empty:
        return
    records: list[dict[str, Any]] = []
    for ts, row in df.iterrows():
        records.append(
            {
                "ticker": ticker.upper(),
                "asset_class": asset,
                "resolution": resolution,
                "ts": ts.to_pydatetime(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
        )

    batch_size = 500
    for i in range(0, len(records), batch_size):
        chunk = records[i : i + batch_size]
        stmt = pg_insert(OhlcvBar).values(chunk)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["ticker", "asset_class", "resolution", "ts"]
        )
        await session.execute(stmt)
    if own_session:
        await session.commit()
    else:
        await session.flush()


async def fetch_ohlcv_async(
    ticker: str,
    start: str | date | datetime,
    end: str | date | datetime,
    resolution: str = "1d",
    asset_class: str = "STOCK",
    session: AsyncSession | None = None,
    provider: str | None = None,
    timezone: str = "Asia/Kolkata",
) -> pd.DataFrame:
    """
    Fetch OHLCV data from cache, database, or external API.

    Bug Fix #10: Added gap detection for cached database data.
    Previously, only checked if min/max dates covered the range, which could
    return incomplete data (e.g., Jan 1-5 and Jan 25-31 would pass for Jan 1-31).
    Now checks data completeness using bar count heuristics before serving from cache.

    Args:
        ticker: Stock/crypto ticker symbol
        start: Start date
        end: End date
        resolution: Time resolution (e.g., "1d", "1h")
        asset_class: "STOCK" or "CRYPTO"
        session: Optional database session
        provider: Data provider to use (optional)
                 Supported: "yfinance", "binance"
                 If None, defaults to:
                   - "yfinance" for STOCK
                   - "binance" for CRYPTO
        timezone: Timezone for date range interpretation (default: "Asia/Kolkata" = IST)

    Returns:
        DataFrame with OHLCV data
    """
    asset = asset_class.upper()
    resolution = resolution.lower()
    if asset == "STOCK" and resolution not in STOCK_RESOLUTIONS:
        raise ValueError(f"Unsupported stock resolution: {resolution}")
    if asset == "CRYPTO" and resolution not in CRYPTO_RESOLUTIONS:
        raise ValueError(f"Unsupported crypto resolution: {resolution}")
    if asset not in {"STOCK", "CRYPTO"}:
        raise ValueError(f"Unsupported asset class: {asset}")

    start_date = _to_date(start)
    end_date = _to_date(end)

    key = get_cache_key(ticker, resolution, start_date, end_date)
    client = _redis_client()
    cached_blob = client.get(key)
    if cached_blob:
        cached_df = deserialize_df(cached_blob)
        if not cached_df.empty:
            return cached_df

    own_session = False
    engine = None
    if session is None:
        engine = create_async_engine(
            settings.database_url, echo=False, future=True, poolclass=NullPool
        )
        session_maker = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        session = session_maker()
        own_session = True

    try:
        db_df = await _load_db_ohlcv(session, ticker, asset, resolution, start_date, end_date)
        if not db_df.empty:
            covers_start = db_df.index.min().date() <= start_date
            covers_end = db_df.index.max().date() >= end_date

            if covers_start and covers_end:
                # Check for data completeness (rough heuristic to detect gaps)
                # For daily data, expect ~70% coverage (accounting for weekends)
                # For intraday, this check is less reliable, so we're more lenient
                expected_days = (end_date - start_date).days
                actual_bars = len(db_df)

                # Daily data should have at least 60% coverage (5/7 days minus holidays)
                # Intraday can vary greatly, so we use a lower threshold
                if resolution == "1d":
                    min_expected_bars = expected_days * 0.6
                else:
                    # For intraday, just check we have some reasonable amount of data
                    # Don't enforce strict coverage due to market hours variation
                    min_expected_bars = 1

                if actual_bars >= min_expected_bars:
                    store_cache(key, db_df, settings.ohlcv_cache_ttl_seconds)
                    return db_df
                # else: fall through to re-fetch (likely has gaps)

        if asset == "STOCK" and resolution in STOCK_INTRADAY_RESOLUTIONS:
            max_days = 60
            span_days = (end_date - start_date).days
            if span_days > max_days:
                if not db_df.empty:
                    return db_df
                raise ValueError(
                    "Intraday stock data cannot extend beyond last 60 days for Yahoo data."
                )

        if asset == "STOCK":
            # Always use provider system
            if provider is None:
                provider = "yfinance"  # Default provider for stocks

            from app.providers.factory import ProviderFactory

            data_provider = ProviderFactory.create_provider(provider, timezone=timezone)
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.min.time())
            df = await data_provider.fetch_ohlcv(
                ticker, start_dt, end_dt, interval=resolution, asset_class=asset
            )
        else:
            # CRYPTO asset class
            if provider is None:
                provider = "binance"  # Default provider for crypto

            from app.providers.factory import ProviderFactory

            data_provider = ProviderFactory.create_provider(provider, timezone=timezone)
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.min.time())
            df = await data_provider.fetch_ohlcv(
                ticker, start_dt, end_dt, interval=resolution, asset_class=asset
            )

        df = _normalize_df(df)
        if df.empty:
            raise ValueError(
                f"No OHLCV data for {ticker} in range {start_date.isoformat()} to {end_date.isoformat()}"
            )

        await _store_db_ohlcv(session, df, ticker, asset, resolution, own_session)
        store_cache(key, df, settings.ohlcv_cache_ttl_seconds)
        return df
    finally:
        if own_session and session is not None:
            await session.close()
        if engine is not None:
            await engine.dispose()


def fetch_ohlcv(
    ticker: str,
    start: str | date | datetime,
    end: str | date | datetime,
    resolution: str = "1d",
    asset_class: str = "STOCK",
    provider: str | None = None,
    timezone: str = "Asia/Kolkata",
) -> pd.DataFrame:
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            fetch_ohlcv_async(
                ticker,
                start,
                end,
                resolution=resolution,
                asset_class=asset_class,
                provider=provider,
                timezone=timezone,
            )
        )
    raise RuntimeError("fetch_ohlcv cannot be called from an active event loop; use fetch_ohlcv_async.")


def validate_ticker(ticker: str, asset_class: str = "STOCK") -> bool:
    """
    Validate that a ticker symbol is valid and returns data.

    Uses the provider system to attempt fetching recent data.

    Args:
        ticker: Ticker symbol to validate
        asset_class: "STOCK" or "CRYPTO"

    Returns:
        True if ticker is valid, False otherwise
    """
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=7)

    try:
        # Use fetch_ohlcv which goes through provider system
        df = fetch_ohlcv(
            ticker=ticker,
            start=start_date,
            end=end_date,
            resolution="1d",
            asset_class=asset_class,
        )
        return not df.empty
    except Exception:
        return False
