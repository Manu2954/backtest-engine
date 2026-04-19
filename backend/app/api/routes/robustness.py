"""
API routes for robustness analysis.
"""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.schemas.robustness import (
    ParameterSensitivityCreate,
    RobustnessAnalysisOut,
    WalkForwardCreate,
)
from app.core.database import get_session
from app.models.robustness import RobustnessAnalysis
from app.tasks.robustness_task import run_parameter_sensitivity_analysis, run_walk_forward_validation

router = APIRouter(prefix="/robustness", tags=["robustness"])


@router.post("/parameter-sensitivity", response_model=RobustnessAnalysisOut, summary="Run parameter sensitivity analysis")
async def create_parameter_sensitivity_analysis(
    request: ParameterSensitivityCreate,
):
    """
    Run parameter sensitivity analysis on a strategy.

    Tests strategy performance as indicator parameters vary by ±variation_pct (default ±20%).

    **Process**:
    1. Generate parameter variants (e.g., SMA period 50 → 40 and 60)
    2. Run backtest for each variant
    3. Calculate stability score using coefficient of variation
    4. Classify strategy as ROBUST, MODERATE, or FRAGILE

    **Report fields** (when COMPLETE):
    - baseline: Original strategy metrics
    - variants: List of variant results with delta from baseline
    - stability_metrics: overall_stability_score, per_metric_cv
    - assessment: robustness_level, risk_flags, recommendation
    """
    # Build backtest params dict
    backtest_params = {
        "ticker": request.ticker,
        "asset_class": request.asset_class,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "bar_resolution": request.bar_resolution,
        "initial_capital": request.initial_capital,
        "position_size_type": request.position_size_type,
        "position_size_value": request.position_size_value,
        "stop_loss_pct": request.stop_loss_pct,
        "take_profit_pct": request.take_profit_pct,
        "commission_per_trade": request.commission_per_trade,
        "commission_pct": request.commission_pct,
        "slippage_pct": request.slippage_pct,
        "enable_attribution": request.enable_attribution,
    }

    # Submit Celery task (runs in background)
    run_parameter_sensitivity_analysis.apply_async(
        args=[str(request.strategy_id), backtest_params, request.variation_pct]
    )

    # Poll database briefly for analysis record (created at start of task)
    import asyncio
    for _ in range(30):  # Try for up to 6 seconds
        async for session in get_session():
            stmt = select(RobustnessAnalysis).where(
                RobustnessAnalysis.strategy_id == request.strategy_id
            ).order_by(RobustnessAnalysis.created_at.desc()).limit(1)
            result = await session.execute(stmt)
            analysis = result.scalar_one_or_none()

            if analysis:
                return analysis

        await asyncio.sleep(0.2)

    # If still not found after 6 seconds, raise error
    raise HTTPException(
        status_code=500,
        detail="Analysis record not created in time"
    )


@router.get("/{analysis_id}", response_model=RobustnessAnalysisOut, summary="Get robustness analysis")
async def get_robustness_analysis(analysis_id: UUID):
    """
    Get robustness analysis status and results.

    **Status values**:
    - PENDING: Analysis queued but not started
    - RUNNING: Backtests in progress
    - COMPLETE: Analysis finished, check report field
    - FAILED: Error occurred, check error_message field

    **Robustness levels**:
    - ROBUST (score ≥ 0.8): Strategy stable across parameter changes
    - MODERATE (0.6-0.8): Some sensitivity to parameters
    - FRAGILE (< 0.6): Highly sensitive, may be overfitted
    """
    async for session in get_session():
        stmt = select(RobustnessAnalysis).where(RobustnessAnalysis.id == analysis_id)
        result = await session.execute(stmt)
        analysis = result.scalar_one_or_none()

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        return analysis


@router.delete("/{analysis_id}", summary="Delete robustness analysis")
async def delete_robustness_analysis(analysis_id: UUID):
    """Delete a robustness analysis and all associated data."""
    async for session in get_session():
        stmt = select(RobustnessAnalysis).where(RobustnessAnalysis.id == analysis_id)
        result = await session.execute(stmt)
        analysis = result.scalar_one_or_none()

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        await session.delete(analysis)
        await session.commit()

    return {"message": "Analysis deleted successfully"}


@router.post("/walk-forward", response_model=RobustnessAnalysisOut, summary="Run walk-forward validation")
async def create_walk_forward_validation(
    request: WalkForwardCreate,
):
    """
    Run walk-forward validation on a strategy.

    Tests strategy performance across rolling time windows to detect period-dependency.
    Uses fixed parameters - validates if strategy works consistently across different periods.

    **Process**:
    1. Fetch full date range and compute indicators once
    2. Divide into N equal windows by bar count
    3. Run backtest for each window
    4. Calculate consistency score and assess results

    **Confidence levels** (based on trades per window):
    - HIGH: 20+ trades (reliable metrics)
    - MEDIUM: 10-19 trades (interpret with caution)
    - LOW: <10 trades (excluded from consistency score)

    **Report fields** (when COMPLETE):
    - windows: Per-window metrics and confidence
    - summary: Consistency score, profitable ratio, best/worst windows
    - assessment: Level (ROBUST/MODERATE/FRAGILE), risk_flags, recommendation
    """
    # Build backtest params dict
    backtest_params = {
        "ticker": request.ticker,
        "asset_class": request.asset_class,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "bar_resolution": request.bar_resolution,
        "initial_capital": request.initial_capital,
        "position_size_type": request.position_size_type,
        "position_size_value": request.position_size_value,
        "stop_loss_pct": request.stop_loss_pct,
        "take_profit_pct": request.take_profit_pct,
        "commission_per_trade": request.commission_per_trade,
        "commission_pct": request.commission_pct,
        "slippage_pct": request.slippage_pct,
    }

    # Submit Celery task
    run_walk_forward_validation.apply_async(
        args=[str(request.strategy_id), backtest_params, request.window_count]
    )

    # Poll database briefly for analysis record
    import asyncio
    for _ in range(30):
        async for session in get_session():
            stmt = select(RobustnessAnalysis).where(
                RobustnessAnalysis.strategy_id == request.strategy_id,
                RobustnessAnalysis.analysis_type == "WALK_FORWARD",
            ).order_by(RobustnessAnalysis.created_at.desc()).limit(1)
            result = await session.execute(stmt)
            analysis = result.scalar_one_or_none()

            if analysis:
                return analysis

        await asyncio.sleep(0.2)

    raise HTTPException(
        status_code=500,
        detail="Analysis record not created in time"
    )
