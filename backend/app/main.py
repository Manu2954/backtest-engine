from __future__ import annotations

import logging
import time
import traceback
import uuid
from datetime import datetime, timezone

import redis
from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes.backtests import router as backtests_router
from app.api.routes.robustness import router as robustness_router
from app.api.routes.strategies import router as strategies_router
from app.api.routes.tickers import router as tickers_router
from app.api.routes.charts import router as charts_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Initialize rate limiter with remote address as key
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])

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
    title="Backtest Engine API v1",
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

# Add rate limiter state and middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID for tracing."""

    async def dispatch(self, request: Request, call_next):
        # Check for incoming X-Request-ID header, or generate a new one
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store request_id in request.state for access in route handlers
        request.state.request_id = request_id

        # Process the request
        response = await call_next(request)

        # Add request_id to response headers
        response.headers["X-Request-ID"] = request_id

        return response


# Add RequestID middleware
app.add_middleware(RequestIDMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions with generic error response."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(
        "Unhandled exception [request_id=%s]: %s\n%s",
        request_id,
        str(exc),
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors with detailed field-level messages."""
    errors = []
    for error in exc.errors():
        loc = " -> ".join(str(x) for x in error["loc"])
        errors.append({"field": loc, "message": error["msg"], "type": error["type"]})
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors},
    )


# Parse CORS origins from settings (comma-separated)
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create versioned API router
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(strategies_router)
api_v1_router.include_router(backtests_router)
api_v1_router.include_router(robustness_router)
api_v1_router.include_router(tickers_router)
api_v1_router.include_router(charts_router)

# Mount the versioned router
app.include_router(api_v1_router)


async def _check_database() -> dict:
    """Check database connectivity."""
    start_time = time.time()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {"status": "ok", "latency_ms": latency_ms}
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {"status": "error", "latency_ms": latency_ms, "error": str(e)}


def _check_redis() -> dict:
    """Check Redis connectivity."""
    start_time = time.time()
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {"status": "ok", "latency_ms": latency_ms}
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {"status": "error", "latency_ms": latency_ms, "error": str(e)}


@app.get("/health")
@limiter.exempt
async def health_check():
    """
    Health check endpoint for monitoring.

    Returns detailed status of all dependencies with latency metrics.
    - HTTP 200: All dependencies healthy
    - HTTP 503: One or more dependencies unhealthy
    """
    db_check = await _check_database()
    redis_check = _check_redis()

    checks = {
        "database": db_check,
        "redis": redis_check,
    }

    # Determine overall status
    all_ok = all(check["status"] == "ok" for check in checks.values())
    any_ok = any(check["status"] == "ok" for check in checks.values())

    if all_ok:
        status = "healthy"
    elif any_ok:
        status = "degraded"
    else:
        status = "unhealthy"

    response_data = {
        "status": status,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    status_code = 200 if status == "healthy" else 503
    return JSONResponse(content=response_data, status_code=status_code)
