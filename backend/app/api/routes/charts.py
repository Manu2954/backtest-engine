from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.engine.data_layer import fetch_ohlcv_async

router = APIRouter(prefix="/charts", tags=["charts"])


@router.get("/ohlcv", summary="Fetch OHLCV chart data")
async def get_ohlcv_chart(
    ticker: str = Query(..., description="Ticker symbol (e.g., AAPL, BTCUSDT)"),
    asset_class: str = Query("STOCK", description="STOCK or CRYPTO"),
    resolution: str = Query("1d", description="Bar resolution (e.g., 1d, 1h, 15m)"),
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Fetch historical OHLCV data for charting.

    Uses the same cached data layer as backtests (Redis -> PostgreSQL -> provider).
    Defaults to the last 365 days if no date range is provided.

    Returns candle data shaped for lightweight-charts:
    - **candles**: list of {time, open, high, low, close}
    - **volume**: list of {time, value}
    """
    # Default to last year if no range supplied
    if not end_date:
        end_date = date.today().isoformat()
    if not start_date:
        start_dt = date.fromisoformat(end_date) - timedelta(days=365)
        start_date = start_dt.isoformat()

    try:
        df = await fetch_ohlcv_async(
            ticker=ticker,
            start=start_date,
            end=end_date,
            resolution=resolution,
            asset_class=asset_class,
            session=session,
        )
    except Exception as exc:  # noqa: BLE001 - surface provider errors to client
        raise HTTPException(
            status_code=422,
            detail=f"Failed to fetch data for {ticker}: {exc}",
        ) from exc

    if df is None or df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for {ticker} in the requested range.",
        )

    candles = []
    volume = []
    for ts, row in df.iterrows():
        time_str = ts.date().isoformat() if resolution.endswith("d") or resolution.endswith("wk") or resolution.endswith("mo") else ts.isoformat()
        candles.append(
            {
                "time": time_str,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
        )
        if "volume" in row:
            volume.append({"time": time_str, "value": float(row["volume"])})

    return {
        "ticker": ticker,
        "asset_class": asset_class,
        "resolution": resolution,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(candles),
        "candles": candles,
        "volume": volume,
    }
