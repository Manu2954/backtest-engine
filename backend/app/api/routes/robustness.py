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
    RegimeDetectionCreate,
    FeatureConditioningCreate,
)
from app.core.database import get_session
from app.models.robustness import RobustnessAnalysis
from app.tasks.robustness_task import (
    run_parameter_sensitivity_analysis,
    run_walk_forward_validation,
    run_regime_detection,
    run_feature_conditioning,
)

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


@router.post("/regime-detection", response_model=RobustnessAnalysisOut, summary="Run regime detection analysis")
async def create_regime_detection(
    request: RegimeDetectionCreate,
):
    """
    Run regime detection analysis on a strategy.

    Detects market regimes (BULL, BEAR, CHOPPY, RANGING) using PELT changepoint
    detection with pluggable segmentation strategies.

    **Segmentation Strategies**:
    - `volatility`: Signal = [log_returns, rolling_vol] - detects volatility shifts
    - `directional`: Signal = rolling_mean(log_returns) - detects trend reversals

    **Process**:
    1. Detect changepoints using PELT with selected strategy
    2. Extract features per segment (OLS slope, R², mean return, std)
    3. Classify segments using SNR-based labeling
    4. Run full backtest and analyze trades by regime
    5. Assess regime dependency using CV of returns

    **Regime types**:
    - BULL: Positive trend (high SNR, positive slope)
    - BEAR: Negative trend (high SNR, negative slope)
    - CHOPPY: No trend, high volatility
    - RANGING: No trend, low volatility

    **Dependency levels**:
    - INDEPENDENT: CV < 0.3 - Strategy works across all regimes
    - MODERATE: CV 0.3-0.6 - Some regime sensitivity
    - DEPENDENT: CV > 0.6 - Highly regime-dependent

    **Report fields** (when COMPLETE):
    - segments: List of detected regime segments with dates and features
    - regimes: Per-regime metrics (trades, return, win rate, Sharpe)
    - summary: Distribution, dependency score, best/worst regimes
    - assessment: Level, risk_flags, recommendation
    - overall_backtest: Full backtest metrics for reference
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
    run_regime_detection.apply_async(
        args=[
            str(request.strategy_id),
            backtest_params,
            request.segmentation_strategy,
            request.k,
            request.penalty,
            request.min_segment_length,
            request.vol_window,
        ]
    )

    # Poll database briefly for analysis record
    import asyncio
    for _ in range(30):
        async for session in get_session():
            stmt = select(RobustnessAnalysis).where(
                RobustnessAnalysis.strategy_id == request.strategy_id,
                RobustnessAnalysis.analysis_type == "REGIME_DETECTION",
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



@router.post("/feature-conditioning", response_model=RobustnessAnalysisOut, summary="Run feature-based conditional analysis")
async def create_feature_conditioning(
    request: FeatureConditioningCreate,
):
    """
    Run feature-based conditional analysis on a strategy.

    Extracts observable features (volatility, trend strength, etc.) at trade entry time
    and finds which feature ranges predict trade success.

    **Key difference from regime detection:**
    - Regime detection: Labels bars as BULL/BEAR/CHOPPY (descriptive, backward-looking)
    - Feature conditioning: Reports raw measurable features (predictive, real-time available)

    **Process**:
    1. Run full backtest to get all trades
    2. Extract features at each trade entry (vol, trend_strength, r_squared, price_vs_sma50, etc.)
    3. Bin features into quartiles
    4. Find feature ranges with highest/lowest win rates
    5. Report actionable conditions

    **Features extracted** (all computable in real-time):
    - volatility: Rolling std of returns
    - trend_strength: R² from OLS regression (0-1, higher = stronger trend)
    - trend_slope: OLS slope (positive = uptrend, negative = downtrend)
    - price_vs_sma50: (price - SMA50) / SMA50 (relative position)
    - returns_autocorr: Lag-1 autocorrelation (mean reversion signal)
    - rsi_level: RSI at entry (if strategy uses RSI)
    - atr_pct: ATR as % of price (if strategy uses ATR)

    **Report fields** (when COMPLETE):
    - winning_conditions: Feature ranges with high win rates (e.g., "vol ∈ [0.015, 0.025], win_rate=68%")
    - losing_conditions: Feature ranges with low win rates to avoid
    - feature_importance: Which features matter most (0-1 normalized)
    - feature_statistics: Mean/std for each feature
    - assessment: Actionable recommendation and risk flags

    **Example output**:
    "Strategy performs best when volatility ∈ [0.015, 0.025] (win rate: 72%).
    Avoid trading when trend_strength < 0.3 (win rate: 35%)."
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
    run_feature_conditioning.apply_async(
        args=[
            str(request.strategy_id),
            backtest_params,
            request.lookback_window,
            request.min_trades_per_bin,
        ]
    )

    # Poll database briefly for analysis record
    import asyncio
    for _ in range(30):
        async for session in get_session():
            stmt = select(RobustnessAnalysis).where(
                RobustnessAnalysis.strategy_id == request.strategy_id,
                RobustnessAnalysis.analysis_type == "FEATURE_CONDITIONING",
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

