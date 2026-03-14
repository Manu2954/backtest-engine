"""
Test Binance provider specifically.

Verifies Binance API integration and data quality.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def test_binance_provider():
    """Test Binance provider with various crypto pairs."""

    from app.providers.factory import ProviderFactory

    print("=" * 80)
    print("Testing Binance Provider")
    print("=" * 80)

    # Test multiple crypto pairs
    test_cases = [
        {"ticker": "BTCUSDT", "name": "Bitcoin"},
        {"ticker": "ETHUSDT", "name": "Ethereum"},
        {"ticker": "BNBUSDT", "name": "Binance Coin"},
    ]

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 31)

    provider = ProviderFactory.create_provider("binance")
    print(f"\n✅ Provider created: {provider.get_provider_name()}")

    for test_case in test_cases:
        ticker = test_case["ticker"]
        name = test_case["name"]

        print(f"\n{'=' * 80}")
        print(f"Testing {name} ({ticker})")
        print("=" * 80)

        try:
            # Test daily data
            print(f"\n1. Fetching daily data...")
            df = await provider.fetch_ohlcv(
                ticker, start_date, end_date, interval="1d", asset_class="CRYPTO"
            )

            if df.empty:
                print(f"❌ No data returned!")
                continue

            print(f"✅ Fetched {len(df)} daily bars")
            print(f"   Date range: {df.index.min().date()} to {df.index.max().date()}")
            print(f"   First close: ${df['close'].iloc[0]:,.2f}")
            print(f"   Last close: ${df['close'].iloc[-1]:,.2f}")

            # Validate data structure
            print(f"\n2. Validating data...")
            required_cols = ["open", "high", "low", "close", "volume"]
            missing = [col for col in required_cols if col not in df.columns]

            if missing:
                print(f"❌ Missing columns: {missing}")
                continue

            print(f"✅ All required columns present")

            # Check data quality
            invalid_hl = (df["high"] < df["low"]).sum()
            invalid_close = ((df["close"] < df["low"]) | (df["close"] > df["high"])).sum()
            invalid_volume = (df["volume"] < 0).sum()

            if invalid_hl > 0:
                print(f"❌ Found {invalid_hl} bars where high < low")
            elif invalid_close > 0:
                print(f"❌ Found {invalid_close} bars where close not in [low, high]")
            elif invalid_volume > 0:
                print(f"❌ Found {invalid_volume} bars with negative volume")
            else:
                print(f"✅ Data quality checks passed")

            # Test intraday data (1 hour) - single day
            print(f"\n3. Testing intraday data (1h, IST timezone, single day manu)...")
            df_1h = await provider.fetch_ohlcv(
                ticker,
                datetime(2024, 1, 15),
                datetime(2024, 1, 16, 10, 45),  # Same day = 1 day of data
                interval="1m",
                asset_class="CRYPTO",
            )

            if not df_1h.empty:
                print(f"✅ Fetched {len(df_1h)} hourly bars")
                print(df_1h)
                print(f"   Date range: {df_1h.index.min()} to {df_1h.index.max()}")
                # For 1 full day in IST (00:00 to 23:59), should get exactly 24 bars
                if 23 <= len(df_1h) <= 25:
                    print(f"   ✅ Bar count correct for 1 day (~24 hours)")
                else:
                    print(f"   ⚠️  Expected ~24 bars for 1 day, got {len(df_1h)}")
            else:
                print(f"⚠️  No hourly data returned")

        except Exception as e:
            print(f"\n❌ Test failed for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Test error handling
    print(f"\n{'=' * 80}")
    print("Testing Error Handling")
    print("=" * 80)

    # Test invalid ticker
    print(f"\n1. Testing invalid ticker...")
    try:
        df = await provider.fetch_ohlcv(
            "INVALIDTICKER",
            start_date,
            end_date,
            interval="1d",
            asset_class="CRYPTO",
        )
        print(f"⚠️  Expected error for invalid ticker, but got data")
    except Exception as e:
        print(f"✅ Correctly raised error for invalid ticker: {type(e).__name__}")

    # Test invalid asset class
    print(f"\n2. Testing invalid asset class...")
    try:
        df = await provider.fetch_ohlcv(
            "BTCUSDT",
            start_date,
            end_date,
            interval="1d",
            asset_class="STOCK",  # Should fail
        )
        print(f"❌ Should have raised error for STOCK asset class")
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")
    except Exception as e:
        print(f"⚠️  Raised unexpected error: {type(e).__name__}: {e}")

    # Test invalid interval
    print(f"\n3. Testing invalid interval...")
    try:
        df = await provider.fetch_ohlcv(
            "BTCUSDT",
            start_date,
            end_date,
            interval="99h",  # Invalid
            asset_class="CRYPTO",
        )
        print(f"❌ Should have raised error for invalid interval")
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")
    except Exception as e:
        print(f"⚠️  Raised unexpected error: {type(e).__name__}: {e}")

    print(f"\n{'=' * 80}")
    print("✅ Binance provider testing complete!")
    print("=" * 80)


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(test_binance_provider())
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
