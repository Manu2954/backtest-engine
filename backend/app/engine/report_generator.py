from __future__ import annotations

import math
from typing import Any

import pandas as pd


def calculate_buy_and_hold_equity(
    df: pd.DataFrame,
    initial_capital: float,
    asset_class: str = "STOCK",
) -> pd.Series:
    """
    Calculate buy-and-hold equity curve using percentage returns.

    This represents tracking the asset's performance without share constraints.
    Works for all assets regardless of price (handles high-priced indices like
    ^NSEI, ^DJI, BRK.A, etc.).

    Args:
        df: OHLCV DataFrame
        initial_capital: Starting capital
        asset_class: "STOCK" or "CRYPTO" (not used, kept for API compatibility)

    Returns:
        Equity curve Series aligned with df.index

    Algorithm:
        1. Entry at first bar's open price
        2. Calculate percentage change from entry to each bar's close
        3. Apply percentage returns to initial capital
        4. Result: equity_curve[i] = initial_capital * (close[i] / open[0])

    Example:
        - Initial capital: $10,000
        - Entry price (open[0]): 100
        - Close prices: [101, 102, 110, 95]
        - Returns: [1.01, 1.02, 1.10, 0.95]
        - Equity: [$10,100, $10,200, $11,000, $9,500]
    """
    if df.empty or "open" not in df.columns or "close" not in df.columns:
        return pd.Series([], dtype=float, name="benchmark_equity")

    # Entry at first bar's open price
    entry_price = float(df.iloc[0]["open"])

    if entry_price <= 0:
        # Invalid entry price - return flat equity at initial capital
        return pd.Series([initial_capital] * len(df), index=df.index, name="benchmark_equity")

    # Calculate percentage returns from entry price to each bar's close
    # pct_return = close / entry_price (e.g., close=110, entry=100 -> 1.10 = +10%)
    pct_returns = df["close"] / entry_price

    # Apply percentage returns to initial capital
    equity_curve = initial_capital * pct_returns

    return pd.Series(equity_curve, index=df.index, name="benchmark_equity")


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _to_series(equity_curve: pd.Series) -> pd.Series:
    if equity_curve is None:
        return pd.Series(dtype=float)
    if not isinstance(equity_curve, pd.Series):
        return pd.Series(equity_curve)
    return equity_curve


