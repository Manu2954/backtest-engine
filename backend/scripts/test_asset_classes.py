"""
Test providers with both STOCK and CRYPTO asset classes.

Verifies that providers correctly handle different asset types.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def test_asset_classes():
    """Test providers with different asset classes."""

    from app.providers.factory import ProviderFactory

    print("=" * 80)
    print("Testing Providers with Different Asset Classes")
    print("=" * 80)

    # Test configurations
    test_cases = [
        {
            "ticker": "AAPL",
            "asset_class": "STOCK",
            "start": datetime(2024, 1, 1),
            "end": datetime(2024, 1, 31),
        },
        {
            "ticker": "BTC-USD",
            "asset_class": "CRYPTO",
            "start": datetime(2024, 1, 1),
            "end": datetime(2024, 1, 31),
        },
    ]

    providers_to_test = [
        "yfinance",
    ]

    for provider_name in providers_to_test:
        print(f"\n{'=' * 80}")
        print(f"Testing Provider: {provider_name}")
        print("=" * 80)

        provider = ProviderFactory.create_provider(provider_name)

        for test_case in test_cases:
            ticker = test_case["ticker"]
            asset_class = test_case["asset_class"]
            start = test_case["start"]
            end = test_case["end"]

            print(f"\n  Testing {asset_class}: {ticker}")

            try:
                df = await provider.fetch_ohlcv(
                    ticker,
                    start,
                    end,
                    interval="1d",
                    asset_class=asset_class,
                )

                if df.empty:
                    print(f"  ❌ No data returned for {ticker} ({asset_class})")
                    continue

                print(f"  ✅ Fetched {len(df)} bars for {ticker} ({asset_class})")
                print(f"     Date range: {df.index.min().date()} to {df.index.max().date()}")
                print(f"     Sample close: ${df['close'].iloc[0]:.2f}")

            except Exception as e:
                print(f"  ❌ Failed to fetch {ticker} ({asset_class}): {e}")

    print(f"\n{'=' * 80}")
    print("✅ Asset class testing complete!")
    print("=" * 80)


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(test_asset_classes())
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
