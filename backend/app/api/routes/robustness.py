"""
API routes for robustness analysis.
"""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.schemas.robustness import (
    ParameterSensitivityCreate,
    RobustnessAnalysisOut,
)
from app.core.database import get_session
from app.models.robustness import RobustnessAnalysis
from app.tasks.robustness_task import run_parameter_sensitivity_analysis

router = APIRouter(prefix="/robustness", tags=["robustness"])


@router.post("/parameter-sensitivity", response_model=RobustnessAnalysisOut)
async def create_parameter_sensitivity_analysis(
    request: ParameterSensitivityCreate,
):
    """
    Run parameter sensitivity analysis on a strategy.

    Tests strategy performance as indicator parameters vary by ±variation_pct.
    Returns analysis_id immediately while backtests run in background.

    Use GET /robustness/{analysis_id} to check status and retrieve results.
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


@router.get("/{analysis_id}", response_model=RobustnessAnalysisOut)
async def get_robustness_analysis(analysis_id: UUID):
    """
    Get robustness analysis status and results.

    Status values:
    - PENDING: Analysis queued but not started
    - RUNNING: Backtests in progress
    - COMPLETE: Analysis finished, check report field
    - FAILED: Error occurred, check error_message field
    """
    async for session in get_session():
        stmt = select(RobustnessAnalysis).where(RobustnessAnalysis.id == analysis_id)
        result = await session.execute(stmt)
        analysis = result.scalar_one_or_none()

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        return analysis


@router.delete("/{analysis_id}")
async def delete_robustness_analysis(analysis_id: UUID):
    """
    Delete a robustness analysis and all associated variant backtests.

    Cascade delete removes variant backtest links automatically.
    """
    async for session in get_session():
        stmt = select(RobustnessAnalysis).where(RobustnessAnalysis.id == analysis_id)
        result = await session.execute(stmt)
        analysis = result.scalar_one_or_none()

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        await session.delete(analysis)
        await session.commit()

    return {"message": "Analysis deleted successfully"}
