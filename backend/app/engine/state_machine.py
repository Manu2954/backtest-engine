from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class TradeRecord:
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp
    exit_price: float
    shares: float
    pnl: float
    pnl_pct: float
    trade_duration_days: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_date": self.entry_date,
            "entry_price": self.entry_price,
            "exit_date": self.exit_date,
            "exit_price": self.exit_price,
            "shares": self.shares,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "trade_duration_days": self.trade_duration_days,
        }


def _ensure_series(series: pd.Series, index: pd.Index) -> pd.Series:
    if series is None or len(series) == 0:
        return pd.Series([False] * len(index), index=index, dtype=bool)
    if not series.index.equals(index):
        series = series.reindex(index, fill_value=False)
    return series.astype(bool)


def run_backtest(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    exit_signal: pd.Series,
    initial_capital: float,
    asset_class: str = "STOCK",
    shares: float = 0.0,
    periodic_contribution: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], pd.Series]:
    if df.empty:
        return [], pd.Series([], dtype=float, name="equity")

    for col in ("open", "close"):
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    entry_signal = _ensure_series(entry_signal, df.index)
    exit_signal = _ensure_series(exit_signal, df.index)

    allow_fractional = asset_class.upper() != "STOCK"

    # Backward-compatible handling if periodic_contribution was passed positionally.
    if isinstance(shares, dict) and periodic_contribution is None:
        periodic_contribution = shares
        shares = 0.0

    cash = float(initial_capital)

    trade_log: list[TradeRecord] = []
    equity_curve = pd.Series(index=df.index, dtype=float, name="equity")

    pending_entry = False
    pending_exit = False
    entry_date: pd.Timestamp | None = None
    entry_price: float | None = None

    contribution_amount = 0.0
    contribution_frequency = ""
    interval_days = 0
    include_start = False
    if periodic_contribution:
        contribution_amount = float(periodic_contribution.get("amount", 0.0))
        contribution_frequency = str(
            periodic_contribution.get("frequency", "monthly")
        ).lower()
        interval_days = int(periodic_contribution.get("interval_days", 0))
        include_start = bool(periodic_contribution.get("include_start", False))

        allowed = {"daily", "weekly", "monthly", "interval_days"}
        if contribution_frequency not in allowed:
            raise ValueError(f"Unsupported contribution frequency: {contribution_frequency}")
        if contribution_amount < 0:
            raise ValueError("Contribution amount must be non-negative")
        if contribution_frequency == "interval_days" and interval_days <= 0:
            raise ValueError("interval_days must be > 0 for interval_days frequency")

    def period_key(ts: pd.Timestamp) -> tuple[Any, ...]:
        if contribution_frequency == "daily":
            return (ts.year, ts.month, ts.day)
        if contribution_frequency == "weekly":
            iso = ts.isocalendar()
            return (int(iso.year), int(iso.week))
        if contribution_frequency == "monthly":
            return (ts.year, ts.month)
        if contribution_frequency == "interval_days":
            start_ts = df.index[0]
            if not isinstance(start_ts, pd.Timestamp):
                start_ts = pd.to_datetime(start_ts)
            days = (ts.normalize() - start_ts.normalize()).days
            bucket = days // interval_days
            return (bucket,)
        return (0,)

    last_period_key: tuple[Any, ...] | None = None

    for i, (ts, row) in enumerate(df.iterrows()):
        # Apply periodic contributions at the start of a new period (before fills)
        if contribution_amount > 0:
            key = period_key(ts)
            # print(i, ts, key, last_period_key, cash, shares, entry_signal.iloc[i])
            if last_period_key is None:
                last_period_key = key
                if include_start:   
                    cash += contribution_amount
            elif key != last_period_key:
                cash += contribution_amount
                last_period_key = key

        open_price = float(row["open"])
        close_price = float(row["close"])

        # Fill pending entry at current bar open
        if pending_entry and shares == 0.0:
            raw_shares = cash / open_price if open_price > 0 else 0.0
            shares = raw_shares if allow_fractional else float(int(raw_shares))
            cash = cash - (shares * open_price)
            if abs(cash) < 1e-8:
                cash = 0.0
            entry_price = open_price
            entry_date = ts
            pending_entry = False

        # Fill pending exit at current bar open
        if pending_exit and shares > 0.0:
            exit_price = open_price
            exit_date = ts
            pnl = (exit_price - (entry_price or 0.0)) * shares
            pnl_pct = pnl / initial_capital if initial_capital else 0.0
            trade_duration_days = (
                (exit_date - entry_date).days if entry_date is not None else 0
            )
            trade_log.append(
                TradeRecord(
                    entry_date=entry_date or ts,
                    entry_price=entry_price or open_price,
                    exit_date=exit_date,
                    exit_price=exit_price,
                    shares=shares,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    trade_duration_days=trade_duration_days,
                )
            )
            cash = cash + (shares * exit_price)
            if abs(cash) < 1e-8:
                cash = 0.0
            shares = 0.0
            entry_date = None
            entry_price = None
            pending_exit = False

        # Mark-to-market equity at bar close
        equity_curve.iloc[i] = cash + (shares * close_price)

        # Evaluate signals for next bar
        if shares == 0.0 and not pending_entry and entry_signal.iloc[i]:
            pending_entry = True
        elif shares > 0.0 and not pending_exit and exit_signal.iloc[i]:
            pending_exit = True

    # Force-close at last bar close if still in position
    if shares > 0.0:
        last_ts = df.index[-1]
        last_close = float(df.iloc[-1]["close"])
        pnl = (last_close - (entry_price or 0.0)) * shares
        pnl_pct = pnl / initial_capital if initial_capital else 0.0
        trade_duration_days = (
            (last_ts - entry_date).days if entry_date is not None else 0
        )
        trade_log.append(
            TradeRecord(
                entry_date=entry_date or last_ts,
                entry_price=entry_price or last_close,
                exit_date=last_ts,
                exit_price=last_close,
                shares=shares,
                pnl=pnl,
                pnl_pct=pnl_pct,
                trade_duration_days=trade_duration_days,
            )
        )
        cash = cash + (shares * last_close)
        if abs(cash) < 1e-8:
            cash = 0.0
        shares = 0.0
        equity_curve.iloc[-1] = cash

    return [t.to_dict() for t in trade_log], equity_curve
