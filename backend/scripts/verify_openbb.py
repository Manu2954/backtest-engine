"""
Verify OpenBB installation and basic functionality.

Tests that OpenBB can be imported and initialized.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def verify_openbb():
    """Verify OpenBB installation."""

    print("=" * 80)
    print("Verifying OpenBB Installation")
    print("=" * 80)

    # Test 1: Import OpenBB
    print("\n1. Testing OpenBB import...")
    try:
        from openbb import obb
        print("✅ OpenBB imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import OpenBB: {e}")
        return False

    # Test 2: Check version
    print("\n2. Checking OpenBB version...")
    try:
        import openbb
        version = getattr(openbb, "__version__", "unknown")
        print(f"✅ OpenBB version: {version}")
    except Exception as e:
        print(f"⚠️  Could not determine version: {e}")

    # Test 3: List available providers
    print("\n3. Checking available providers...")
    try:
        # Get available providers
        providers = obb.account.providers
        print(f"✅ Available providers: {list(providers.keys()) if hasattr(providers, 'keys') else 'N/A'}")
    except Exception as e:
        print(f"⚠️  Could not list providers: {e}")

    # Test 4: Test basic equity.price.historical call (without API key)
    print("\n4. Testing basic data fetch (AAPL, 5 days)...")
    try:
        # Try to fetch historical data for AAPL (last 5 days)
        data = obb.equity.price.historical(
            symbol="AAPL",
            start_date="2024-01-01",
            end_date="2024-01-05",
            provider="yfinance"  # Use yfinance as it doesn't require API key
        )

        if data and hasattr(data, 'results'):
            print(f"✅ Successfully fetched {len(data.results)} bars")
            if len(data.results) > 0:
                first_bar = data.results[0]
                print(f"   First bar: {first_bar.date} - Close: ${first_bar.close:.2f}")
        else:
            print("⚠️  Data fetch returned empty results")
    except Exception as e:
        print(f"⚠️  Basic data fetch test failed: {e}")
        print("   (This may be normal if providers need configuration)")

    print("\n" + "=" * 80)
    print("✅ OpenBB verification complete!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    try:
        success = verify_openbb()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Verification failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
