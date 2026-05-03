"""
Test Bai-Perron structural break detection via R service.

Prerequisites:
    1. Install R: brew install r
    2. Install R packages: R -e "install.packages(c('plumber', 'strucchange', 'jsonlite'))"
    3. Start R service: cd r_service && ./start.sh

Then run: python backend/scripts/test_bai_perron.py
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from app.engine.data_layer import fetch_ohlcv
from app.engine.robustness.bai_perron_client import detect_structural_breaks


def main():
    print("=== Bai-Perron Structural Break Detection Test ===\n")

    # Fetch data - use daily for faster testing (Bai-Perron is O(n²))
    df = fetch_ohlcv('BTCUSDT', '2026-03-01', '2026-04-25', '1d', 'CRYPTO')
    print(f"Total bars: {len(df)}")

    # If you want 5m data, uncomment below (will be slow ~15k points):
    # df = fetch_ohlcv('BTCUSDT', '2026-03-01', '2026-04-25', '5m', 'CRYPTO')

    prices = df['close'].tolist()
    dates = [str(d) for d in df.index]

    print(f"Price range: ${min(prices):.0f} - ${max(prices):.0f}")
    print(f"Date range: {dates[0]} to {dates[-1]}")

    # Detect breaks
    print("\nCalling R service...")
    try:
        # min_segment should be < n/2
        min_seg = max(5, len(df) // 10)  # ~10% of data, at least 5
        print(f"Using min_segment={min_seg}")

        result = detect_structural_breaks(
            prices=prices,
            dates=dates,
            min_segment=min_seg,
            max_breaks=20,
        )
    except ConnectionError as e:
        print(f"\n❌ {e}")
        print("\nTo start the R service:")
        print("  cd r_service")
        print("  ./start.sh")
        return

    # Print results
    print(f"\n=== Results ===")

    # Helper to unwrap R list values
    def unwrap(val):
        if isinstance(val, list) and len(val) == 1:
            return val[0]
        return val

    success = unwrap(result.get('success', False))

    if not success:
        error = unwrap(result.get('error', 'Unknown'))
        print(f"Error: {error}")
        return

    n_breaks = unwrap(result.get('n_breaks', 0))
    bic_raw = unwrap(result.get('bic', 0))
    bic = float(bic_raw) if bic_raw != 'NA' else None

    print(f"Number of breaks: {n_breaks}")
    print(f"BIC score: {bic:.2f}" if bic else "BIC score: N/A")

    print(f"\nSegments:")
    for i, seg in enumerate(result['segments']):
        # Unwrap all segment values
        start_date = unwrap(seg.get('start_date', ''))
        end_date = unwrap(seg.get('end_date', ''))
        n_bars = int(unwrap(seg.get('n_bars', 0)))
        pct_change = float(unwrap(seg.get('pct_change', 0)))
        r_squared = float(unwrap(seg.get('r_squared', 0)))
        slope = float(unwrap(seg.get('slope', 0)))

        direction = "↑" if slope > 0 else "↓" if slope < 0 else "→"
        print(f"  Seg {i+1}: {start_date} → {end_date}")
        print(f"          Bars: {n_bars}, Change: {pct_change:+.2f}% {direction}")
        print(f"          R²: {r_squared:.3f}, Slope: {slope:.6f}")

    if result.get('break_dates'):
        print(f"\nBreak dates:")
        for bd in result['break_dates']:
            print(f"  - {unwrap(bd)}")


if __name__ == "__main__":
    main()
