from __future__ import annotations

from typing import Any

import pandas as pd


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


def generate_report(
    trade_log: list[dict[str, Any]],
    equity_curve: pd.Series,
    initial_capital: float,
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
    avg_win_loss = _safe_div(avg_win, abs(avg_loss)) if avg_loss != 0 else 0.0

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
        "avg_win_loss": avg_win_loss,
        "max_drawdown_pct": _max_drawdown(equity),
        "sharpe_ratio": sharpe,
        "profit_factor": profit_factor,
        "avg_trade_duration": avg_trade_duration,
        "longest_drawdown_days": _longest_drawdown_days(equity),
        "final_capital": final_capital,
    }

    return report
