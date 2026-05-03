"""
Celery tasks for robustness analysis.

Includes:
- Parameter sensitivity analysis
- Walk-forward validation
- Regime detection
"""
from __future__ import annotations

import asyncio
import logging
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
from app.engine.robustness.walk_forward import (
    generate_windows,
    calculate_consistency_score as calculate_wf_consistency_score,
    assess_walk_forward_results,
    build_walk_forward_report,
)
from app.engine.robustness.regime_detection import (
    detect_regimes,
    analyze_trades_by_regime,
    calculate_regime_distribution,
    assess_regime_dependency,
    build_regime_report,
)
from app.engine.robustness.feature_conditioning import (
    extract_trade_features,
    analyze_feature_conditions,
    build_feature_conditioning_report,
)
from app.models.backtest import BacktestRun
from app.models.robustness import RobustnessAnalysis, RobustnessVariantBacktest
from app.models.strategy import Strategy, Indicator, ConditionGroup, Condition
from app.tasks.backtest_task import run_backtest_task

logger = logging.getLogger(__name__)


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


# =============================================================================
# Walk-Forward Validation
# =============================================================================

@celery_app.task(name="robustness.walk_forward")
def run_walk_forward_validation(
    strategy_id: str,
    backtest_params: dict[str, Any],
    window_count: int = 5,
) -> str:
    """
    Run walk-forward validation.

    Tests strategy across rolling time windows to detect period-dependency.
    Uses fixed parameters - validates if strategy works consistently.

    Args:
        strategy_id: UUID of strategy to analyze
        backtest_params: Backtest configuration (ticker, dates, capital, etc.)
        window_count: Number of windows to divide data into (default: 5)

    Returns:
        analysis_id (UUID string)
    """
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
        return asyncio.run(
            _run_walk_forward_async(
                strategy_id,
                backtest_params,
                window_count,
                session_maker,
            )
        )
    finally:
        asyncio.run(engine.dispose())


