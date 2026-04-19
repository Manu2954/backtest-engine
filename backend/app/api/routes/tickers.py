from __future__ import annotations

from fastapi import APIRouter, Query

from app.engine.data_layer import validate_ticker

router = APIRouter(prefix="/tickers", tags=["tickers"])


@router.get("/validate", summary="Validate ticker")
async def validate(
    ticker: str = Query(..., description="Ticker symbol (e.g., AAPL, BTCUSDT)"),
    asset_class: str = Query("STOCK", description="STOCK or CRYPTO"),
) -> dict[str, bool]:
    """
    Check if a ticker is valid and has available data.

    - **STOCK**: Uses Yahoo Finance (e.g., AAPL, MSFT, ^SPX)
    - **CRYPTO**: Uses Binance (e.g., BTCUSDT, ETHUSDT)
    """
    return {"valid": validate_ticker(ticker, asset_class=asset_class)}
