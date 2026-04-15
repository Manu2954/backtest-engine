"""
Celery task for parameter sensitivity analysis.

Orchestrates parallel backtest execution for strategy variants.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.celery_app import celery_app
from app.core.config import settings
from app.engine.robustness.parameter_sensitivity import (
    assess_robustness_level,
    calculate_stability_score,
    generate_parameter_variants,
    generate_recommendation,
    generate_risk_flags,
)
from app.models.backtest import BacktestRun
from app.models.robustness import RobustnessAnalysis, RobustnessVariantBacktest
from app.models.strategy import Strategy, Indicator, ConditionGroup, Condition
from app.tasks.backtest_task import run_backtest_task


async def _create_temporary_strategy(
    base_strategy: Strategy,
    variant_data: dict[str, Any],
    session_maker,
) -> UUID:
    """
    Create temporary strategy with modified indicator parameters.

    Args:
        base_strategy: Original strategy
        variant_data: Variant info with modified strategy dict
        session_maker: Async session maker

    Returns:
        UUID of created temporary strategy
    """
    import logging
    logger = logging.getLogger(__name__)

    variant_strategy_dict = variant_data["strategy"]
    variant_label = variant_data["variant_label"]

    # Create temporary strategy
    temp_strategy = Strategy(
        id=uuid4(),
        user_id=base_strategy.user_id,
        name=f"[TEMP] {base_strategy.name} - {variant_label}",
        description=f"Temporary variant for parameter sensitivity analysis",
        entry_expression=base_strategy.entry_expression,
        exit_expression=base_strategy.exit_expression,
    )

    async with session_maker() as session:
        session.add(temp_strategy)

        # Add indicators
        for ind_data in variant_strategy_dict["indicators"]:
            logger.info(f"Creating indicator: alias={ind_data['alias']}, type={ind_data['indicator_type']}, params={ind_data['params']}")
            indicator = Indicator(
                id=uuid4(),
                strategy_id=temp_strategy.id,
                alias=ind_data["alias"],
                indicator_type=ind_data["indicator_type"],
                params=ind_data["params"],
                display_order=0,
            )
            session.add(indicator)

        # Add condition groups and conditions
        for cg_data in variant_strategy_dict["condition_groups"]:
            condition_group = ConditionGroup(
                id=uuid4(),
                strategy_id=temp_strategy.id,
                group_type=cg_data["group_type"],
                group_name=cg_data.get("group_name"),
                logic=cg_data["logic"],
            )
            session.add(condition_group)

            for cond_data in cg_data["conditions"]:
                condition = Condition(
                    id=uuid4(),
                    group_id=condition_group.id,
                    left_operand_type=cond_data["left_operand_type"],
                    left_operand_value=cond_data["left_operand_value"],
                    operator=cond_data["operator"],
                    right_operand_type=cond_data["right_operand_type"],
                    right_operand_value=cond_data["right_operand_value"],
                    display_order=0,
                )
                session.add(condition)

        await session.commit()

    return temp_strategy.id


async def _delete_temporary_strategy(strategy_id: UUID, session_maker) -> None:
    """Delete temporary strategy and all related data."""
    async with session_maker() as session:
        stmt = select(Strategy).where(Strategy.id == strategy_id)
        result = await session.execute(stmt)
        strategy = result.scalar_one_or_none()

        if strategy:
            await session.delete(strategy)
            await session.commit()


async def _create_backtest_run(
    strategy_id: UUID,
    backtest_params: dict[str, Any],
    session_maker,
) -> UUID:
    """Create a BacktestRun record for a variant."""
    # Convert date strings to date objects if needed
    start_date = backtest_params["start_date"]
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

    end_date = backtest_params["end_date"]
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    run = BacktestRun(
        strategy_id=strategy_id,
        ticker=backtest_params["ticker"],
        asset_class=backtest_params.get("asset_class", "STOCK"),
        provider=backtest_params.get("provider", "yfinance"),
        start_date=start_date,
        end_date=end_date,
        bar_resolution=backtest_params.get("bar_resolution", "1d"),
        initial_capital=backtest_params["initial_capital"],
        status="PENDING",
        periodic_contribution=backtest_params.get("periodic_contribution"),
        position_size_type=backtest_params.get("position_size_type", "full_capital"),
        position_size_value=backtest_params.get("position_size_value", 100.0),
        stop_loss_pct=backtest_params.get("stop_loss_pct"),
        take_profit_pct=backtest_params.get("take_profit_pct"),
        commission_per_trade=backtest_params.get("commission_per_trade", 0.0),
        commission_pct=backtest_params.get("commission_pct", 0.0),
        slippage_pct=backtest_params.get("slippage_pct", 0.0),
        enable_attribution=backtest_params.get("enable_attribution", False),
    )

    async with session_maker() as session:
        session.add(run)
        await session.commit()
        await session.refresh(run)

    return run.id


async def _get_strategy(strategy_id: UUID, session_maker) -> Strategy:
    """Load strategy with all relationships."""
    async with session_maker() as session:
        stmt = (
            select(Strategy)
            .where(Strategy.id == strategy_id)
            .options(
                selectinload(Strategy.indicators),
                selectinload(Strategy.condition_groups).selectinload(
                    ConditionGroup.conditions
                ),
            )
        )
        result = await session.execute(stmt)
        strategy = result.scalar_one()

    return strategy


async def _create_analysis_record(
    strategy_id: UUID,
    params: dict[str, Any],
    session_maker,
) -> RobustnessAnalysis:
    """Create initial analysis record with PENDING status."""
    analysis = RobustnessAnalysis(
        id=uuid4(),
        strategy_id=strategy_id,
        analysis_type="PARAMETER_SENSITIVITY",
        status="PENDING",
        params=params,
    )

    async with session_maker() as session:
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)

    return analysis


async def _update_analysis_status(
    analysis_id: UUID,
    status: str,
    session_maker,
    report: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    """Update analysis status and results."""
    async with session_maker() as session:
        stmt = select(RobustnessAnalysis).where(RobustnessAnalysis.id == analysis_id)
        result = await session.execute(stmt)
        analysis = result.scalar_one()

        analysis.status = status
        if report:
            analysis.report = report
        if error_message:
            analysis.error_message = error_message
        if status in ["COMPLETE", "FAILED"]:
            analysis.completed_at = datetime.utcnow()

        await session.commit()


async def _link_backtest_to_analysis(
    analysis_id: UUID,
    backtest_run_id: UUID,
    variant_label: str,
    variant_params: dict[str, Any],
    session_maker,
) -> None:
    """Link a backtest run to the analysis."""
    link = RobustnessVariantBacktest(
        id=uuid4(),
        analysis_id=analysis_id,
        backtest_run_id=backtest_run_id,
        variant_label=variant_label,
        variant_params=variant_params,
    )

    async with session_maker() as session:
        session.add(link)
        await session.commit()


async def _wait_for_backtest_completion(
    run_id: UUID,
    session_maker,
    timeout: int = 300,
) -> None:
    """Poll the database until the backtest completes or times out."""
    import time
    start_time = time.time()

    while time.time() - start_time < timeout:
        async with session_maker() as session:
            stmt = select(BacktestRun).where(BacktestRun.id == run_id)
            result = await session.execute(stmt)
            run = result.scalar_one()

            if run.status == "COMPLETE":
                return
            elif run.status == "FAILED":
                raise RuntimeError(f"Backtest failed: {run.error_message}")

        await asyncio.sleep(2)  # Poll every 2 seconds

    raise TimeoutError(f"Backtest {run_id} did not complete within {timeout} seconds")


async def _get_backtest_metrics(backtest_run_id: UUID, session_maker) -> dict[str, float]:
    """Extract key metrics from backtest report."""
    async with session_maker() as session:
        stmt = select(BacktestRun).where(BacktestRun.id == backtest_run_id)
        result = await session.execute(stmt)
        backtest = result.scalar_one()

        if not backtest.report:
            return {}

        report = backtest.report
        metrics = {
            "total_return_pct": report.get("total_return_pct", 0.0),
            "sharpe_ratio": report.get("sharpe_ratio", 0.0),
            "win_rate": report.get("win_rate", 0.0),
            "max_drawdown_pct": report.get("max_drawdown_pct", 0.0),
            "profit_factor": report.get("profit_factor", 0.0),
            "total_trades": report.get("total_trades", 0),
        }

    return metrics


@celery_app.task(name="robustness.parameter_sensitivity")
def run_parameter_sensitivity_analysis(
    strategy_id: str,
    backtest_params: dict[str, Any],
    variation_pct: float = 0.2,
) -> str:
    """
    Run parameter sensitivity analysis.

    Creates strategy variants, runs backtests in parallel, analyzes stability.

    Args:
        strategy_id: UUID of strategy to analyze
        backtest_params: Backtest configuration (ticker, dates, capital, etc.)
        variation_pct: Parameter variation percentage (default: 0.2 = ±20%)

    Returns:
        analysis_id (UUID string)
    """
    # Create engine once for entire task
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        poolclass=NullPool,
    )
    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        # Run the entire async workflow with shared engine
        return asyncio.run(
            _run_analysis_async(
                strategy_id,
                backtest_params,
                variation_pct,
                session_maker,
            )
        )
    finally:
        # Dispose engine after task completes
        asyncio.run(engine.dispose())


async def _run_analysis_async(
    strategy_id: str,
    backtest_params: dict[str, Any],
    variation_pct: float,
    session_maker,
) -> str:
    """Async implementation of parameter sensitivity analysis."""
    strategy_uuid = UUID(strategy_id)

    # Create analysis record
    analysis = await _create_analysis_record(
        strategy_uuid,
        {
            "variation_pct": variation_pct,
            "backtest_params": backtest_params,
        },
        session_maker,
    )

    # Track temp strategies for cleanup
    temp_strategy_ids = []

    try:
        # Update status to RUNNING
        await _update_analysis_status(analysis.id, "RUNNING", session_maker)

        # Load strategy
        strategy = await _get_strategy(strategy_uuid, session_maker)

        # Convert strategy to dict
        strategy_dict = {
            "id": str(strategy.id),
            "name": strategy.name,
            "description": strategy.description,
            "indicators": [
                {
                    "alias": ind.alias,
                    "indicator_type": ind.indicator_type,
                    "params": ind.params,
                }
                for ind in strategy.indicators
            ],
            "condition_groups": [
                {
                    "group_type": cg.group_type,
                    "group_name": cg.group_name,
                    "logic": cg.logic,
                    "conditions": [
                        {
                            "left_operand_type": c.left_operand_type,
                            "left_operand_value": c.left_operand_value,
                            "operator": c.operator,
                            "right_operand_type": c.right_operand_type,
                            "right_operand_value": c.right_operand_value,
                        }
                        for c in cg.conditions
                    ],
                }
                for cg in strategy.condition_groups
            ],
            "entry_expression": strategy.entry_expression,
            "exit_expression": strategy.exit_expression,
        }

        # Run baseline backtest first
        baseline_run_id = await _create_backtest_run(
            strategy_uuid,
            backtest_params,
            session_maker,
        )
        run_backtest_task.apply_async(args=[str(baseline_run_id)])

        # Wait for baseline to complete
        await _wait_for_backtest_completion(baseline_run_id, session_maker)

        await _link_backtest_to_analysis(
            analysis.id,
            baseline_run_id,
            "Baseline (original parameters)",
            {"baseline": True},
            session_maker,
        )

        baseline_metrics = await _get_backtest_metrics(baseline_run_id, session_maker)

        # Generate variants
        variants = generate_parameter_variants(strategy_dict, variation_pct)

        if not variants:
            # No variants generated (no numeric params or all too small)
            report = {
                "baseline": {
                    "strategy_id": strategy_id,
                    "params": {
                        ind.alias: ind.params
                        for ind in strategy.indicators
                    },
                    "metrics": baseline_metrics,
                },
                "variants": [],
                "stability_metrics": {
                    "overall_stability_score": 1.0,  # Perfect stability (no variation possible)
                    "per_metric_cv": {},
                },
                "assessment": {
                    "robustness_level": "ROBUST",
                    "risk_flags": [],
                    "recommendation": "No numeric parameters to vary. Strategy has no parameter sensitivity.",
                },
            }
            await _update_analysis_status(
                analysis.id,
                "COMPLETE",
                session_maker,
                report=report,
            )
            return str(analysis.id)

        # Create temporary strategies for each variant
        variant_labels = []
        variant_params_list = []

        for variant_data in variants:
            temp_strategy_id = await _create_temporary_strategy(
                strategy,
                variant_data,
                session_maker,
            )
            temp_strategy_ids.append(temp_strategy_id)
            variant_labels.append(variant_data["variant_label"])
            variant_params_list.append(variant_data["variant_params"])

        # Create BacktestRun records for each variant
        variant_run_ids = []
        for temp_id in temp_strategy_ids:
            run_id = await _create_backtest_run(temp_id, backtest_params, session_maker)
            variant_run_ids.append(run_id)

        # Run variant backtests in parallel using Celery
        for run_id in variant_run_ids:
            run_backtest_task.apply_async(args=[str(run_id)])

        # Wait for all variants to complete (in parallel)
        await asyncio.gather(*[
            _wait_for_backtest_completion(run_id, session_maker)
            for run_id in variant_run_ids
        ])

        # Link variant backtests to analysis and collect metrics
        variant_metrics_list = []
        for i, run_id in enumerate(variant_run_ids):
            # Link to analysis
            await _link_backtest_to_analysis(
                analysis.id,
                run_id,
                variant_labels[i],
                variant_params_list[i],
                session_maker,
            )

            # Get metrics
            metrics = await _get_backtest_metrics(run_id, session_maker)
            variant_metrics_list.append(metrics)

        # Calculate stability metrics
        stability_score, metric_cvs = calculate_stability_score(
            baseline_metrics,
            variant_metrics_list,
        )

        robustness_level = assess_robustness_level(stability_score)
        risk_flags = generate_risk_flags(baseline_metrics, variant_metrics_list, metric_cvs)
        recommendation = generate_recommendation(robustness_level, risk_flags, stability_score)

        # Build comprehensive report
        report = {
            "baseline": {
                "strategy_id": strategy_id,
                "params": {
                    ind.alias: ind.params
                    for ind in strategy.indicators
                },
                "metrics": baseline_metrics,
            },
            "variants": [
                {
                    "variant_label": variant_labels[i],
                    "variant_params": variant_params_list[i],
                    "metrics": variant_metrics_list[i],
                    "delta_from_baseline": {
                        metric_name: variant_metrics_list[i].get(metric_name, 0) - baseline_metrics.get(metric_name, 0)
                        for metric_name in ["total_return_pct", "sharpe_ratio", "win_rate", "max_drawdown_pct"]
                    }
                }
                for i in range(len(variants))
            ],
            "stability_metrics": {
                "overall_stability_score": stability_score,
                "per_metric_cv": metric_cvs,
            },
            "assessment": {
                "robustness_level": robustness_level,
                "risk_flags": risk_flags,
                "recommendation": recommendation,
            },
        }

        # Clean up temporary strategies
        for temp_id in temp_strategy_ids:
            await _delete_temporary_strategy(temp_id, session_maker)

        await _update_analysis_status(
            analysis.id,
            "COMPLETE",
            session_maker,
            report=report,
        )
        return str(analysis.id)

    except Exception as e:
        # Clean up temp strategies on error
        for temp_id in temp_strategy_ids:
            try:
                await _delete_temporary_strategy(temp_id, session_maker)
            except Exception:
                pass  # Best effort cleanup

        await _update_analysis_status(
            analysis.id,
            "FAILED",
            session_maker,
            error_message=str(e),
        )
        raise
