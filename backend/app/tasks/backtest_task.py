from __future__ import annotations

from datetime import date
import logging
from typing import Any

from app.celery_app import celery_app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.engine.condition_engine import evaluate_conditions, evaluate_expression
from app.engine.data_layer import fetch_ohlcv_async
from app.engine.indicator_layer import compute_indicators, trim_warmup_period
from app.engine.report_generator import generate_report, calculate_buy_and_hold_equity
from app.engine.state_machine import run_backtest
from app.models.backtest import BacktestRun, TradeLog
from app.models.strategy import ConditionGroup, Strategy

logger = logging.getLogger(__name__)


@celery_app.task(name="backtest.run")
def run_backtest_task(run_id: str) -> None:
    import asyncio

    logger.info("Task started for run_id=%s", run_id)
    asyncio.run(_run_backtest_async(run_id))


async def _run_backtest_async(run_id: str) -> None:
    engine = create_async_engine(settings.database_url, echo=False, future=True, poolclass=NullPool)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        run = await session.get(BacktestRun, run_id)
        if run is None:
            await engine.dispose()
            return

        run.status = "RUNNING"
        await session.commit()

        try:
            strategy = await _load_strategy(session, run.strategy_id)
            if strategy is None:
                raise ValueError("Strategy not found")

            logger.info("Fetching OHLCV")
            df = await fetch_ohlcv_async(
                run.ticker,
                run.start_date,
                run.end_date,
                run.bar_resolution,
                run.asset_class,
                session=session,
            )

            # Store original OHLCV data for benchmark calculation (before warmup trim)
            logger.info("Storing original OHLCV for benchmark")
            df_original = df[["open", "high", "low", "close", "volume"]].copy()

            logger.info("Computing indicators")
            indicators = [
                {
                    "indicator_type": ind.indicator_type,
                    "alias": ind.alias,
                    "params": ind.params,
                }
                for ind in strategy.indicators
            ]
            df = compute_indicators(df, indicators)

            # Trim warmup period where indicators have NaN values
            logger.info("Checking for indicator warmup period")
            df, warmup_bars = trim_warmup_period(df)
            if warmup_bars > 0:
                logger.info(f"Trimmed {warmup_bars} bars from warmup period. Starting backtest from bar {warmup_bars}.")

            # Validate we have enough data after warmup
            if len(df) < 30:
                raise ValueError(
                    f"Insufficient data after indicator warmup: {len(df)} bars remaining. "
                    f"Need at least 30 bars. Try extending the date range or using shorter indicator periods."
                )

            # Evaluate entry/exit signals
            logger.info("Evaluating conditions")

            # Check if strategy uses expressions
            if strategy.entry_expression:
                # Use expression-based evaluation
                entry_groups_dict = _build_groups_dict(strategy, "ENTRY")
                entry_signal = evaluate_expression(df, entry_groups_dict, strategy.entry_expression)
            else:
                # Legacy: single entry group
                entry_group = _group_to_payload(strategy, "ENTRY")
                entry_signal = evaluate_conditions(df, entry_group)

            if strategy.exit_expression:
                # Use expression-based evaluation
                exit_groups_dict = _build_groups_dict(strategy, "EXIT")
                exit_signal = evaluate_expression(df, exit_groups_dict, strategy.exit_expression)
            else:
                # Legacy: single exit group
                exit_group = _group_to_payload(strategy, "EXIT")
                exit_signal = evaluate_conditions(df, exit_group)

            logger.info("Running backtest")
            trades, equity_curve = run_backtest(
                df,
                entry_signal,
                exit_signal,
                float(run.initial_capital),
                asset_class=run.asset_class,
                periodic_contribution=run.periodic_contribution,
                # Position sizing parameters
                position_size_type=run.position_size_type or "full_capital",
                position_size_value=float(run.position_size_value or 100.0),
                # Risk management parameters
                stop_loss_pct=float(run.stop_loss_pct) if run.stop_loss_pct is not None else None,
                take_profit_pct=float(run.take_profit_pct) if run.take_profit_pct is not None else None,
                # Transaction cost parameters
                commission_per_trade=float(run.commission_per_trade or 0.0),
                commission_pct=float(run.commission_pct or 0.0),
                slippage_pct=float(run.slippage_pct or 0.0),
            )

            logger.info("Generating report and persisting trades")
            _persist_trades(session, run.id, trades)

            # Calculate buy-and-hold benchmark using ORIGINAL data (not trimmed)
            # This ensures benchmark buys at the actual start date, not after warmup trim
            logger.info("Calculating buy-and-hold benchmark from original OHLCV")
            benchmark_equity = calculate_buy_and_hold_equity(
                df_original, float(run.initial_capital), asset_class=run.asset_class
            )

            report = generate_report(
                trades, equity_curve, float(run.initial_capital), benchmark_equity=benchmark_equity
            )
            run.report = report
            run.status = "COMPLETE"
            await session.commit()
            logger.info("Task succeeded for run_id=%s", run_id)
        except Exception as exc:  # noqa: BLE001
            run.status = "FAILED"
            run.error_message = str(exc)
            await session.commit()
            logger.exception("Task failed for run_id=%s", run_id)

    await engine.dispose()


