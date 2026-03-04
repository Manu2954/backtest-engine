from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BacktestCreate(BaseModel):
    strategy_id: UUID
    ticker: str
    asset_class: str
    start_date: date
    end_date: date
    bar_resolution: str = "1d"
    initial_capital: float
    periodic_contribution: dict[str, Any] | None = None


class BacktestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    strategy_id: UUID
    ticker: str
    asset_class: str
    start_date: date
    end_date: date
    bar_resolution: str
    initial_capital: float
    status: str
    celery_task_id: str | None
    created_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    report: dict[str, Any] | None
    periodic_contribution: dict[str, Any] | None


class TradeLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    entry_date: date
    entry_price: float
    exit_date: date
    exit_price: float
    shares: float
    pnl: float
    pnl_pct: float
    trade_duration_days: int
