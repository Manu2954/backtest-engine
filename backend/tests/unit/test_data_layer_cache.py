"""Unit tests for data_layer cache invalidation for splits/dividends."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

from app.engine.data_layer import (
    fetch_ohlcv_async,
    RECENT_DATA_DAYS,
    STALE_CACHE_DAYS,
    get_cache_key,
    serialize_df,
    deserialize_df,
)


@pytest.fixture
def sample_ohlcv_df():
    """Create a sample OHLCV DataFrame."""
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    return pd.DataFrame(
        {
            "open": [100 + i for i in range(30)],
            "high": [102 + i for i in range(30)],
            "low": [99 + i for i in range(30)],
            "close": [101 + i for i in range(30)],
            "volume": [1000000] * 30,
        },
        index=dates,
    )


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_get_cache_key_format(self):
        key = get_cache_key("AAPL", "1d", date(2026, 1, 1), date(2026, 1, 31))
        assert key == "ohlcv:AAPL:1d:2026-01-01:2026-01-31"

    def test_get_cache_key_normalizes_ticker(self):
        key = get_cache_key("  aapl  ", "1d", date(2026, 1, 1), date(2026, 1, 31))
        assert key == "ohlcv:AAPL:1d:2026-01-01:2026-01-31"


class TestSerializationRoundtrip:
    """Tests for DataFrame serialization/deserialization."""

    def test_serialize_deserialize_roundtrip(self, sample_ohlcv_df):
        serialized = serialize_df(sample_ohlcv_df)
        deserialized = deserialize_df(serialized)

        assert len(deserialized) == len(sample_ohlcv_df)
        assert list(deserialized.columns) == list(sample_ohlcv_df.columns)
        # Check values are preserved (allowing for float precision)
        assert deserialized["close"].iloc[0] == pytest.approx(101.0)


class TestForceRefresh:
    """Tests for force_refresh parameter."""

    @pytest.mark.asyncio
    async def test_force_refresh_skips_redis_cache(self, sample_ohlcv_df):
        """force_refresh=True should skip Redis cache and delete existing key."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = serialize_df(sample_ohlcv_df)

        with patch("app.engine.data_layer._redis_client", return_value=mock_redis):
            with patch("app.engine.data_layer.create_async_engine") as mock_engine:
                with patch("app.engine.data_layer._load_db_ohlcv") as mock_load:
                    with patch("app.engine.data_layer._invalidate_stale_db_cache") as mock_invalidate:
                        with patch("app.engine.data_layer._store_db_ohlcv") as mock_store:
                            with patch("app.engine.data_layer.store_cache"):
                                with patch("app.providers.factory.ProviderFactory.create_provider") as mock_provider_factory:
                                    # Setup mocks
                                    mock_load.return_value = (pd.DataFrame(), None)
                                    mock_invalidate.return_value = None
                                    mock_store.return_value = None

                                    mock_provider = MagicMock()
                                    mock_provider.fetch_ohlcv = AsyncMock(return_value=sample_ohlcv_df)
                                    mock_provider_factory.return_value = mock_provider

                                    mock_session = AsyncMock()
                                    mock_session_maker = MagicMock(return_value=mock_session)
                                    mock_engine.return_value.dispose = AsyncMock()

                                    with patch("app.engine.data_layer.async_sessionmaker", return_value=mock_session_maker):
                                        result = await fetch_ohlcv_async(
                                            "AAPL",
                                            date(2026, 1, 1),
                                            date(2026, 1, 31),
                                            force_refresh=True,
                                        )

                                    # Verify Redis cache was deleted, not read
                                    mock_redis.delete.assert_called_once()
                                    # Verify DB cache was invalidated
                                    mock_invalidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_force_refresh_uses_redis_cache(self, sample_ohlcv_df):
        """Without force_refresh, should return Redis cached data."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = serialize_df(sample_ohlcv_df)

        with patch("app.engine.data_layer._redis_client", return_value=mock_redis):
            result = await fetch_ohlcv_async(
                "AAPL",
                date(2026, 1, 1),
                date(2026, 1, 31),
                force_refresh=False,
            )

            # Verify Redis cache was read
            mock_redis.get.assert_called_once()
            # Verify we got the cached data
            assert len(result) == 30


class TestStaleCacheInvalidation:
    """Tests for automatic cache invalidation for stale data."""

    def test_stale_cache_constants(self):
        """Verify constants are set correctly."""
        assert RECENT_DATA_DAYS == 30
        assert STALE_CACHE_DAYS == 7

    @pytest.mark.asyncio
    async def test_stale_stock_data_triggers_refresh(self):
        """Stock data older than STALE_CACHE_DAYS for recent date ranges should be refreshed."""
        from datetime import timezone as tz
        # Create a DataFrame with fetched_at from 10 days ago
        old_fetched_at = datetime.now(tz.utc).replace(tzinfo=None) - timedelta(days=10)

        sample_df = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [102, 103, 104],
                "low": [99, 100, 101],
                "close": [101, 102, 103],
                "volume": [1000000, 1000000, 1000000],
            },
            index=pd.date_range(date.today() - timedelta(days=5), periods=3, freq="D"),
        )

        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # No Redis cache

        with patch("app.engine.data_layer._redis_client", return_value=mock_redis):
            with patch("app.engine.data_layer.create_async_engine") as mock_engine:
                with patch("app.engine.data_layer._load_db_ohlcv") as mock_load:
                    with patch("app.engine.data_layer._store_db_ohlcv") as mock_store:
                        with patch("app.engine.data_layer.store_cache"):
                            with patch("app.providers.factory.ProviderFactory.create_provider") as mock_provider_factory:
                                # Return stale cached data
                                mock_load.return_value = (sample_df, old_fetched_at)
                                mock_store.return_value = None

                                # Fresh data from provider
                                fresh_df = sample_df.copy()
                                fresh_df["close"] = [150, 151, 152]  # Different values

                                mock_provider = MagicMock()
                                mock_provider.fetch_ohlcv = AsyncMock(return_value=fresh_df)
                                mock_provider_factory.return_value = mock_provider

                                mock_session = AsyncMock()
                                mock_session_maker = MagicMock(return_value=mock_session)
                                mock_engine.return_value.dispose = AsyncMock()

                                with patch("app.engine.data_layer.async_sessionmaker", return_value=mock_session_maker):
                                    # Request recent data (within RECENT_DATA_DAYS)
                                    result = await fetch_ohlcv_async(
                                        "AAPL",
                                        date.today() - timedelta(days=5),
                                        date.today(),
                                        asset_class="STOCK",
                                    )

                                # Should have fetched fresh data
                                mock_provider.fetch_ohlcv.assert_called_once()
                                # And stored it
                                mock_store.assert_called_once()


class TestCryptoNoStalenessCheck:
    """Tests that crypto data doesn't trigger staleness checks (no splits/dividends)."""

    @pytest.mark.asyncio
    async def test_crypto_skips_staleness_check(self):
        """Crypto data should not be invalidated based on age (no splits/dividends)."""
        from datetime import timezone as tz
        old_fetched_at = datetime.now(tz.utc).replace(tzinfo=None) - timedelta(days=30)  # Very old

        # Create dates that fully cover the requested range
        start = date.today() - timedelta(days=5)
        end = date.today()
        sample_df = pd.DataFrame(
            {
                "open": [50000, 50100, 50200, 50300, 50400, 50500],
                "high": [50200, 50300, 50400, 50500, 50600, 50700],
                "low": [49900, 50000, 50100, 50200, 50300, 50400],
                "close": [50100, 50200, 50300, 50400, 50500, 50600],
                "volume": [1000, 1000, 1000, 1000, 1000, 1000],
            },
            index=pd.date_range(start, end, freq="D"),
        )

        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # No Redis cache

        with patch("app.engine.data_layer._redis_client", return_value=mock_redis):
            with patch("app.engine.data_layer.create_async_engine") as mock_engine:
                with patch("app.engine.data_layer._load_db_ohlcv") as mock_load:
                    with patch("app.engine.data_layer._store_db_ohlcv") as mock_store:
                        with patch("app.engine.data_layer.store_cache"):
                            # Return old cached data - should still be used for crypto
                            mock_load.return_value = (sample_df, old_fetched_at)

                            mock_session = AsyncMock()
                            mock_session_maker = MagicMock(return_value=mock_session)
                            mock_engine.return_value.dispose = AsyncMock()

                            with patch("app.engine.data_layer.async_sessionmaker", return_value=mock_session_maker):
                                result = await fetch_ohlcv_async(
                                    "BTCUSDT",
                                    start,
                                    end,
                                    asset_class="CRYPTO",
                                )

                            # Should return cached data (no fresh fetch)
                            assert len(result) == 6
                            assert result["close"].iloc[0] == pytest.approx(50100)
                            # _store_db_ohlcv should NOT be called (used cache)
                            mock_store.assert_not_called()
