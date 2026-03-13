from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.strategy import (
    ConditionCreate,
    ConditionGroupCreate,
    StrategyCreate,
    StrategyUpdate,
    StrategyOut,
)
from app.core.database import get_session
from app.models.strategy import Condition, ConditionGroup, Indicator, Strategy

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("", response_model=list[StrategyOut])
async def list_strategies(
    user_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[Strategy]:
    query = select(Strategy).options(
        selectinload(Strategy.indicators),
        selectinload(Strategy.condition_groups).selectinload(ConditionGroup.conditions),
    )
    if user_id:
        query = query.where(Strategy.user_id == user_id)
    query = query.order_by(Strategy.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("", response_model=StrategyOut)
async def create_strategy(
    payload: StrategyCreate,
    session: AsyncSession = Depends(get_session),
) -> Strategy:
    strategy = Strategy(
        name=payload.name,
        description=payload.description,
        entry_expression=payload.entry_expression,
        exit_expression=payload.exit_expression,
    )

    for idx, indicator in enumerate(payload.indicators):
        strategy.indicators.append(
            Indicator(
                alias=indicator.alias,
                indicator_type=indicator.indicator_type,
                params=indicator.params,
                display_order=indicator.display_order or idx,
            )
        )

    # Handle legacy single entry/exit groups (backward compatible)
    if payload.entry and payload.exit:
        entry_group = _build_group("ENTRY", payload.entry, group_name=None)
        exit_group = _build_group("EXIT", payload.exit, group_name=None)
        strategy.condition_groups.extend([entry_group, exit_group])

    # Handle new expression-based groups
    if payload.entry_groups:
        for group_name, group_def in payload.entry_groups.items():
            group = _build_group("ENTRY", group_def, group_name=group_name)
            strategy.condition_groups.append(group)

    if payload.exit_groups:
        for group_name, group_def in payload.exit_groups.items():
            group = _build_group("EXIT", group_def, group_name=group_name)
            strategy.condition_groups.append(group)

    session.add(strategy)
    await session.commit()
    return await _fetch_strategy(session, strategy.id)


@router.get("/{strategy_id}", response_model=StrategyOut)
async def get_strategy(
    strategy_id: str,
    session: AsyncSession = Depends(get_session),
) -> Strategy:
    strategy = await _fetch_strategy(session, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.put("/{strategy_id}", response_model=StrategyOut)
async def update_strategy(
    strategy_id: str,
    payload: StrategyUpdate,
    session: AsyncSession = Depends(get_session),
) -> Strategy:
    strategy = await _fetch_strategy(session, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy.name = payload.name
    strategy.description = payload.description
    strategy.entry_expression = payload.entry_expression
    strategy.exit_expression = payload.exit_expression

    # Replace indicators and condition groups
    strategy.indicators.clear()
    strategy.condition_groups.clear()

    for idx, indicator in enumerate(payload.indicators):
        strategy.indicators.append(
            Indicator(
                alias=indicator.alias,
                indicator_type=indicator.indicator_type,
                params=indicator.params,
                display_order=indicator.display_order or idx,
            )
        )

    # Handle legacy single entry/exit groups (backward compatible)
    if payload.entry and payload.exit:
        entry_group = _build_group("ENTRY", payload.entry, group_name=None)
        exit_group = _build_group("EXIT", payload.exit, group_name=None)
        strategy.condition_groups.extend([entry_group, exit_group])

    # Handle new expression-based groups
    if payload.entry_groups:
        for group_name, group_def in payload.entry_groups.items():
            group = _build_group("ENTRY", group_def, group_name=group_name)
            strategy.condition_groups.append(group)

    if payload.exit_groups:
        for group_name, group_def in payload.exit_groups.items():
            group = _build_group("EXIT", group_def, group_name=group_name)
            strategy.condition_groups.append(group)

    await session.commit()
    return await _fetch_strategy(session, strategy.id)


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    strategy = await session.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    await session.delete(strategy)
    await session.commit()
    return {"status": "deleted"}


async def _fetch_strategy(session: AsyncSession, strategy_id: str) -> Strategy | None:
    result = await session.execute(
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .options(
            selectinload(Strategy.indicators),
            selectinload(Strategy.condition_groups).selectinload(ConditionGroup.conditions),
        )
    )
    return result.scalar_one_or_none()


def _build_group(group_type: str, group: ConditionGroupCreate, group_name: str | None = None) -> ConditionGroup:
    condition_group = ConditionGroup(
        group_type=group_type,
        logic=group.logic,
        group_name=group_name or group.group_name,
    )
    for idx, cond in enumerate(group.conditions):
        condition_group.conditions.append(_build_condition(cond, idx))
    return condition_group


def _build_condition(cond: ConditionCreate, idx: int) -> Condition:
    return Condition(
        left_operand_type=cond.left_operand_type,
        left_operand_value=cond.left_operand_value,
        operator=cond.operator,
        right_operand_type=cond.right_operand_type,
        right_operand_value=cond.right_operand_value,
        display_order=cond.display_order or idx,
    )