async def _run_walk_forward_async(
    strategy_id: str,
    backtest_params: dict[str, Any],
    window_count: int,
    session_maker,
) -> str:
    """Async implementation of walk-forward validation."""
    from app.engine.data_layer import fetch_ohlcv_async
    from app.engine.indicator_layer import compute_indicators, trim_warmup_period
    from app.engine.condition_engine import evaluate_conditions, evaluate_expression
    from app.engine.state_machine import run_backtest
    from app.engine.report_generator import generate_report

    strategy_uuid = UUID(strategy_id)

    # Create analysis record
    analysis = await _create_walk_forward_analysis_record(
        strategy_uuid,
        {
            "window_count": window_count,
            "backtest_params": backtest_params,
        },
        session_maker,
    )

    try:
        await _update_analysis_status(analysis.id, "RUNNING", session_maker)

        # Load strategy
        strategy = await _get_strategy(strategy_uuid, session_maker)

        # Parse dates
        start_date = backtest_params["start_date"]
        end_date = backtest_params["end_date"]
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Step 1: Fetch full OHLCV data
        logger.info(f"Walk-forward: Fetching OHLCV for {backtest_params['ticker']}")
        async with session_maker() as session:
            df = await fetch_ohlcv_async(
                backtest_params["ticker"],
                start_date,
                end_date,
                backtest_params.get("bar_resolution", "1d"),
                backtest_params.get("asset_class", "STOCK"),
                session=session,
                provider=backtest_params.get("provider"),
            )

        # Step 2: Compute all indicators once
        logger.info("Walk-forward: Computing indicators")
        indicators = [
            {
                "indicator_type": ind.indicator_type,
                "alias": ind.alias,
                "params": ind.params,
            }
            for ind in strategy.indicators
        ]
        df = compute_indicators(df, indicators)

        # Step 3: Trim warmup once
        logger.info("Walk-forward: Trimming warmup")
        df, warmup_bars = trim_warmup_period(df)

        if len(df) < window_count * 10:
            raise ValueError(
                f"Insufficient data after warmup: {len(df)} bars for {window_count} windows. "
                f"Need at least {window_count * 10} bars."
            )

        # Step 4: Generate windows
        logger.info(f"Walk-forward: Generating {window_count} windows from {len(df)} bars")
        windows = generate_windows(df, window_count)

        # Build condition groups for evaluation
        entry_groups_dict = {}
        exit_groups_dict = {}
        entry_group_legacy = None
        exit_group_legacy = None

        for cg in strategy.condition_groups:
            group_payload = {
                "logic": cg.logic,
                "conditions": [
                    {
                        "id": str(c.id),
                        "left_operand_type": c.left_operand_type,
                        "left_operand_value": c.left_operand_value,
                        "operator": c.operator,
                        "right_operand_type": c.right_operand_type,
                        "right_operand_value": c.right_operand_value,
                    }
                    for c in cg.conditions
                ],
            }

            if cg.group_type == "ENTRY":
                if cg.group_name:
                    entry_groups_dict[cg.group_name] = group_payload
                else:
                    entry_group_legacy = group_payload
            elif cg.group_type == "EXIT":
                if cg.group_name:
                    exit_groups_dict[cg.group_name] = group_payload
                else:
                    exit_group_legacy = group_payload

        # Step 5: Run backtest for each window
        window_results = []
        initial_capital = float(backtest_params["initial_capital"])

        for window in windows:
            logger.info(f"Walk-forward: Processing window {window.index}/{window_count}")

            # Slice dataframe for this window
            df_window = df.iloc[window.start_idx:window.end_idx + 1].copy()

            # Evaluate entry/exit signals on window
            if strategy.entry_expression:
                entry_signal = evaluate_expression(df_window, entry_groups_dict, strategy.entry_expression)
            else:
                entry_signal = evaluate_conditions(df_window, entry_group_legacy)

            if strategy.exit_expression:
                exit_signal = evaluate_expression(df_window, exit_groups_dict, strategy.exit_expression)
            else:
                exit_signal = evaluate_conditions(df_window, exit_group_legacy)

            # Run backtest
            trades, equity_curve = run_backtest(
                df=df_window,
                entry_signal=entry_signal,
                exit_signal=exit_signal,
                initial_capital=initial_capital,
                asset_class=backtest_params.get("asset_class", "STOCK"),
                position_size_type=backtest_params.get("position_size_type", "full_capital"),
                position_size_value=float(backtest_params.get("position_size_value", 100.0)),
                stop_loss_pct=float(backtest_params["stop_loss_pct"]) if backtest_params.get("stop_loss_pct") else None,
                take_profit_pct=float(backtest_params["take_profit_pct"]) if backtest_params.get("take_profit_pct") else None,
                commission_per_trade=float(backtest_params.get("commission_per_trade", 0.0)),
                commission_pct=float(backtest_params.get("commission_pct", 0.0)),
                slippage_pct=float(backtest_params.get("slippage_pct", 0.0)),
            )

            # Generate report for window
            report = generate_report(trades, equity_curve, initial_capital)

            # Build window result
            period_str = f"{window.start_date} to {window.end_date}"
            trade_count = report.get("total_trades", 0)

            window_results.append({
                "period": period_str,
                "start_date": str(window.start_date),
                "end_date": str(window.end_date),
                "metrics": {
                    "total_return_pct": round(report.get("total_return_pct", 0.0), 2),
                    "sharpe_ratio": round(report.get("sharpe_ratio", 0.0), 2),
                    "max_drawdown_pct": round(report.get("max_drawdown_pct", 0.0), 2),
                    "win_rate": round(report.get("win_rate", 0.0), 2),
                    "total_trades": trade_count,
                },
            })

        # Step 6: Calculate consistency and assessment
        logger.info("Walk-forward: Calculating consistency score")
        consistency_score, metric_cvs = calculate_wf_consistency_score(window_results)
        assessment = assess_walk_forward_results(window_results, consistency_score)

        # Step 7: Build report
        report = build_walk_forward_report(
            window_results,
            consistency_score,
            metric_cvs,
            assessment,
        )

        # Add metadata
        report["metadata"] = {
            "strategy_id": strategy_id,
            "ticker": backtest_params["ticker"],
            "full_period": f"{start_date} to {end_date}",
            "warmup_bars_trimmed": warmup_bars,
            "total_bars_analyzed": len(df),
        }

        await _update_analysis_status(
            analysis.id,
            "COMPLETE",
            session_maker,
            report=report,
        )
        return str(analysis.id)

    except Exception as e:
        logger.exception(f"Walk-forward validation failed: {e}")
        await _update_analysis_status(
            analysis.id,
            "FAILED",
            session_maker,
            error_message=str(e),
        )
        raise


