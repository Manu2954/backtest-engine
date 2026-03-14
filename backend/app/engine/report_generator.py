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
    Calculate buy-and-hold equity curve.

    Buys at the first bar's open price and holds until the end.

    Args:
        df: OHLCV DataFrame
        initial_capital: Starting capital
        asset_class: "STOCK" or "CRYPTO" (affects fractional shares)

    Returns:
        Equity curve Series aligned with df.index
    """
    if df.empty or "open" not in df.columns or "close" not in df.columns:
        return pd.Series([], dtype=float, name="benchmark_equity")

    # Buy at first bar's open
    entry_price = float(df.iloc[0]["open"])

    # Calculate shares
    allow_fractional = asset_class.upper() != "STOCK"
    raw_shares = initial_capital / entry_price if entry_price > 0 else 0.0
    shares = raw_shares if allow_fractional else float(int(raw_shares))

    if shares == 0:
        # Not enough capital to buy even 1 share
        return pd.Series([initial_capital] * len(df), index=df.index, name="benchmark_equity")

    # Mark-to-market at each bar's close
    equity_curve = df["close"] * shares

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
        benchmark_equity: Buy-and-hold equity curve
        initial_capital: Starting capital
        strategy_daily_returns: Strategy daily returns (already calculated)

    Returns:
        Dictionary with benchmark comparison stats
    """
    benchmark_equity = _to_series(benchmark_equity).dropna()
    benchmark_equity = _ensure_datetime_index(benchmark_equity)

    if benchmark_equity.empty:
        return {}

    # Benchmark final capital and return
    benchmark_final = float(benchmark_equity.iloc[-1])
    benchmark_return_pct = _safe_div(benchmark_final - initial_capital, initial_capital) * 100

    # Alpha: Strategy return - Benchmark return
    strategy_final = float(strategy_equity.iloc[-1])
    strategy_return_pct = _safe_div(strategy_final - initial_capital, initial_capital) * 100
    alpha = strategy_return_pct - benchmark_return_pct

    # Benchmark Sharpe ratio
    benchmark_daily_returns = benchmark_equity.pct_change().dropna()
    if not benchmark_daily_returns.empty and benchmark_daily_returns.std() != 0:
        benchmark_sharpe = (benchmark_daily_returns.mean() / benchmark_daily_returns.std()) * (252 ** 0.5)
    else:
        benchmark_sharpe = 0.0

    # Beta: Correlation between strategy and benchmark returns
    # Align the two series
    aligned_strategy, aligned_benchmark = strategy_daily_returns.align(benchmark_daily_returns, join="inner")

    if len(aligned_strategy) > 1 and aligned_benchmark.std() != 0:
        covariance = aligned_strategy.cov(aligned_benchmark)
        benchmark_variance = aligned_benchmark.var()
        beta = covariance / benchmark_variance if benchmark_variance != 0 else 0.0
    else:
        beta = 0.0

    # Benchmark max drawdown
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
        cagr = (final_capital / initial_capital) ** (1 / years) - 1
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
        sharpe = (daily_returns.mean() / daily_returns.std()) * (252 ** 0.5)
    else:
        sharpe = 0.0

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
        "profit_factor": profit_factor,
        "avg_trade_duration_days": avg_trade_duration,
        "longest_drawdown_days": _longest_drawdown_days(equity),
        "final_capital": final_capital,
    }

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
