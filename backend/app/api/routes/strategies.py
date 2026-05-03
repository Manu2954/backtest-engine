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


@router.get("", response_model=list[StrategyOut], summary="List strategies")
async def list_strategies(
    user_id: str | None = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_session),
) -> list[Strategy]:
    """
    Retrieve all strategies with their indicators and condition groups.

    Supports pagination via limit/offset parameters.
    """
    query = select(Strategy).options(
        selectinload(Strategy.indicators),
        selectinload(Strategy.condition_groups).selectinload(ConditionGroup.conditions),
    )
    if user_id:
        query = query.where(Strategy.user_id == user_id)
    query = query.order_by(Strategy.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("", response_model=StrategyOut, summary="Create strategy")
async def create_strategy(
    payload: StrategyCreate,
    session: AsyncSession = Depends(get_session),
) -> Strategy:
    """
    Create a new trading strategy.

    A strategy consists of:
    - **Indicators**: Technical indicators (SMA, EMA, RSI, MACD, etc.) with configurable parameters
    - **Entry conditions**: Rules that trigger position entry (e.g., SMA crossover, RSI oversold)
    - **Exit conditions**: Rules that trigger position exit

    Conditions can be combined using AND/OR logic and grouped into named groups
    for complex entry/exit expressions like `(groupA AND groupB) OR groupC`.
    """
    strategy = Strategy(
        name=payload.name,
        description=payload.description,
        entry_expression=payload.entry_expression,
        exit_expression=payload.exit_expression,
        short_entry_expression=payload.short_entry_expression,
        short_exit_expression=payload.short_exit_expression,
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

    # Handle short selling groups
    if payload.short_entry:
        strategy.condition_groups.append(_build_group("SHORT_ENTRY", payload.short_entry, group_name=None))

    if payload.short_exit:
        strategy.condition_groups.append(_build_group("SHORT_EXIT", payload.short_exit, group_name=None))

    if payload.short_entry_groups:
        for group_name, group_def in payload.short_entry_groups.items():
            strategy.condition_groups.append(_build_group("SHORT_ENTRY", group_def, group_name=group_name))

    if payload.short_exit_groups:
        for group_name, group_def in payload.short_exit_groups.items():
            strategy.condition_groups.append(_build_group("SHORT_EXIT", group_def, group_name=group_name))

    session.add(strategy)
    await session.commit()
    return await _fetch_strategy(session, strategy.id)


@router.get("/{strategy_id}", response_model=StrategyOut, summary="Get strategy")
async def get_strategy(
    strategy_id: str,
    session: AsyncSession = Depends(get_session),
) -> Strategy:
    """Retrieve a strategy by ID with all indicators and condition groups."""
    strategy = await _fetch_strategy(session, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.put("/{strategy_id}", response_model=StrategyOut, summary="Update strategy")
async def update_strategy(
    strategy_id: str,
    payload: StrategyUpdate,
    session: AsyncSession = Depends(get_session),
) -> Strategy:
    """
    Update an existing strategy.

    Replaces all indicators and condition groups with the new values.
    """
    strategy = await _fetch_strategy(session, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy.name = payload.name
    strategy.description = payload.description
    strategy.entry_expression = payload.entry_expression
    strategy.exit_expression = payload.exit_expression
    strategy.short_entry_expression = payload.short_entry_expression
    strategy.short_exit_expression = payload.short_exit_expression

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

    # Handle short selling groups
    if payload.short_entry:
        strategy.condition_groups.append(_build_group("SHORT_ENTRY", payload.short_entry, group_name=None))

    if payload.short_exit:
        strategy.condition_groups.append(_build_group("SHORT_EXIT", payload.short_exit, group_name=None))

    if payload.short_entry_groups:
        for group_name, group_def in payload.short_entry_groups.items():
            strategy.condition_groups.append(_build_group("SHORT_ENTRY", group_def, group_name=group_name))

    if payload.short_exit_groups:
        for group_name, group_def in payload.short_exit_groups.items():
            strategy.condition_groups.append(_build_group("SHORT_EXIT", group_def, group_name=group_name))

    await session.commit()
    return await _fetch_strategy(session, strategy.id)


@router.delete("/{strategy_id}", summary="Delete strategy")
async def delete_strategy(
    strategy_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """
    Delete a strategy and all associated backtests.

    This action is irreversible.
    """
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
