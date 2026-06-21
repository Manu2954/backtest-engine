"""
Smoke test: Display BTCUSDT price movements from 2:30 AM to 4:30 AM (Asia/Kolkata)

Shows all candles in the time window with price action details.
"""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv


def main():
    ticker = "BTCUSDT"
    start_date = "2025-01-01"
    end_date = "2025-12-31"
    resolution = "1h"
    asset_class = "CRYPTO"

    print(f"Fetching {ticker} data ({resolution}) from {start_date} to {end_date}...")
    df = fetch_ohlcv(ticker, start_date, end_date, resolution, asset_class)

    if df.empty:
        print("No data returned")
        return

    print(f"Total candles fetched: {len(df)}")

    # Data already in IST timezone, just filter by time
    df_ist = df.copy()

    # Filter to 2:30 AM - 4:30 AM window
    night_window = df_ist.between_time("02:30", "04:30")

    print(f"\nCandles in 2:30 AM - 4:30 AM window: {len(night_window)}")

    if night_window.empty:
        print("No candles found in this time window")
        return

    # Calculate price movement metrics
    night_window = night_window.copy()
    night_window["range"] = night_window["high"] - night_window["low"]
    night_window["range_pct"] = (night_window["range"] / night_window["open"]) * 100
    night_window["body"] = abs(night_window["close"] - night_window["open"])
    night_window["body_pct"] = (night_window["body"] / night_window["open"]) * 100
    night_window["direction"] = night_window.apply(
        lambda r: "UP" if r["close"] > r["open"] else "DOWN" if r["close"] < r["open"] else "DOJI",
        axis=1
    )

    # Display statistics
    print("\n" + "="*80)
    print("NIGHT WINDOW STATISTICS (2:30 AM - 4:30 AM)")
    print("="*80)
    print(f"Average Range: ${night_window['range'].mean():.2f} ({night_window['range_pct'].mean():.3f}%)")
    print(f"Max Range: ${night_window['range'].max():.2f} ({night_window['range_pct'].max():.3f}%)")
    print(f"Min Range: ${night_window['range'].min():.2f} ({night_window['range_pct'].min():.3f}%)")
    print(f"Average Body: ${night_window['body'].mean():.2f} ({night_window['body_pct'].mean():.3f}%)")

    up_candles = (night_window["direction"] == "UP").sum()
    down_candles = (night_window["direction"] == "DOWN").sum()
    doji_candles = (night_window["direction"] == "DOJI").sum()

    print(f"\nDirection Distribution:")
    print(f"  UP: {up_candles} ({up_candles/len(night_window)*100:.1f}%)")
    print(f"  DOWN: {down_candles} ({down_candles/len(night_window)*100:.1f}%)")
    print(f"  DOJI: {doji_candles} ({doji_candles/len(night_window)*100:.1f}%)")

    # Show sample candles (first 20)
    print("\n" + "="*80)
    print("SAMPLE CANDLES (First 20)")
    print("="*80)

    display_cols = ["open", "high", "low", "close", "volume", "range", "range_pct", "direction"]
    sample = night_window[display_cols].head(20)

    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.float_format', lambda x: f'{x:.2f}')

    print(sample.to_string())

    # Group by date to show daily patterns
    print("\n" + "="*80)
    print("DAILY AGGREGATES")
    print("="*80)

    night_window_with_date = night_window.copy()
    night_window_with_date["date_col"] = night_window_with_date.index.date
    daily = night_window_with_date.groupby("date_col").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "range": "sum",
        "range_pct": "mean",
        "volume": "sum",
        "direction": lambda x: f"{(x=='UP').sum()}↑ {(x=='DOWN').sum()}↓"
    })

    # Calculate period price range %
    daily["period_range_pct"] = ((daily["high"] - daily["low"]) / daily["open"]) * 100
    daily["period_move_pct"] = ((daily["close"] - daily["open"]) / daily["open"]) * 100

    # Select and rename columns
    daily = daily[["range", "range_pct", "period_range_pct", "period_move_pct", "volume", "direction"]]
    daily.columns = ["Total_Range", "Avg_Candle_Range_%", "Period_Range_%", "Period_Move_%", "Total_Volume", "UP↑_DOWN↓"]

    print(daily.head(30).to_string())

    print("\n✅ Analysis complete")


if __name__ == "__main__":
    main()
