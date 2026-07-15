from __future__ import annotations

from datetime import date, datetime
import logging
from typing import Any
import pandas as pd

from app.celery_app import celery_app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.engine.condition_engine import evaluate_conditions, evaluate_expression
from app.engine.data_layer import fetch_ohlcv_async
from app.engine.exit_rules import ExitRule
from app.engine.indicator_layer import compute_indicators, trim_warmup_period
from app.engine.report_generator import generate_report, generate_attribution_report, generate_binning_report, calculate_buy_and_hold_equity
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
                provider=run.provider,
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
                    "chart_type": ind.chart_type,  # May be None (inherit from strategy)
                }
                for ind in strategy.indicators
            ]
            logger.info(f"Indicators to compute: {indicators}")
            df = compute_indicators(df, indicators, strategy_chart_type=strategy.chart_type)

            # Restore raw OHLCV for fills if strategy uses non-standard chart type (e.g., Heikin-Ashi)
            # Indicators were computed on transformed data, but fills must use actual market prices
            if strategy.chart_type and strategy.chart_type != "ohlcv":
                logger.info(f"Restoring raw OHLCV for fills (strategy uses {strategy.chart_type})")
                df["open"] = df["raw_open"]
                df["high"] = df["raw_high"]
                df["low"] = df["raw_low"]
                df["close"] = df["raw_close"]

            # Trim warmup period where indicators have NaN values
            logger.info("Checking for indicator warmup period")
            df, warmup_bars = trim_warmup_period(df)

            # Capture actual trading start date after warmup
            requested_start_date = run.start_date
            actual_start_date = df.index[0].date() if not df.empty else requested_start_date

            if warmup_bars > 0:
                logger.info(f"Trimmed {warmup_bars} bars from warmup period. Starting backtest from bar {warmup_bars}.")
                logger.info(f"Requested start: {requested_start_date}, Actual start after warmup: {actual_start_date}")

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
                entry_groups_dict = _build_groups_dict(strategy, "ENTRY")
                entry_signal = evaluate_expression(df, entry_groups_dict, strategy.entry_expression)
            else:
                entry_group = _group_to_payload(strategy, "ENTRY")
                entry_signal = evaluate_conditions(df, entry_group)

            if strategy.exit_expression:
                exit_groups_dict = _build_groups_dict(strategy, "EXIT")
                exit_signal = evaluate_expression(df, exit_groups_dict, strategy.exit_expression)
            else:
                exit_group = _group_to_payload(strategy, "EXIT")
                exit_signal = evaluate_conditions(df, exit_group)

            # Evaluate SHORT entry/exit signals (if strategy defines them)
            short_entry_signal = None
            short_exit_signal = None

            has_short_entry = strategy.short_entry_expression or any(
                g.group_type == "SHORT_ENTRY" for g in strategy.condition_groups
            )
            has_short_exit = strategy.short_exit_expression or any(
                g.group_type == "SHORT_EXIT" for g in strategy.condition_groups
            )

            if has_short_entry:
                if strategy.short_entry_expression:
                    short_entry_groups_dict = _build_groups_dict(strategy, "SHORT_ENTRY")
                    short_entry_signal = evaluate_expression(df, short_entry_groups_dict, strategy.short_entry_expression)
                else:
                    short_entry_group = _group_to_payload(strategy, "SHORT_ENTRY")
                    short_entry_signal = evaluate_conditions(df, short_entry_group)

            if has_short_exit:
                if strategy.short_exit_expression:
                    short_exit_groups_dict = _build_groups_dict(strategy, "SHORT_EXIT")
                    short_exit_signal = evaluate_expression(df, short_exit_groups_dict, strategy.short_exit_expression)
                else:
                    short_exit_group = _group_to_payload(strategy, "SHORT_EXIT")
                    short_exit_signal = evaluate_conditions(df, short_exit_group)

            logger.info("Running backtest")

            # Prepare condition groups for attribution (if enabled)
            entry_conditions_for_attribution = None
            exit_conditions_for_attribution = None
            short_entry_conditions_for_attribution = None
            short_exit_conditions_for_attribution = None
            if run.enable_attribution:
                entry_conditions_for_attribution = _group_to_payload(strategy, "ENTRY") if not strategy.entry_expression else _build_groups_dict(strategy, "ENTRY")
                exit_conditions_for_attribution = _group_to_payload(strategy, "EXIT") if not strategy.exit_expression else _build_groups_dict(strategy, "EXIT")
                if has_short_entry:
                    short_entry_conditions_for_attribution = _group_to_payload(strategy, "SHORT_ENTRY") if not strategy.short_entry_expression else _build_groups_dict(strategy, "SHORT_ENTRY")
                if has_short_exit:
                    short_exit_conditions_for_attribution = _group_to_payload(strategy, "SHORT_EXIT") if not strategy.short_exit_expression else _build_groups_dict(strategy, "SHORT_EXIT")

            trades, equity_curve = run_backtest(
                df,
                entry_signal,
                exit_signal,
                float(run.initial_capital),
                asset_class=run.asset_class,
                periodic_contribution=run.periodic_contribution,
                position_size_type=run.position_size_type or "full_capital",
                position_size_value=float(run.position_size_value or 100.0),
                stop_loss_pct=float(run.stop_loss_pct) if run.stop_loss_pct is not None else None,
                take_profit_pct=float(run.take_profit_pct) if run.take_profit_pct is not None else None,
                commission_per_trade=float(run.commission_per_trade or 0.0),
                commission_pct=float(run.commission_pct or 0.0),
                slippage_pct=float(run.slippage_pct or 0.0),
                enable_attribution=run.enable_attribution,
                entry_conditions=entry_conditions_for_attribution,
                exit_conditions=exit_conditions_for_attribution,
                short_entry_signal=short_entry_signal,
                short_exit_signal=short_exit_signal,
                short_entry_conditions=short_entry_conditions_for_attribution,
                short_exit_conditions=short_exit_conditions_for_attribution,
                # Advanced features
                leverage=float(run.leverage) if run.leverage is not None else 1.0,
                dynamic_stop_column=run.dynamic_stop_column,
                dynamic_tp_pct_column=run.dynamic_tp_pct_column,
                enable_counter_trades=run.enable_counter_trades if run.enable_counter_trades is not None else False,
                counter_tp_multiplier=float(run.counter_tp_multiplier) if run.counter_tp_multiplier is not None else 1.5,
                exit_rules=[ExitRule(**r) for r in run.exit_rules] if run.exit_rules else None,
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
                trades, equity_curve, float(run.initial_capital),
                benchmark_equity=benchmark_equity,
                risk_free_rate=float(run.risk_free_rate or 0.0),
            )

            # Add warmup information to report
            report["requested_start_date"] = str(requested_start_date)
            report["actual_start_date"] = str(actual_start_date)
            report["warmup_bars_trimmed"] = warmup_bars
            if warmup_bars > 0:
                report["warmup_note"] = (
                    f"Backtest started {warmup_bars} bars after requested date due to indicator warmup. "
                    f"Requested: {requested_start_date}, Actual: {actual_start_date}"
                )

            # Add equity curve for frontend charting
            # Format: [{"date": "YYYY-MM-DD", "equity": float, "benchmark": float}, ...]
            equity_curve_list = []
            for idx, val in equity_curve.items():
                entry = {
                    "date": str(idx.date()) if hasattr(idx, 'date') else str(idx),
                    "equity": float(val) if val is not None else 0.0,
                }
                # Add benchmark if available
                if benchmark_equity is not None and idx in benchmark_equity.index:
                    entry["benchmark"] = float(benchmark_equity.loc[idx])
                equity_curve_list.append(entry)
            report["equity_curve"] = equity_curve_list

            # Generate attribution report if enabled
            if run.enable_attribution:
                logger.info("Generating attribution report")
                attribution_report = generate_attribution_report(trades)
                if attribution_report:
                    report["attribution"] = attribution_report

                # Generate binning analysis report (diagnostic tool)
                logger.info("Generating binning analysis report")
                all_conditions = []
                for group in strategy.condition_groups:
                    for cond in group.conditions:
                        all_conditions.append({
                            "operator": cond.operator,
                            "left_operand_value": cond.left_operand_value,
                            "right_operand_value": cond.right_operand_value
                        })

                binning_report = generate_binning_report(
                    trades,
                    indicators,
                    conditions=all_conditions if all_conditions else None
                )
                if binning_report:
                    report["binning_analysis"] = binning_report

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
        if group_type in ("SHORT_ENTRY", "SHORT_EXIT"):
            return {"logic": "AND", "conditions": []}
        raise ValueError(f"Missing {group_type} condition group")

    return {
        "logic": group.logic,
        "conditions": [
            {
                "id": str(c.id),
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
                    "id": str(c.id),
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
                entry_date=_to_datetime(trade["entry_date"]),
                entry_price=trade["entry_price"],
                exit_date=_to_datetime(trade["exit_date"]),
                exit_price=trade["exit_price"],
                shares=trade["shares"],
                pnl=trade["pnl"],
                pnl_pct=trade["pnl_pct"],
                trade_duration_days=trade["trade_duration_days"],
                exit_reason=trade.get("exit_reason", "signal"),
                direction=trade.get("direction", "LONG"),
                # Attribution fields (optional)
                entry_conditions_met=trade.get("entry_conditions_met"),
                exit_conditions_met=trade.get("exit_conditions_met"),
                entry_signal_strength=trade.get("entry_signal_strength"),
                market_return_during_trade=trade.get("market_return_during_trade"),
                alpha=trade.get("alpha"),
                indicator_snapshot_entry=trade.get("indicator_snapshot_entry"),
                indicator_snapshot_exit=trade.get("indicator_snapshot_exit"),
            )
        )


def _to_datetime(value) -> datetime:
    """Convert pandas Timestamp or datetime to datetime."""
    if isinstance(value, datetime):
        return value
    if hasattr(value, 'to_pydatetime'):
        return value.to_pydatetime()
    return pd.to_datetime(value).to_pydatetime()
