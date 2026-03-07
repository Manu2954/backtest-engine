from __future__ import annotations

import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(16), nullable=False)
    start_date: Mapped[str] = mapped_column(Date, nullable=False)
    end_date: Mapped[str] = mapped_column(Date, nullable=False)
    bar_resolution: Mapped[str] = mapped_column(String(8), nullable=False)
    initial_capital: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    periodic_contribution: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    position_size_type: Mapped[str | None] = mapped_column(String(32), nullable=True, default="full_capital")
    position_size_value: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True, default=100.0)
    stop_loss_pct: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    take_profit_pct: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    commission_per_trade: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True, default=0.0)
    commission_pct: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True, default=0.0)
    slippage_pct: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True, default=0.0)

    strategy = relationship("Strategy", back_populates="backtest_runs")
    trades = relationship("TradeLog", back_populates="run", cascade="all, delete-orphan")


class TradeLog(Base):
    __tablename__ = "trade_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    entry_date: Mapped[str] = mapped_column(Date, nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    exit_date: Mapped[str] = mapped_column(Date, nullable=False)
    exit_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    shares: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    pnl: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    pnl_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    trade_duration_days: Mapped[int] = mapped_column(nullable=False)
    exit_reason: Mapped[str | None] = mapped_column(String(32), nullable=True, default="signal")

    run = relationship("BacktestRun", back_populates="trades")
