from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.backtest import BacktestCreate, BacktestOut, TradeLogOut
from app.core.database import get_session
from app.models.backtest import BacktestRun, TradeLog
from app.models.strategy import Strategy
from app.tasks.backtest_task import run_backtest_task

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("", response_model=BacktestOut, summary="Run backtest")
async def create_backtest(
    payload: BacktestCreate,
    session: AsyncSession = Depends(get_session),
) -> BacktestRun:
    """
    Execute a backtest for a strategy.

    The backtest runs asynchronously via Celery. Poll the GET endpoint to check status.

    **Status progression**: PENDING → RUNNING → COMPLETE (or FAILED)

    **Report fields** (when COMPLETE):
    - Performance: total_return_pct, cagr, sharpe_ratio, max_drawdown_pct
    - Trade stats: total_trades, win_rate, profit_factor, avg_win, avg_loss
    - Benchmark: benchmark_return_pct, alpha, beta
    - Warmup info: requested_start_date, actual_start_date, warmup_bars_trimmed
    """
    strategy = await session.get(Strategy, payload.strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    run = BacktestRun(
        strategy_id=payload.strategy_id,
        ticker=payload.ticker,
        asset_class=payload.asset_class,
        provider=payload.provider,
        start_date=payload.start_date,
        end_date=payload.end_date,
        bar_resolution=payload.bar_resolution,
        initial_capital=payload.initial_capital,
        status="PENDING",
        periodic_contribution=payload.periodic_contribution,
        position_size_type=payload.position_size_type,
        position_size_value=payload.position_size_value,
        stop_loss_pct=payload.stop_loss_pct,
        take_profit_pct=payload.take_profit_pct,
        commission_per_trade=payload.commission_per_trade,
        commission_pct=payload.commission_pct,
        slippage_pct=payload.slippage_pct,
        enable_attribution=payload.enable_attribution,
        risk_free_rate=payload.risk_free_rate,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    run.celery_task_id = run_backtest_task.delay(str(run.id)).id
    await session.commit()
    return run


@router.get("", response_model=list[BacktestOut], summary="List backtests")
async def list_backtests(
    user_id: str | None = Query(None, description="Filter by user ID"),
    strategy_id: str | None = Query(None, description="Filter by strategy ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_session),
) -> list[BacktestRun]:
    """Retrieve all backtests with optional filtering by user or strategy."""
    query = select(BacktestRun)
    if strategy_id:
        query = query.where(BacktestRun.strategy_id == strategy_id)
    if user_id:
        query = query.join(Strategy, Strategy.id == BacktestRun.strategy_id).where(
            Strategy.user_id == user_id
        )
    query = query.order_by(BacktestRun.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{run_id}", response_model=BacktestOut, summary="Get backtest")
async def get_backtest(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> BacktestRun:
    """
    Retrieve a backtest by ID.

    Use this endpoint to poll for completion status and retrieve the final report.
    """
    result = await session.execute(select(BacktestRun).where(BacktestRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return run


@router.get("/{run_id}/trades", response_model=list[TradeLogOut], summary="Get trade log")
async def get_backtest_trades(
    run_id: UUID,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_session),
) -> list[TradeLog]:
    """
    Retrieve the trade log for a completed backtest.

    Each trade includes entry/exit dates, prices, PnL, and attribution data (if enabled).
    """
    result = await session.execute(
        select(TradeLog)
        .where(TradeLog.run_id == run_id)
        .order_by(TradeLog.entry_date.asc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.delete("/{run_id}", summary="Delete backtest")
async def delete_backtest(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete a backtest and all associated trade logs."""
    result = await session.execute(select(BacktestRun).where(BacktestRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    await session.delete(run)
    await session.commit()
    return {"status": "deleted", "id": str(run_id)}
