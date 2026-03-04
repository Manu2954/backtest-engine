from __future__ import annotations

from fastapi import APIRouter, Query

from app.engine.data_layer import validate_ticker

router = APIRouter(prefix="/tickers", tags=["tickers"])


@router.get("/validate")
async def validate(ticker: str = Query(...), asset_class: str = Query("STOCK")) -> dict[str, bool]:
    return {"valid": validate_ticker(ticker, asset_class=asset_class)}