async def _create_walk_forward_analysis_record(
    strategy_id: UUID,
    params: dict[str, Any],
    session_maker,
) -> RobustnessAnalysis:
    """Create initial analysis record for walk-forward validation."""
    analysis = RobustnessAnalysis(
        id=uuid4(),
        strategy_id=strategy_id,
        analysis_type="WALK_FORWARD",
        status="PENDING",
        params=params,
    )

    async with session_maker() as session:
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)

    return analysis


# =============================================================================
# Regime Detection
# =============================================================================

@celery_app.task(name="robustness.regime_detection")
def run_regime_detection(
    strategy_id: str,
    backtest_params: dict[str, Any],
    segmentation_strategy: str = "pelt_volatility",
    k: float = 0.015,
    penalty: float | None = None,
    min_segment_length: int = 20,
    vol_window: int = 20,
) -> str:
    """
    Run regime detection analysis.

    Detects market regimes and analyzes strategy performance per regime.

    Args:
        strategy_id: UUID of strategy to analyze
        backtest_params: Backtest configuration (ticker, dates, capital, etc.)
        segmentation_strategy: "l1_trend", "pelt_directional", or "pelt_volatility"
        k: L1 smoothing parameter (only for l1_trend, range 0.01-0.03)
        penalty: PELT penalty (only for PELT strategies, None = auto)
        min_segment_length: Min bars per segment (PELT only)
        vol_window: Window for rolling calculations (PELT only)

    Returns:
        analysis_id (UUID string)
    """
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
        return asyncio.run(
            _run_regime_detection_async(
                strategy_id,
                backtest_params,
                segmentation_strategy,
                k,
                penalty,
                min_segment_length,
                vol_window,
                session_maker,
            )
        )
    finally:
        asyncio.run(engine.dispose())