async def _load_strategy(session: AsyncSession, strategy_id) -> Strategy | None:
    result = await session.execute(
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .options(
            selectinload(Strategy.indicators),
            selectinload(Strategy.condition_groups).selectinload(ConditionGroup.conditions),
        )
    )
    return result.scalar_one_or_none()


def _group_to_payload(strategy: Strategy, group_type: str) -> dict[str, Any]:
    group = next((g for g in strategy.condition_groups if g.group_type == group_type), None)
    if group is None:
        raise ValueError(f"Missing {group_type} condition group")

    return {
        "logic": group.logic,
        "conditions": [
            {
                "left_operand_type": c.left_operand_type,
                "left_operand_value": c.left_operand_value,
                "operator": c.operator,
                "right_operand_type": c.right_operand_type,
                "right_operand_value": c.right_operand_value,
            }
            for c in group.conditions
        ],
    }


def _build_groups_dict(strategy: Strategy, group_type: str) -> dict[str, dict[str, Any]]:
    """
    Build a dictionary of named condition groups for expression evaluation.

    Args:
        strategy: Strategy with condition groups
        group_type: "ENTRY" or "EXIT"

    Returns:
        Dictionary mapping group names to condition group definitions
    """
    groups_dict = {}

    for group in strategy.condition_groups:
        if group.group_type != group_type:
            continue

        if not group.group_name:
            raise ValueError(
                f"Condition group of type {group_type} is missing group_name. "
                f"When using expressions, all groups must have names."
            )

        groups_dict[group.group_name] = {
            "logic": group.logic,
            "conditions": [
                {
                    "left_operand_type": c.left_operand_type,
                    "left_operand_value": c.left_operand_value,
                    "operator": c.operator,
                    "right_operand_type": c.right_operand_type,
                    "right_operand_value": c.right_operand_value,
                }
                for c in group.conditions
            ],
        }

    return groups_dict


def _persist_trades(
    session: AsyncSession,
    run_id,
    trades: list[dict[str, Any]],
) -> None:
    for trade in trades:
        session.add(
            TradeLog(
                run_id=run_id,
                entry_date=_to_date(trade["entry_date"]),
                entry_price=trade["entry_price"],
                exit_date=_to_date(trade["exit_date"]),
                exit_price=trade["exit_price"],
                shares=trade["shares"],
                pnl=trade["pnl"],
                pnl_pct=trade["pnl_pct"],
                trade_duration_days=trade["trade_duration_days"],
                exit_reason=trade.get("exit_reason", "signal"),  # NEW: Store exit reason
            )
        )


def _to_date(value) -> date:
    if isinstance(value, date):
        return value
    return value.date()
