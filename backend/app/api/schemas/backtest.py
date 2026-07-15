from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BacktestCreate(BaseModel):
    """Request payload for creating a new backtest run."""

    strategy_id: UUID = Field(..., description="ID of the strategy to backtest")
    ticker: str = Field(..., description="Ticker symbol (e.g., AAPL, BTCUSDT)")
    asset_class: str = Field(..., description="STOCK or CRYPTO")
    start_date: date = Field(..., description="Backtest start date")
    end_date: date = Field(..., description="Backtest end date")
    bar_resolution: str = Field("1d", description="Bar interval: 1m, 5m, 15m, 1h, 1d")
    initial_capital: float = Field(..., description="Starting capital in dollars")
    provider: str | None = Field(None, description="Data provider: yfinance or binance (auto-selected if None)")
    market_type: str = Field("SPOT", description="Market type for crypto: SPOT or FUTURES")
    periodic_contribution: dict[str, Any] | None = Field(None, description="Periodic cash contributions config")

    # Position sizing
    position_size_type: str = Field("full_capital", description="full_capital, percent_capital, fixed_amount, or risk_based")
    position_size_value: float = Field(100.0, description="Percentage (0-100) or dollar amount depending on type")

    # Risk management
    stop_loss_pct: float | None = Field(None, description="Stop loss percentage (e.g., 5.0 for 5%)")
    take_profit_pct: float | None = Field(None, description="Take profit percentage (e.g., 10.0 for 10%)")

    # Transaction costs
    commission_per_trade: float = Field(0.0, description="Fixed commission per trade in dollars")
    commission_pct: float = Field(0.0, description="Commission as percentage of trade value")
    slippage_pct: float = Field(0.0, description="Slippage as percentage of price")

    # Attribution
    enable_attribution: bool = Field(True, description="Enable trade attribution analysis")

    # Sharpe ratio
    risk_free_rate: float = Field(0.0, description="Annual risk-free rate for Sharpe ratio (e.g., 0.05 for 5%)")

    # Advanced features
    leverage: float = Field(1.0, description="Leverage multiplier (1.0 = no leverage)")
    dynamic_stop_column: str | None = Field(None, description="Column name for dynamic trailing stop")
    dynamic_tp_pct_column: str | None = Field(None, description="Column name for dynamic take profit percentage")
    enable_counter_trades: bool = Field(False, description="Enable counter-trade on losing exits")
    counter_tp_multiplier: float = Field(1.5, description="Counter-trade TP = abs(loss%) × multiplier")
    exit_rules: list[dict[str, Any]] | None = Field(None, description="Custom exit rules")


class BacktestOut(BaseModel):
    """Response payload for a backtest run."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique backtest ID")
    strategy_id: UUID = Field(..., description="Strategy ID")
    ticker: str = Field(..., description="Ticker symbol")
    asset_class: str = Field(..., description="STOCK or CRYPTO")
    provider: str | None = Field(None, description="Data provider used")
    market_type: str | None = Field(None, description="Market type: SPOT or FUTURES (crypto only)")
    start_date: date = Field(..., description="Backtest start date")
    end_date: date = Field(..., description="Backtest end date")
    bar_resolution: str = Field(..., description="Bar interval")
    initial_capital: float = Field(..., description="Starting capital")
    status: str = Field(..., description="PENDING, RUNNING, COMPLETE, or FAILED")
    celery_task_id: str | None = Field(None, description="Background task ID")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    error_message: str | None = Field(None, description="Error message if FAILED")
    report: dict[str, Any] | None = Field(None, description="Performance report when COMPLETE")
    periodic_contribution: dict[str, Any] | None = None
    position_size_type: str | None = None
    position_size_value: float | None = None
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    commission_per_trade: float | None = None
    commission_pct: float | None = None
    slippage_pct: float | None = None
    enable_attribution: bool
    risk_free_rate: float | None = Field(None, description="Risk-free rate used for Sharpe ratio")

    # Advanced features
    leverage: float | None = None
    dynamic_stop_column: str | None = None
    dynamic_tp_pct_column: str | None = None
    enable_counter_trades: bool = False
    counter_tp_multiplier: float | None = None
    exit_rules: list[dict[str, Any]] | None = None


class TradeLogOut(BaseModel):
    """Individual trade record from a backtest."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique trade ID")
    run_id: UUID = Field(..., description="Parent backtest ID")
    entry_date: datetime = Field(..., description="Position entry timestamp")
    entry_price: float = Field(..., description="Entry fill price")
    exit_date: datetime = Field(..., description="Position exit timestamp")
    exit_price: float = Field(..., description="Exit fill price")
    shares: float = Field(..., description="Number of shares/units")
    pnl: float = Field(..., description="Profit/loss in dollars")
    pnl_pct: float = Field(..., description="Profit/loss as percentage")
    trade_duration_days: int = Field(..., description="Days position was held")
    exit_reason: str | None = Field(None, description="signal, stop_loss, take_profit, or force_close")
    direction: str = Field("LONG", description="LONG or SHORT")

    # Attribution fields
    entry_conditions_met: list[str] | None = Field(None, description="Condition IDs that triggered entry")
    exit_conditions_met: list[str] | None = Field(None, description="Condition IDs that triggered exit")
    entry_signal_strength: float | None = Field(None, description="Signal confluence score (0-1)")
    market_return_during_trade: float | None = Field(None, description="Buy-and-hold return during trade")
    alpha: float | None = Field(None, description="Trade return minus market return")
    indicator_snapshot_entry: dict[str, Any] | None = Field(None, description="Indicator values at entry")
    indicator_snapshot_exit: dict[str, Any] | None = Field(None, description="Indicator values at exit")
