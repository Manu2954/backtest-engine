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
    # Position sizing parameters
    position_size_type: str = "full_capital"  # "full_capital" | "percent_capital" | "fixed_amount"
    position_size_value: float = 100.0  # Percentage or dollar amount
    # Risk management parameters
    stop_loss_pct: float | None = None  # Stop loss percentage (e.g., 5.0 for 5%)
    take_profit_pct: float | None = None  # Take profit percentage (e.g., 10.0 for 10%)
    # Transaction cost parameters
    commission_per_trade: float = 0.0  # Fixed commission per trade (e.g., $5)
    commission_pct: float = 0.0  # Commission as % of trade value (e.g., 0.1 for 0.1%)
    slippage_pct: float = 0.0  # Slippage as % of price (e.g., 0.05 for 0.05%)


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
    # Position sizing and risk management parameters
    position_size_type: str | None
    position_size_value: float | None
    stop_loss_pct: float | None
    take_profit_pct: float | None
    # Transaction cost parameters
    commission_per_trade: float | None
    commission_pct: float | None
    slippage_pct: float | None


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
    exit_reason: str | None  # NEW: Why the trade exited