async def _run_regime_detection_async(
    strategy_id: str,
    backtest_params: dict[str, Any],
    segmentation_strategy: str,
    k: float,
    penalty: float | None,
    min_segment_length: int,
    vol_window: int,
    session_maker,
) -> str:
    """Async implementation of regime detection analysis."""
    from app.engine.data_layer import fetch_ohlcv_async
    from app.engine.indicator_layer import compute_indicators, trim_warmup_period
    from app.engine.condition_engine import evaluate_conditions, evaluate_expression
    from app.engine.state_machine import run_backtest
    from app.engine.report_generator import generate_report

    strategy_uuid = UUID(strategy_id)

    # Create analysis record
    analysis = await _create_regime_detection_analysis_record(
        strategy_uuid,
        {
            "segmentation_strategy": segmentation_strategy,
            "k": k,
            "penalty": penalty,
            "min_segment_length": min_segment_length,
            "vol_window": vol_window,
            "backtest_params": backtest_params,
        },
        session_maker,
    )

    try:
        await _update_analysis_status(analysis.id, "RUNNING", session_maker)

        # Load strategy
        strategy = await _get_strategy(strategy_uuid, session_maker)

        # Parse dates
        start_date = backtest_params["start_date"]
        end_date = backtest_params["end_date"]
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Step 1: Fetch full OHLCV data
        logger.info(f"Regime detection: Fetching OHLCV for {backtest_params['ticker']}")
        async with session_maker() as session:
            df = await fetch_ohlcv_async(
                backtest_params["ticker"],
                start_date,
                end_date,
                backtest_params.get("bar_resolution", "1d"),
                backtest_params.get("asset_class", "STOCK"),
                session=session,
                provider=backtest_params.get("provider"),
            )

        # Step 2: Detect regimes on raw OHLCV data (before indicators)
        logger.info(f"Regime detection: Detecting regimes with {segmentation_strategy} strategy")
        segments, regime_labels = detect_regimes(
            df,
            strategy=segmentation_strategy,
            k=k,
            penalty=penalty,
            min_segment_length=min_segment_length,
            vol_window=vol_window,
        )

        logger.info(f"Regime detection: Found {len(segments)} regime segments")

        # Step 3: Compute indicators for backtest
        logger.info("Regime detection: Computing indicators")
        indicators = [
            {
                "indicator_type": ind.indicator_type,
                "alias": ind.alias,
                "params": ind.params,
            }
            for ind in strategy.indicators
        ]
        df = compute_indicators(df, indicators)

        # Step 4: Trim warmup
        logger.info("Regime detection: Trimming warmup")
        df, warmup_bars = trim_warmup_period(df)

        # Also trim regime labels to match
        regime_labels = regime_labels.loc[df.index]

        if len(df) < 30:
            raise ValueError(
                f"Insufficient data after warmup: {len(df)} bars. Need at least 30."
            )

        # Build condition groups for evaluation
        entry_groups_dict = {}
        exit_groups_dict = {}
        entry_group_legacy = None
        exit_group_legacy = None

        for cg in strategy.condition_groups:
            group_payload = {
                "logic": cg.logic,
                "conditions": [
                    {
                        "id": str(c.id),
                        "left_operand_type": c.left_operand_type,
                        "left_operand_value": c.left_operand_value,
                        "operator": c.operator,
                        "right_operand_type": c.right_operand_type,
                        "right_operand_value": c.right_operand_value,
                    }
                    for c in cg.conditions
                ],
            }

            if cg.group_type == "ENTRY":
                if cg.group_name:
                    entry_groups_dict[cg.group_name] = group_payload
                else:
                    entry_group_legacy = group_payload
            elif cg.group_type == "EXIT":
                if cg.group_name:
                    exit_groups_dict[cg.group_name] = group_payload
                else:
                    exit_group_legacy = group_payload

        # Step 5: Run full backtest
        logger.info("Regime detection: Running backtest")
        initial_capital = float(backtest_params["initial_capital"])

        # Evaluate entry/exit signals
        if strategy.entry_expression:
            entry_signal = evaluate_expression(df, entry_groups_dict, strategy.entry_expression)
        else:
            entry_signal = evaluate_conditions(df, entry_group_legacy)

        if strategy.exit_expression:
            exit_signal = evaluate_expression(df, exit_groups_dict, strategy.exit_expression)
        else:
            exit_signal = evaluate_conditions(df, exit_group_legacy)

        trades, equity_curve = run_backtest(
            df=df,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            initial_capital=initial_capital,
            asset_class=backtest_params.get("asset_class", "STOCK"),
            position_size_type=backtest_params.get("position_size_type", "full_capital"),
            position_size_value=float(backtest_params.get("position_size_value", 100.0)),
            stop_loss_pct=float(backtest_params["stop_loss_pct"]) if backtest_params.get("stop_loss_pct") else None,
            take_profit_pct=float(backtest_params["take_profit_pct"]) if backtest_params.get("take_profit_pct") else None,
            commission_per_trade=float(backtest_params.get("commission_per_trade", 0.0)),
            commission_pct=float(backtest_params.get("commission_pct", 0.0)),
            slippage_pct=float(backtest_params.get("slippage_pct", 0.0)),
        )

        # Convert trades to dict format
        trades_dicts = [
            {
                "entry_date": t.entry_time,
                "exit_date": t.exit_time,
                "pnl_pct": t.pnl_pct,
            }
            for t in trades
        ]

        # Step 6: Analyze trades by regime
        logger.info("Regime detection: Analyzing trades by regime")
        regime_metrics = analyze_trades_by_regime(trades_dicts, regime_labels)

        # Step 7: Calculate distribution and dependency
        regime_distribution = calculate_regime_distribution(regime_labels)
        dependency_level, dependency_score = assess_regime_dependency(regime_metrics)

        # Step 8: Build report
        logger.info("Regime detection: Building report")
        report = build_regime_report(
            segments,
            regime_labels,
            regime_metrics,
            regime_distribution,
            dependency_level,
            dependency_score,
        )

        # Add metadata
        report["metadata"] = {
            "strategy_id": strategy_id,
            "ticker": backtest_params["ticker"],
            "period": f"{start_date} to {end_date}",
            "warmup_bars_trimmed": warmup_bars,
            "total_bars_analyzed": len(df),
            "params": {
                "penalty": penalty,
                "min_segment_length": min_segment_length,
                "vol_window": vol_window,
                "local_window": local_window,
                "n_clusters": n_clusters,
            },
        }

        # Add overall backtest metrics for reference
        overall_report = generate_report(trades, equity_curve, initial_capital)
        report["overall_backtest"] = {
            "total_return_pct": round(overall_report.get("total_return_pct", 0.0), 2),
            "sharpe_ratio": round(overall_report.get("sharpe_ratio", 0.0), 2),
            "max_drawdown_pct": round(overall_report.get("max_drawdown_pct", 0.0), 2),
            "win_rate": round(overall_report.get("win_rate", 0.0), 2),
            "total_trades": overall_report.get("total_trades", 0),
        }

        await _update_analysis_status(
            analysis.id,
            "COMPLETE",
            session_maker,
            report=report,
        )
        return str(analysis.id)

    except Exception as e:
        logger.exception(f"Regime detection failed: {e}")
        await _update_analysis_status(
            analysis.id,
            "FAILED",
            session_maker,
            error_message=str(e),
        )
        raise


