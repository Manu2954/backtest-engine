from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv  # noqa: E402
from app.engine.indicator_layer import compute_indicators  # noqa: E402


def main() -> None:
    ticker = "BTCUSDT"
    start = "2025-01-01"
    end = "2026-02-21"
    resolution = "5m"
    print(f"Fetching {ticker} from {start} to {end}...")
    t0 = perf_counter()
    df = fetch_ohlcv(ticker, start, end, resolution, "CRYPTO")
    t1 = perf_counter()

    print(f"First fetch took {(t1 - t0) * 1000:.2f} ms, {df.size}")
    indicators = [
        {"indicator_type": "RSI", "alias": "rsi_14", "params": {"period": 14, "source": "close"}},
        {"indicator_type": "EMA", "alias": "ema_20", "params": {"period": 20, "source": "close"}},
        {"indicator_type": "EMA", "alias": "ema_50", "params": {"period": 50, "source": "close"}},
    ]
    df_with_indicators = compute_indicators(df, indicators)

    print("Columns:", list(df_with_indicators.columns))
    print("Index type:", type(df_with_indicators.index).__name__)
    print("Head:")
    print(df_with_indicators.head(3))
    print("Tail:")
    print(df_with_indicators.tail(3))

    new_cols = ["rsi_14", "ema_20", "ema_50"]
    has_nans_after_50 = df_with_indicators.loc[df_with_indicators.index[50]:, new_cols].isna().any().any()
    print("NaN after row ~50:", has_nans_after_50)

    t0 = perf_counter()
    df_cached = fetch_ohlcv(ticker, start, end, resolution, "CRYPTO")
    t1 = perf_counter()
    print(f"Second fetch took {(t1 - t0) * 1000:.2f} ms")
    print("Cache hit rows:", len(df_cached))


if __name__ == "__main__":
    main()
