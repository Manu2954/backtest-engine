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


@router.post("", response_model=BacktestOut)
async def create_backtest(
    payload: BacktestCreate,
    session: AsyncSession = Depends(get_session),
) -> BacktestRun:
    strategy = await session.get(Strategy, payload.strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    run = BacktestRun(
        strategy_id=payload.strategy_id,
        ticker=payload.ticker,
        asset_class=payload.asset_class,
        start_date=payload.start_date,
        end_date=payload.end_date,
        bar_resolution=payload.bar_resolution,
        initial_capital=payload.initial_capital,
        status="PENDING",
        periodic_contribution=payload.periodic_contribution,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    run.celery_task_id = run_backtest_task.delay(str(run.id)).id
    await session.commit()
    return run


@router.get("", response_model=list[BacktestOut])
async def list_backtests(
    user_id: str | None = Query(None),
    strategy_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[BacktestRun]:
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


@router.get("/{run_id}", response_model=BacktestOut)
async def get_backtest(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> BacktestRun:
    result = await session.execute(select(BacktestRun).where(BacktestRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return run


@router.get("/{run_id}/trades", response_model=list[TradeLogOut])
async def get_backtest_trades(
    run_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[TradeLog]:
    result = await session.execute(
        select(TradeLog)
        .where(TradeLog.run_id == run_id)
        .order_by(TradeLog.entry_date.asc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()