async def _create_regime_detection_analysis_record(
    strategy_id: UUID,
    params: dict[str, Any],
    session_maker,
) -> RobustnessAnalysis:
    """Create initial analysis record for regime detection."""
    analysis = RobustnessAnalysis(
        id=uuid4(),
        strategy_id=strategy_id,
        analysis_type="REGIME_DETECTION",
        status="PENDING",
        params=params,
    )

    async with session_maker() as session:
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)

    return analysis



# =============================================================================
# Feature Conditioning
# =============================================================================

@celery_app.task(name="robustness.feature_conditioning")
def run_feature_conditioning(
    strategy_id: str,
    backtest_params: dict[str, Any],
    lookback_window: int = 50,
    min_trades_per_bin: int = 10,
) -> str:
    """
    Run feature-based conditional analysis.

    Extracts observable features at trade entry and finds which feature
    combinations predict trade success.

    Args:
        strategy_id: UUID of strategy to analyze
        backtest_params: Backtest configuration (ticker, dates, capital, etc.)
        lookback_window: Bars for rolling feature calculations
        min_trades_per_bin: Minimum trades to consider a condition reliable

    Returns:
        analysis_id (UUID string)
    """
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
        return asyncio.run(
            _run_feature_conditioning_async(
                strategy_id,
                backtest_params,
                lookback_window,
                min_trades_per_bin,
                session_maker,
            )
        )
    finally:
        asyncio.run(engine.dispose())


