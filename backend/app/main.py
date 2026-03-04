from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.backtests import router as backtests_router
from app.api.routes.strategies import router as strategies_router
from app.api.routes.tickers import router as tickers_router

app = FastAPI(title="Backtest Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(strategies_router)
app.include_router(backtests_router)
app.include_router(tickers_router)