def _ensure_datetime_index(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    if not isinstance(series.index, pd.DatetimeIndex):
        try:
            series.index = pd.to_datetime(series.index)
        except Exception:
            pass
    return series


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    return float(drawdown.min()) * 100


def _direction_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate summary metrics for a subset of trades (one direction)."""
    total = len(trades)
    if total == 0:
        return {"total_trades": 0, "win_rate": 0.0, "total_pnl": 0.0, "avg_pnl": 0.0}

    pnl_values = [float(t.get("pnl", 0.0)) for t in trades]
    wins = [p for p in pnl_values if p > 0]
    return {
        "total_trades": total,
        "win_rate": (len(wins) / total) * 100,
        "total_pnl": sum(pnl_values),
        "avg_pnl": sum(pnl_values) / total,
    }


def _longest_drawdown_days(equity: pd.Series) -> int:
    if equity.empty:
        return 0

    equity = _ensure_datetime_index(equity.copy())
    running_max = equity.cummax()
    in_drawdown = equity < running_max

    if not in_drawdown.any():
        return 0

    longest = 0
    start = None
    for idx, is_dd in in_drawdown.items():
        if is_dd and start is None:
            start = idx
        if not is_dd and start is not None:
            duration = idx - start
            days = int(duration.days) if hasattr(duration, "days") else int(duration)
            longest = max(longest, days)
            start = None

    if start is not None:
        end = equity.index[-1]
        duration = end - start
        days = int(duration.days) if hasattr(duration, "days") else int(duration)
        longest = max(longest, days)

    return longest


def _calculate_benchmark_stats(
    strategy_equity: pd.Series,
    benchmark_equity: pd.Series,
    initial_capital: float,
    strategy_daily_returns: pd.Series,
) -> dict[str, Any]:
    """
    Calculate benchmark comparison statistics.

    Args:
        strategy_equity: Strategy equity curve
        benchmark_equity: Buy-and-hold equity curve (FULL period, including warmup)
        initial_capital: Starting capital
        strategy_daily_returns: Strategy daily returns (already calculated)

    Returns:
        Dictionary with benchmark comparison stats

    Note:
        Benchmark represents buy-and-hold for the FULL requested period (original start to end),
        while strategy may only trade during a subset (after warmup trim).
        We calculate benchmark stats from the full period for accurate representation.
    """
    benchmark_equity = _to_series(benchmark_equity).dropna()
    benchmark_equity = _ensure_datetime_index(benchmark_equity)

    if benchmark_equity.empty:
        return {}

    # Benchmark return from FULL period (original start to end)
    # This is what users expect: "What if I bought and held from day 1?"
    benchmark_initial = float(benchmark_equity.iloc[0])
    benchmark_final = float(benchmark_equity.iloc[-1])
    benchmark_return_pct = _safe_div(benchmark_final - benchmark_initial, benchmark_initial) * 100

    # Strategy return from when it started trading (after warmup)
    strategy_final = float(strategy_equity.iloc[-1])
    strategy_return_pct = _safe_div(strategy_final - initial_capital, initial_capital) * 100

    # Alpha: Strategy return - Benchmark return
    # Note: This compares strategy's partial period against benchmark's full period
    # This is correct because it shows if the strategy's active trading beat simple buy-and-hold
    alpha = strategy_return_pct - benchmark_return_pct

    # Benchmark Sharpe ratio (from full period)
    benchmark_daily_returns = benchmark_equity.pct_change().dropna()
    if not benchmark_daily_returns.empty and benchmark_daily_returns.std() != 0:
        benchmark_sharpe = (benchmark_daily_returns.mean() / benchmark_daily_returns.std()) * (252 ** 0.5)
    else:
        benchmark_sharpe = 0.0

    # Beta: Correlation between strategy and benchmark returns
    # Align the two series to overlapping period only
    aligned_strategy, aligned_benchmark = strategy_daily_returns.align(benchmark_daily_returns, join="inner")

    if len(aligned_strategy) > 1 and aligned_benchmark.std() != 0:
        covariance = aligned_strategy.cov(aligned_benchmark)
        benchmark_variance = aligned_benchmark.var()
        beta = covariance / benchmark_variance if benchmark_variance != 0 else 0.0
    else:
        beta = 0.0

    # Benchmark max drawdown (from full period)
    benchmark_max_dd = _max_drawdown(benchmark_equity)

    return {
        "benchmark_return_pct": benchmark_return_pct,
        "benchmark_final_capital": benchmark_final,
        "benchmark_sharpe_ratio": benchmark_sharpe,
        "benchmark_max_drawdown_pct": benchmark_max_dd,
        "alpha": alpha,
        "beta": beta,
    }


def generate_report(
    trade_log: list[dict[str, Any]],
    equity_curve: pd.Series,
    initial_capital: float,
    benchmark_equity: pd.Series | None = None,
    risk_free_rate: float = 0.0,
) -> dict[str, Any]:
    equity = _to_series(equity_curve).dropna()
    equity = _ensure_datetime_index(equity)

    final_capital = float(equity.iloc[-1]) if not equity.empty else float(initial_capital)
    total_return_pct = _safe_div(final_capital - initial_capital, initial_capital) * 100

    if equity.empty or len(equity.index) < 2:
        years = 0.0
    else:
        delta = equity.index[-1] - equity.index[0]
        years = delta.days / 365.25 if hasattr(delta, "days") else 0.0

    if years > 0 and initial_capital > 0:
        cagr = ((final_capital / initial_capital) ** (1 / years) - 1) * 100
    else:
        cagr = 0.0

    total_trades = len(trade_log)
    # print(len(trade_log))
    pnl_values = [float(t.get("pnl", 0.0)) for t in trade_log]
    wins = [p for p in pnl_values if p > 0]
    losses = [p for p in pnl_values if p < 0]

    win_rate = _safe_div(len(wins), total_trades) * 100 if total_trades else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0

    # Calculate avg_win_loss ratio
    if avg_loss != 0:
        avg_win_loss = _safe_div(avg_win, abs(avg_loss))
    elif avg_win > 0:
        # No losses but have wins - perfect strategy (very large ratio)
        # Use 999999 instead of infinity (PostgreSQL JSONB doesn't support inf)
        avg_win_loss = 999999.0
    else:
        # No wins and no losses (no trades)
        avg_win_loss = 0.0

    largest_win = max(wins) if wins else 0.0
    largest_loss = min(losses) if losses else 0.0

    daily_returns = equity.pct_change().dropna()
    if not daily_returns.empty and daily_returns.std() != 0:
        # Convert annual risk-free rate to daily rate
        daily_rf = (1 + risk_free_rate) ** (1 / 252) - 1
        excess_returns = daily_returns - daily_rf
        sharpe = (excess_returns.mean() / daily_returns.std()) * (252 ** 0.5)
    else:
        sharpe = 0.0

    # Sortino ratio: only penalizes downside volatility
    # Formula: (Mean Return - Risk Free Rate) / Downside Deviation * sqrt(252)
    if not daily_returns.empty:
        daily_rf = (1 + risk_free_rate) ** (1 / 252) - 1
        excess_returns_sortino = daily_returns - daily_rf
        # Downside deviation: std of returns below target (risk-free rate)
        downside_returns = excess_returns_sortino[excess_returns_sortino < 0]
        if len(downside_returns) > 0:
            downside_std = downside_returns.std()
            if downside_std != 0:
                sortino = (excess_returns_sortino.mean() / downside_std) * (252 ** 0.5)
            else:
                # No volatility in downside returns (all same value)
                sortino = None
        else:
            # No negative returns - strategy never had a down day
            sortino = None
    else:
        sortino = None

    gross_profit = sum(p for p in pnl_values if p > 0)
    gross_loss = abs(sum(p for p in pnl_values if p < 0))
    profit_factor = _safe_div(gross_profit, gross_loss) if gross_loss != 0 else 0.0

    durations = [int(t.get("trade_duration_days", 0)) for t in trade_log]
    avg_trade_duration = sum(durations) / len(durations) if durations else 0.0

    report = {
        "total_return_pct": total_return_pct,
        "cagr": cagr,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "avg_win_loss": avg_win_loss,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "max_drawdown_pct": _max_drawdown(equity),
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "profit_factor": profit_factor,
        "avg_trade_duration_days": avg_trade_duration,
        "longest_drawdown_days": _longest_drawdown_days(equity),
        "final_capital": final_capital,
    }

    # Per-direction breakdown (only when short trades exist)
    if any(t.get("direction") == "SHORT" for t in trade_log):
        long_trades = [t for t in trade_log if t.get("direction", "LONG") == "LONG"]
        short_trades = [t for t in trade_log if t.get("direction") == "SHORT"]
        report["long_trades_summary"] = _direction_metrics(long_trades)
        report["short_trades_summary"] = _direction_metrics(short_trades)

    # Add benchmark comparison if provided
    if benchmark_equity is not None and not benchmark_equity.empty:
        benchmark_stats = _calculate_benchmark_stats(
            equity, benchmark_equity, initial_capital, daily_returns
        )
        report.update(benchmark_stats)

    # Sanitize report: Replace any NaN or Infinity values with safe defaults
    # PostgreSQL JSONB doesn't support NaN or Infinity
    for key, value in report.items():
        if isinstance(value, float):
            if math.isnan(value):
                report[key] = 0.0
            elif math.isinf(value):
                # Use large finite number instead of infinity
                report[key] = 999999.0 if value > 0 else -999999.0

    return report


def generate_attribution_report(
    trade_log: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Generate trade attribution report from trade-level attribution data.

    Aggregates individual trade attribution into strategy-level insights:
    - Total alpha across all trades
    - Signal strength distribution (strong/medium/weak performance)
    - Win rate by signal strength
    - Condition frequency analysis
    - Average alpha by signal strength bin

    Args:
        trade_log: List of trade dictionaries with attribution fields

    Returns:
        Dictionary with attribution insights, or None if no attribution data

    Attribution Fields in Trade Log:
        - entry_conditions_met: List of condition IDs that triggered entry
        - entry_signal_strength: Float 0.0-1.0 (confluence score)
        - market_return_during_trade: Float percent (buy-and-hold return)
        - alpha: Float percent (pnl_pct - market_return)
        - indicator_snapshot_entry: Dict of indicator values at entry

    Report Structure:
        {
            "total_alpha": float,  # Sum of all trade alphas
            "alpha_percentage": float,  # Alpha as % of total return
            "signal_strength": {
                "strong": {"count": int, "win_rate": float, "avg_alpha": float},
                "medium": {"count": int, "win_rate": float, "avg_alpha": float},
                "weak": {"count": int, "win_rate": float, "avg_alpha": float}
            },
            "condition_frequency": {
                "condition_id": int,  # How many trades triggered each condition
            }
        }
    """
    # Check if any trades have attribution data
    trades_with_attribution = [
        t for t in trade_log
        if t.get("entry_signal_strength") is not None
    ]

    if not trades_with_attribution:
        return None

    # Calculate total alpha
    total_alpha = sum(
        float(t.get("alpha", 0.0))
        for t in trades_with_attribution
        if t.get("alpha") is not None
    )

    # Calculate alpha percentage (alpha / total return)
    total_pnl_pct = sum(
        float(t.get("pnl_pct", 0.0))
        for t in trades_with_attribution
    )
    alpha_percentage = _safe_div(total_alpha, total_pnl_pct) * 100 if total_pnl_pct != 0 else 0.0

    # Signal strength bins
    signal_strength_bins = {
        "strong": {"trades": [], "threshold": 0.7},
        "medium": {"trades": [], "threshold": 0.3},
        "weak": {"trades": [], "threshold": 0.0},
    }

    # Classify trades by signal strength
    for trade in trades_with_attribution:
        strength = float(trade.get("entry_signal_strength", 0.0))
        if strength >= 0.7:
            signal_strength_bins["strong"]["trades"].append(trade)
        elif strength >= 0.3:
            signal_strength_bins["medium"]["trades"].append(trade)
        else:
            signal_strength_bins["weak"]["trades"].append(trade)

    # Calculate stats per bin
    signal_strength_stats = {}
    for bin_name, bin_data in signal_strength_bins.items():
        trades = bin_data["trades"]
        if not trades:
            signal_strength_stats[bin_name] = {
                "count": 0,
                "win_rate": 0.0,
                "avg_alpha": 0.0,
            }
            continue

        wins = [t for t in trades if float(t.get("pnl", 0.0)) > 0]
        win_rate = _safe_div(len(wins), len(trades)) * 100

        alphas = [float(t.get("alpha", 0.0)) for t in trades if t.get("alpha") is not None]
        avg_alpha = sum(alphas) / len(alphas) if alphas else 0.0

        signal_strength_stats[bin_name] = {
            "count": len(trades),
            "win_rate": win_rate,
            "avg_alpha": avg_alpha,
        }

    # Condition frequency analysis
    condition_frequency = {}
    for trade in trades_with_attribution:
        entry_conditions = trade.get("entry_conditions_met", [])
        if entry_conditions:
            for condition_id in entry_conditions:
                condition_frequency[str(condition_id)] = condition_frequency.get(str(condition_id), 0) + 1

    report = {
        "total_alpha": total_alpha,
        "alpha_percentage": alpha_percentage,
        "signal_strength": signal_strength_stats,
        "condition_frequency": condition_frequency,
    }

    # Sanitize report (NaN/Inf handling)
    for key, value in report.items():
        if isinstance(value, float):
            if math.isnan(value):
                report[key] = 0.0
            elif math.isinf(value):
                report[key] = 999999.0 if value > 0 else -999999.0

    return report


def generate_binning_report(
    trade_log: list[dict[str, Any]],
    indicators: list[dict[str, Any]],
    conditions: list[dict[str, Any]] | None = None
) -> dict[str, Any] | None:
    """
    Generate empirical binning analysis report.

    This is a diagnostic tool that analyzes which indicator value ranges
    correlate with profitable trades. Unlike Phase 1B (arbitrary thresholds),
    this uses data-driven quintile binning.

    Args:
        trade_log: List of trade dicts with indicator_snapshot_entry
        indicators: List of indicator dicts with 'alias' key
        conditions: Optional list of condition dicts (for crossover detection)

    Returns:
        Binning analysis dict or None if insufficient data (< 50 trades)

    Example return:
        {
            "rsi_14": {
                "bins": [
                    {"range": [0, 20], "count": 30, "avg_pnl": 250.0, "win_rate": 0.67},
                    ...
                ],
                "bin_edges": [0, 20, 40, 60, 80, 100],
                "correlation": 0.72,
                "p_value": 0.001,
                "sample_size": 100
            },
            "summary": {
                "total_indicators": 5,
                "analyzed_indicators": 2,
                "significant_indicators": 1,
                "skipped_indicators": ["ema_cross"],
                "insufficient_data": False
            }
        }
    """
    if len(trade_log) < 50:
        return None

    from app.engine.attribution.analysis.binning_analyzer import analyze_indicator_bins

    # Convert trade_log dicts to mock objects that binning_analyzer expects
    # binning_analyzer needs objects with .pnl and .indicator_snapshot_entry attributes
    class TradeMock:
        def __init__(self, trade_dict):
            self.pnl = float(trade_dict.get("pnl", 0.0))
            self.indicator_snapshot_entry = trade_dict.get("indicator_snapshot_entry")

    trades = [TradeMock(t) for t in trade_log]
    indicator_aliases = [ind["alias"] for ind in indicators]

    return analyze_indicator_bins(trades, indicator_aliases, conditions=conditions)