async def _run_feature_conditioning_async(
    strategy_id: str,
    backtest_params: dict[str, Any],
    lookback_window: int,
    min_trades_per_bin: int,
    session_maker,
) -> str:
    """Async implementation of feature conditioning analysis."""
    from app.engine.data_layer import fetch_ohlcv_async
    from app.engine.indicator_layer import compute_indicators, trim_warmup_period
    from app.engine.condition_engine import evaluate_conditions, evaluate_expression
    from app.engine.state_machine import run_backtest
    from app.engine.report_generator import generate_report

    strategy_uuid = UUID(strategy_id)

    # Create analysis record
    analysis = await _create_feature_conditioning_analysis_record(
        strategy_uuid,
        {
            "lookback_window": lookback_window,
            "min_trades_per_bin": min_trades_per_bin,
            "backtest_params": backtest_params,
        },
        session_maker,
    )

    try:
        await _update_analysis_status(analysis.id, "RUNNING", session_maker)

        # Load strategy
        strategy = await _get_strategy(strategy_uuid, session_maker)

        # Parse dates
        start_date = backtest_params["start_date"]
        end_date = backtest_params["end_date"]
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Step 1: Fetch OHLCV data
        logger.info(f"Feature conditioning: Fetching OHLCV for {backtest_params[\"ticker\"]}")
        async with session_maker() as session:
            df = await fetch_ohlcv_async(
                backtest_params["ticker"],
                start_date,
                end_date,
                backtest_params.get("bar_resolution", "1d"),
                backtest_params.get("asset_class", "STOCK"),
                session=session,
            )

        if df.empty:
            raise ValueError("No OHLCV data fetched")

        # Step 2: Compute indicators
        logger.info("Feature conditioning: Computing indicators")
        indicator_data = {
            ind.alias: {
                "indicator_type": ind.indicator_type,
                "params": ind.params,
            }
            for ind in strategy.indicators
        }
        df = compute_indicators(df, indicator_data)
        df = trim_warmup_period(df)

        # Step 3: Build condition groups
        entry_groups_dict = {}
        exit_groups_dict = {}
        entry_group_legacy = None
        exit_group_legacy = None

        for cg in strategy.condition_groups:
            group_payload = {
                "logic": cg.logic,
                "conditions": [
                    {
                        "id": str(c.id),
                        "left_operand_type": c.left_operand_type,
                        "left_operand_value": c.left_operand_value,
                        "operator": c.operator,
                        "right_operand_type": c.right_operand_type,
                        "right_operand_value": c.right_operand_value,
                    }
                    for c in cg.conditions
                ],
            }

            if cg.group_type == "ENTRY":
                if cg.group_name:
                    entry_groups_dict[cg.group_name] = group_payload
                else:
                    entry_group_legacy = group_payload
            elif cg.group_type == "EXIT":
                if cg.group_name:
                    exit_groups_dict[cg.group_name] = group_payload
                else:
                    exit_group_legacy = group_payload

        # Step 4: Run full backtest
        logger.info("Feature conditioning: Running backtest")
        initial_capital = float(backtest_params["initial_capital"])

        # Evaluate entry/exit signals
        if strategy.entry_expression:
            entry_signal = evaluate_expression(df, entry_groups_dict, strategy.entry_expression)
        else:
            entry_signal = evaluate_conditions(df, entry_group_legacy)

        if strategy.exit_expression:
            exit_signal = evaluate_expression(df, exit_groups_dict, strategy.exit_expression)
        else:
            exit_signal = evaluate_conditions(df, exit_group_legacy)

        trades, equity_curve = run_backtest(
            df=df,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            initial_capital=initial_capital,
            asset_class=backtest_params.get("asset_class", "STOCK"),
            position_size_type=backtest_params.get("position_size_type", "full_capital"),
            position_size_value=float(backtest_params.get("position_size_value", 100.0)),
            stop_loss_pct=backtest_params.get("stop_loss_pct"),
            take_profit_pct=backtest_params.get("take_profit_pct"),
            commission_per_trade=float(backtest_params.get("commission_per_trade", 0.0)),
            commission_pct=float(backtest_params.get("commission_pct", 0.0)),
            slippage_pct=float(backtest_params.get("slippage_pct", 0.0)),
        )

        logger.info(f"Feature conditioning: Got {len(trades)} trades")

        if len(trades) < min_trades_per_bin * 2:
            raise ValueError(f"Not enough trades ({len(trades)}) for feature analysis (need at least {min_trades_per_bin * 2})")

        # Step 5: Extract features at entry time for each trade
        logger.info("Feature conditioning: Extracting features at entry")
        trades_with_features = extract_trade_features(trades, df, lookback_window)

        logger.info(f"Feature conditioning: Extracted features for {len(trades_with_features)} trades")

        # Step 6: Analyze feature conditions
        logger.info("Feature conditioning: Analyzing feature conditions")
        condition_analysis = analyze_feature_conditions(trades_with_features, min_trades_per_bin)

        # Step 7: Get overall metrics for comparison
        overall_report = generate_report(trades, equity_curve, initial_capital)
        overall_metrics = {
            "total_return_pct": round(overall_report.get("total_return_pct", 0.0), 2),
            "sharpe_ratio": round(overall_report.get("sharpe_ratio", 0.0), 2),
            "max_drawdown_pct": round(overall_report.get("max_drawdown_pct", 0.0), 2),
            "win_rate": round(overall_report.get("win_rate", 0.0), 2),
            "total_trades": overall_report.get("total_trades", 0),
        }

        # Step 8: Build report
        report = build_feature_conditioning_report(
            trades_with_features,
            condition_analysis,
            overall_metrics,
        )

        await _update_analysis_status(
            analysis.id,
            "COMPLETE",
            session_maker,
            report=report,
        )
        return str(analysis.id)

    except Exception as e:
        logger.exception(f"Feature conditioning failed: {e}")
        await _update_analysis_status(
            analysis.id,
            "FAILED",
            session_maker,
            error_message=str(e),
        )
        raise


async def _create_feature_conditioning_analysis_record(
    strategy_id: UUID,
    params: dict[str, Any],
    session_maker,
) -> RobustnessAnalysis:
    """Create initial analysis record for feature conditioning."""
    analysis = RobustnessAnalysis(
        id=uuid4(),
        strategy_id=strategy_id,
        analysis_type="FEATURE_CONDITIONING",
        status="PENDING",
        params=params,
    )

    async with session_maker() as session:
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)

    return analysis

