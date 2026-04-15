"""
API schemas for robustness analysis endpoints.
"""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ParameterSensitivityCreate(BaseModel):
    """Request schema for parameter sensitivity analysis."""

    strategy_id: UUID
    ticker: str
    asset_class: Literal["STOCK", "CRYPTO"] = "STOCK"
    start_date: str = Field(..., description="YYYY-MM-DD format")
    end_date: str = Field(..., description="YYYY-MM-DD format")
    bar_resolution: str = "1d"
    initial_capital: float = 10000.0
    variation_pct: float = Field(0.2, ge=0.05, le=0.5, description="Parameter variation (0.2 = ±20%)")

    # Optional backtest parameters
    position_size_type: str = "full_capital"
    position_size_value: float = 100.0
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    commission_per_trade: float = 0.0
    commission_pct: float = 0.0
    slippage_pct: float = 0.0
    enable_attribution: bool = False  # Disable for faster variant backtests


class RobustnessAnalysisOut(BaseModel):
    """Response schema for robustness analysis."""

    model_config = {"from_attributes": True}

    id: UUID
    strategy_id: UUID
    analysis_type: str
    status: str  # PENDING, RUNNING, COMPLETE, FAILED
    params: dict[str, Any]
    report: dict[str, Any] | None = None
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None


class ParameterSensitivityReport(BaseModel):
    """Detailed parameter sensitivity analysis report."""

    baseline: dict[str, Any]
    variants: list[dict[str, Any]]
    stability_metrics: dict[str, float]
    assessment: dict[str, Any]
