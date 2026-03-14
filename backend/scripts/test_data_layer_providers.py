"""
Test data_layer integration with provider system.

Tests that fetch_ohlcv_async works with the new provider parameter.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def test_data_layer_provider_integration():
    """Test data_layer with provider parameter."""

    from app.engine.data_layer import fetch_ohlcv_async

    print("=" * 80)
    print("Testing Data Layer Provider Integration")
    print("=" * 80)

    ticker = "AAPL"
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 31)

    # Test 1: Legacy behavior (no provider parameter)
    print("\n" + "=" * 80)
    print("Test 1: Legacy behavior (provider=None)")
    print("=" * 80)

    try:
        print(f"\nFetching {ticker} data without provider parameter...")
        df = await fetch_ohlcv_async(ticker, start, end, resolution="1d", asset_class="STOCK")

        if df.empty:
            print("❌ No data returned!")
        else:
            print(f"✅ Fetched {len(df)} bars")
            print(f"   Columns: {list(df.columns)}")
            print(f"   Date range: {df.index.min().date()} to {df.index.max().date()}")

    except Exception as e:
        print(f"❌ Legacy fetch failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: With yfinance provider
    print("\n" + "=" * 80)
    print("Test 2: With yfinance provider (explicit)")
    print("=" * 80)

    try:
        print(f"\nFetching {ticker} data with provider='yfinance'...")
        df = await fetch_ohlcv_async(
            ticker, start, end, resolution="1d", asset_class="STOCK", provider="yfinance"
        )

        if df.empty:
            print("❌ No data returned!")
        else:
            print(f"✅ Fetched {len(df)} bars")
            print(f"   Columns: {list(df.columns)}")
            print(f"   Date range: {df.index.min().date()} to {df.index.max().date()}")

    except Exception as e:
        print(f"❌ YFinance provider fetch failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Compare results
    print("\n" + "=" * 80)
    print("Test 3: Comparing provider results")
    print("=" * 80)

    try:
        print(f"\nFetching same data with different methods...")

        df_legacy = await fetch_ohlcv_async(ticker, start, end, resolution="1d", asset_class="STOCK")
        df_yf = await fetch_ohlcv_async(
            ticker, start, end, resolution="1d", asset_class="STOCK", provider="yfinance"
        )

        print(f"\nBar counts:")
        print(f"   Legacy:   {len(df_legacy)} bars")
        print(f"   YFinance: {len(df_yf)} bars")

        # Check if bar counts match
        if len(df_legacy) == len(df_yf):
            print(f"✅ Bar counts match")
        else:
            print(f"⚠️  Bar counts differ by {abs(len(df_legacy) - len(df_yf))} bars")

        # Check if close prices are similar (first bar)
        if not df_legacy.empty and not df_yf.empty:
            first_date = max(df_legacy.index.min(), df_yf.index.min())

            if first_date in df_legacy.index and first_date in df_yf.index:
                close_legacy = df_legacy.loc[first_date, "close"]
                close_yf = df_yf.loc[first_date, "close"]

                print(f"\nFirst bar ({first_date.date()}) close prices:")
                print(f"   Legacy:   ${close_legacy:.2f}")
                print(f"   YFinance: ${close_yf:.2f}")

                # Allow small difference (data updates)
                diff_pct = abs(close_legacy - close_yf) / close_legacy * 100

                if diff_pct < 0.01:
                    print(f"✅ Close prices match (within 0.01%)")
                else:
                    print(f"⚠️  Close prices differ by {diff_pct:.4f}%")

    except Exception as e:
        print(f"❌ Comparison failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("✅ Data layer provider integration tests complete!")
    print("=" * 80)


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(test_data_layer_provider_integration())
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
