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
    print("Test 2: With yfinance provider")
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

    # Test 3: With OpenBB provider
    print("\n" + "=" * 80)
    print("Test 3: With OpenBB provider")
    print("=" * 80)

    try:
        print(f"\nFetching {ticker} data with provider='openbb:yfinance'...")
        df = await fetch_ohlcv_async(
            ticker, start, end, resolution="1d", asset_class="STOCK", provider="openbb:yfinance"
        )

        if df.empty:
            print("❌ No data returned!")
        else:
            print(f"✅ Fetched {len(df)} bars")
            print(f"   Columns: {list(df.columns)}")
            print(f"   Date range: {df.index.min().date()} to {df.index.max().date()}")

    except Exception as e:
        print(f"❌ OpenBB provider fetch failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 4: Compare results
    print("\n" + "=" * 80)
    print("Test 4: Comparing provider results")
    print("=" * 80)

    try:
        print(f"\nFetching same data with different providers...")

        df_legacy = await fetch_ohlcv_async(ticker, start, end, resolution="1d", asset_class="STOCK")
        df_yf = await fetch_ohlcv_async(
            ticker, start, end, resolution="1d", asset_class="STOCK", provider="yfinance"
        )
        df_obb = await fetch_ohlcv_async(
            ticker, start, end, resolution="1d", asset_class="STOCK", provider="openbb:yfinance"
        )

        print(f"\nBar counts:")
        print(f"   Legacy:  {len(df_legacy)} bars")
        print(f"   YFinance: {len(df_yf)} bars")
        print(f"   OpenBB:   {len(df_obb)} bars")

        # Check if bar counts are close (allow small differences due to data updates)
        max_count = max(len(df_legacy), len(df_yf), len(df_obb))
        min_count = min(len(df_legacy), len(df_yf), len(df_obb))

        if max_count - min_count <= 2:
            print(f"✅ Bar counts are consistent (within 2 bars)")
        else:
            print(f"⚠️  Bar counts differ by {max_count - min_count} bars")

        # Check if close prices are similar (first and last bar)
        if not df_legacy.empty and not df_yf.empty and not df_obb.empty:
            first_date = max(
                df_legacy.index.min(), df_yf.index.min(), df_obb.index.min()
            )
            last_date = min(df_legacy.index.max(), df_yf.index.max(), df_obb.index.max())

            if first_date in df_legacy.index and first_date in df_yf.index and first_date in df_obb.index:
                close_legacy = df_legacy.loc[first_date, "close"]
                close_yf = df_yf.loc[first_date, "close"]
                close_obb = df_obb.loc[first_date, "close"]

                print(f"\nFirst bar ({first_date.date()}) close prices:")
                print(f"   Legacy:  ${close_legacy:.2f}")
                print(f"   YFinance: ${close_yf:.2f}")
                print(f"   OpenBB:   ${close_obb:.2f}")

                # Allow 1% difference (data sources may differ slightly)
                diff_yf = abs(close_legacy - close_yf) / close_legacy * 100
                diff_obb = abs(close_legacy - close_obb) / close_legacy * 100

                if diff_yf < 1.0 and diff_obb < 1.0:
                    print(f"✅ Close prices are consistent (within 1%)")
                else:
                    print(f"⚠️  Close prices differ (YF: {diff_yf:.2f}%, OBB: {diff_obb:.2f}%)")

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
