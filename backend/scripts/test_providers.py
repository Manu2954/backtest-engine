"""
Test data providers.

Tests both YFinance and OpenBB providers.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def test_providers():
    """Test all data providers."""

    from app.providers.factory import ProviderFactory

    print("=" * 80)
    print("Testing Data Providers")
    print("=" * 80)

    # Test configuration
    ticker = "AAPL"
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 31)
    intervals_to_test = ["1d"]  # Start with daily, can add intraday later
    asset_class = "STOCK"  # Test with stocks

    providers_to_test = [
        "yfinance",
    ]

    for provider_name in providers_to_test:
        for interval in intervals_to_test:
            print(f"\n{'=' * 80}")
            print(f"Testing Provider: {provider_name} | Interval: {interval} | Asset: {asset_class}")
            print("=" * 80)

            try:
                # Create provider
                print(f"\n1. Creating provider '{provider_name}'...")
                provider = ProviderFactory.create_provider(provider_name)
                print(f"✅ Provider created: {provider.get_provider_name()}")

                # Fetch data
                print(f"\n2. Fetching {ticker} data ({start_date.date()} to {end_date.date()}, {interval}, {asset_class})...")
                df = await provider.fetch_ohlcv(
                    ticker, start_date, end_date, interval=interval, asset_class=asset_class
                )

                if df.empty:
                    print(f"❌ No data returned!")
                    continue

                print(f"✅ Fetched {len(df)} bars")

                # Validate structure
                print(f"\n3. Validating data structure...")
                required_cols = ["open", "high", "low", "close", "volume"]
                missing = [col for col in required_cols if col not in df.columns]

                if missing:
                    print(f"❌ Missing columns: {missing}")
                    continue

                print(f"✅ All required columns present: {required_cols}")

                # Check index
                if not isinstance(df.index, pd.DatetimeIndex):
                    print(f"❌ Index is not DatetimeIndex: {type(df.index)}")
                    continue

                print(f"✅ Index is DatetimeIndex")

                # Show sample data
                print(f"\n4. Sample data (first 3 bars):")
                print(df.head(3).to_string())

                # Basic validation
                print(f"\n5. Data validation...")

                # Check for nulls
                null_count = df.isnull().sum().sum()
                if null_count > 0:
                    print(f"⚠️  Found {null_count} null values")
                else:
                    print(f"✅ No null values")

                # Check high >= low
                invalid_hl = (df["high"] < df["low"]).sum()
                if invalid_hl > 0:
                    print(f"❌ Found {invalid_hl} bars where high < low")
                else:
                    print(f"✅ All bars have high >= low")

                # Check close within [low, high]
                invalid_close = ((df["close"] < df["low"]) | (df["close"] > df["high"])).sum()
                if invalid_close > 0:
                    print(f"❌ Found {invalid_close} bars where close not in [low, high]")
                else:
                    print(f"✅ All bars have close within [low, high]")

                # Check volume >= 0
                invalid_volume = (df["volume"] < 0).sum()
                if invalid_volume > 0:
                    print(f"❌ Found {invalid_volume} bars with negative volume")
                else:
                    print(f"✅ All bars have volume >= 0")

                print(f"\n✅ Provider '{provider_name}' (interval={interval}) passed all tests!")

            except Exception as e:
                print(f"\n❌ Provider '{provider_name}' (interval={interval}) failed: {e}")
                import traceback
                traceback.print_exc()
                continue

    print(f"\n{'=' * 80}")
    print("✅ Provider testing complete!")
    print("=" * 80)


if __name__ == "__main__":
    import asyncio
    import pandas as pd

    try:
        asyncio.run(test_providers())
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
