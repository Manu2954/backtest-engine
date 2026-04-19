"""
API schemas for robustness analysis endpoints.
"""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ParameterSensitivityCreate(BaseModel):
    """Request payload for parameter sensitivity analysis."""

    strategy_id: UUID = Field(..., description="ID of the strategy to analyze")
    ticker: str = Field(..., description="Ticker symbol (e.g., AAPL, BTCUSDT)")
    asset_class: Literal["STOCK", "CRYPTO"] = Field("STOCK", description="STOCK or CRYPTO")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    bar_resolution: str = Field("1d", description="Bar interval: 1m, 5m, 15m, 1h, 1d")
    initial_capital: float = Field(10000.0, description="Starting capital in dollars")
    variation_pct: float = Field(0.2, ge=0.05, le=0.5, description="Parameter variation (0.2 = ±20%)")

    # Optional backtest parameters
    position_size_type: str = Field("full_capital", description="Position sizing method")
    position_size_value: float = Field(100.0, description="Position size value")
    stop_loss_pct: float | None = Field(None, description="Stop loss percentage")
    take_profit_pct: float | None = Field(None, description="Take profit percentage")
    commission_per_trade: float = Field(0.0, description="Fixed commission per trade")
    commission_pct: float = Field(0.0, description="Commission as percentage")
    slippage_pct: float = Field(0.0, description="Slippage as percentage")
    enable_attribution: bool = Field(False, description="Enable attribution (slower)")


class RobustnessAnalysisOut(BaseModel):
    """Response payload for robustness analysis."""

    model_config = {"from_attributes": True}

    id: UUID = Field(..., description="Unique analysis ID")
    strategy_id: UUID = Field(..., description="Strategy ID")
    analysis_type: str = Field(..., description="Type of analysis (parameter_sensitivity)")
    status: str = Field(..., description="PENDING, RUNNING, COMPLETE, or FAILED")
    params: dict[str, Any] = Field(..., description="Analysis parameters")
    report: dict[str, Any] | None = Field(None, description="Results when COMPLETE")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    error_message: str | None = Field(None, description="Error message if FAILED")


class ParameterSensitivityReport(BaseModel):
    """Detailed parameter sensitivity analysis report structure."""

    baseline: dict[str, Any] = Field(..., description="Original strategy metrics")
    variants: list[dict[str, Any]] = Field(..., description="Variant results with deltas")
    stability_metrics: dict[str, float] = Field(..., description="Stability score and CVs")
    assessment: dict[str, Any] = Field(..., description="Robustness level, flags, recommendation")


class WalkForwardCreate(BaseModel):
    """Request payload for walk-forward validation."""

    strategy_id: UUID = Field(..., description="ID of the strategy to analyze")
    ticker: str = Field(..., description="Ticker symbol (e.g., AAPL, BTCUSDT)")
    asset_class: Literal["STOCK", "CRYPTO"] = Field("STOCK", description="STOCK or CRYPTO")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    bar_resolution: str = Field("1d", description="Bar interval: 1m, 5m, 15m, 1h, 1d")
    initial_capital: float = Field(10000.0, description="Starting capital in dollars")
    window_count: int = Field(5, ge=2, le=20, description="Number of windows to divide data into")

    # Optional backtest parameters
    position_size_type: str = Field("full_capital", description="Position sizing method")
    position_size_value: float = Field(100.0, description="Position size value")
    stop_loss_pct: float | None = Field(None, description="Stop loss percentage")
    take_profit_pct: float | None = Field(None, description="Take profit percentage")
    commission_per_trade: float = Field(0.0, description="Fixed commission per trade")
    commission_pct: float = Field(0.0, description="Commission as percentage")
    slippage_pct: float = Field(0.0, description="Slippage as percentage")
