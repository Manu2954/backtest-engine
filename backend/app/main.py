from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.backtests import router as backtests_router
from app.api.routes.robustness import router as robustness_router
from app.api.routes.strategies import router as strategies_router
from app.api.routes.tickers import router as tickers_router

API_DESCRIPTION = """
## Overview

Backtest Engine is a full-featured backtesting platform for evaluating technical
indicator-based trading strategies. It supports stocks and cryptocurrencies with
realistic trade simulation including transaction costs, position sizing, and risk management.

## Key Features

- **Strategy Builder**: Define strategies using technical indicators (SMA, EMA, RSI, MACD, etc.)
- **Condition Engine**: Flexible entry/exit rules with AND/OR logic and crossover detection
- **Realistic Simulation**: Next-bar fills, commission, slippage, stop-loss, take-profit
- **Position Sizing**: Full capital, percent capital, fixed amount, or risk-based sizing
- **Performance Metrics**: Sharpe ratio, CAGR, max drawdown, win rate, profit factor
- **Benchmark Comparison**: Alpha and beta vs buy-and-hold
- **Trade Attribution**: Signal strength analysis and per-trade alpha calculation
- **Robustness Analysis**: Parameter sensitivity testing to evaluate strategy stability

## Workflow

1. **Create a Strategy** - Define indicators and entry/exit conditions
2. **Run a Backtest** - Execute against historical data
3. **Analyze Results** - Review performance metrics and trade log
4. **Test Robustness** - Verify stability across parameter variations

## Data Sources

- **Stocks**: Yahoo Finance (daily, intraday)
- **Crypto**: Binance (1m to 1d intervals)
"""

tags_metadata = [
    {
        "name": "strategies",
        "description": "Create and manage trading strategies with indicators and conditions.",
    },
    {
        "name": "backtests",
        "description": "Execute backtests and retrieve results including performance metrics and trade logs.",
    },
    {
        "name": "robustness",
        "description": "Parameter sensitivity analysis to evaluate strategy robustness.",
    },
    {
        "name": "tickers",
        "description": "Search for available tickers across supported data providers.",
    },
]

app = FastAPI(
    title="Backtest Engine",
    description=API_DESCRIPTION,
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "Backtest Engine",
        "url": "https://github.com/Manu2954/backtest-engine",
    },
    license_info={
        "name": "MIT",
    },
)

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
app.include_router(robustness_router)
app.include_router(tickers_router)


@app.get("/health")
def health_check():
    """Health check endpoint for smoke tests and monitoring."""
    return {"status": "healthy"}
