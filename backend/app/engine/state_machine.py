from __future__ import annotations

from dataclasses import dataclass, field
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
    exit_reason: str
    entry_commission: float
    exit_commission: float
    total_commission: float
    direction: str = "LONG"

    # Attribution fields (optional)
    entry_conditions_met: list[str] | None = None
    exit_conditions_met: list[str] | None = None
    entry_signal_strength: float | None = None
    market_return_during_trade: float | None = None
    alpha: float | None = None
    indicator_snapshot_entry: dict | None = None
    indicator_snapshot_exit: dict | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "entry_date": self.entry_date,
            "entry_price": self.entry_price,
            "exit_date": self.exit_date,
            "exit_price": self.exit_price,
            "shares": self.shares,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "trade_duration_days": self.trade_duration_days,
            "exit_reason": self.exit_reason,
            "entry_commission": self.entry_commission,
            "exit_commission": self.exit_commission,
            "total_commission": self.total_commission,
            "direction": self.direction,
        }

        if self.entry_conditions_met is not None:
            result["entry_conditions_met"] = self.entry_conditions_met
        if self.exit_conditions_met is not None:
            result["exit_conditions_met"] = self.exit_conditions_met
        if self.entry_signal_strength is not None:
            result["entry_signal_strength"] = self.entry_signal_strength
        if self.market_return_during_trade is not None:
            result["market_return_during_trade"] = self.market_return_during_trade
        if self.alpha is not None:
            result["alpha"] = self.alpha
        if self.indicator_snapshot_entry is not None:
            result["indicator_snapshot_entry"] = self.indicator_snapshot_entry
        if self.indicator_snapshot_exit is not None:
            result["indicator_snapshot_exit"] = self.indicator_snapshot_exit

        return result


@dataclass
class PositionState:
    """Tracks state for one direction (LONG or SHORT)."""
    direction: str = "LONG"
    shares: float = 0.0
    entry_price: float | None = None
    entry_date: pd.Timestamp | None = None
    entry_commission: float = 0.0
    pending_entry: bool = False
    pending_exit: bool = False
    entry_bar_idx: int | None = None
    exit_bar_idx: int | None = None
    entry_attribution_data: dict[str, Any] | None = None
    exit_attribution_data: dict[str, Any] | None = None

    @property
    def in_position(self) -> bool:
        return self.shares > 0.0

    def reset(self) -> None:
        self.shares = 0.0
        self.entry_price = None
        self.entry_date = None
        self.entry_commission = 0.0
        self.pending_entry = False
        self.pending_exit = False
        self.entry_bar_idx = None
        self.exit_bar_idx = None
        self.entry_attribution_data = None
        self.exit_attribution_data = None


def _capture_entry_attribution(
    df: pd.DataFrame,
    bar_idx: int,
    entry_conditions: dict[str, Any] | None
) -> dict[str, Any] | None:
    if not entry_conditions:
        return None

    try:
        from app.engine.condition_engine import evaluate_conditions_with_attribution
        from app.engine.attribution import get_indicators_used_in_conditions, get_indicator_snapshot

        _, attribution_data = evaluate_conditions_with_attribution(
            df, entry_conditions, bar_idx
        )

        if attribution_data:
            indicators_used = get_indicators_used_in_conditions(
                attribution_data['all_conditions']
            )
            attribution_data['indicator_snapshot'] = get_indicator_snapshot(
                df, bar_idx, indicators_used
            )
            attribution_data['condition_ids'] = [
                str(c.get('id', '')) for c in attribution_data['conditions_met']
                if c.get('id')
            ]

        return attribution_data
    except Exception:
        return None


def _capture_exit_attribution(
    df: pd.DataFrame,
    bar_idx: int,
    exit_conditions: dict[str, Any] | None
) -> dict[str, Any] | None:
    if not exit_conditions:
        return None

    try:
        from app.engine.condition_engine import evaluate_conditions_with_attribution
        from app.engine.attribution import get_indicators_used_in_conditions, get_indicator_snapshot

        _, attribution_data = evaluate_conditions_with_attribution(
            df, exit_conditions, bar_idx
        )

        if attribution_data:
            indicators_used = get_indicators_used_in_conditions(
                attribution_data['all_conditions']
            )
            attribution_data['indicator_snapshot'] = get_indicator_snapshot(
                df, bar_idx, indicators_used
            )
            attribution_data['condition_ids'] = [
                str(c.get('id', '')) for c in attribution_data['conditions_met']
                if c.get('id')
            ]

        return attribution_data
    except Exception:
        return None


def _calculate_trade_attribution(
    df: pd.DataFrame,
    entry_bar_idx: int,
    exit_bar_idx: int,
    pnl_pct: float,
    direction: str = "LONG"
) -> tuple[float | None, float | None]:
    try:
        from app.engine.attribution import calculate_market_return

        market_return = calculate_market_return(
            df, entry_bar_idx, exit_bar_idx, direction
        )
        alpha = pnl_pct - market_return
        return market_return, alpha
    except Exception:
        return None, None


def _create_trade_record_with_attribution(
    entry_date: pd.Timestamp,
    entry_price: float,
    exit_date: pd.Timestamp,
    exit_price: float,
    shares: float,
    pnl: float,
    pnl_pct: float,
    trade_duration_days: int,
    exit_reason: str,
    entry_commission: float,
    exit_commission: float,
    direction: str = "LONG",
    enable_attribution: bool = True,
    df: pd.DataFrame | None = None,
    entry_bar_idx: int | None = None,
    exit_bar_idx: int | None = None,
    entry_attribution_data: dict[str, Any] | None = None,
    exit_attribution_data: dict[str, Any] | None = None,
) -> TradeRecord:
    market_return = None
    alpha = None
    entry_conditions_met = None
    exit_conditions_met = None
    entry_signal_strength = None
    indicator_snapshot_entry = None
    indicator_snapshot_exit = None

    if enable_attribution:
        if df is not None and entry_bar_idx is not None and exit_bar_idx is not None:
            market_return, alpha = _calculate_trade_attribution(
                df, entry_bar_idx, exit_bar_idx, pnl_pct, direction=direction
            )

        if entry_attribution_data:
            entry_conditions_met = entry_attribution_data.get('condition_ids', [])
            entry_signal_strength = entry_attribution_data.get('signal_strength')
            indicator_snapshot_entry = entry_attribution_data.get('indicator_snapshot')

        if exit_attribution_data:
            exit_conditions_met = exit_attribution_data.get('condition_ids', [])
            indicator_snapshot_exit = exit_attribution_data.get('indicator_snapshot')

    return TradeRecord(
        entry_date=entry_date,
        entry_price=entry_price,
        exit_date=exit_date,
        exit_price=exit_price,
        shares=shares,
        pnl=pnl,
        pnl_pct=pnl_pct,
        trade_duration_days=trade_duration_days,
        exit_reason=exit_reason,
        entry_commission=entry_commission,
        exit_commission=exit_commission,
        total_commission=entry_commission + exit_commission,
        direction=direction,
        entry_conditions_met=entry_conditions_met,
        exit_conditions_met=exit_conditions_met,
        entry_signal_strength=entry_signal_strength,
        market_return_during_trade=market_return,
        alpha=alpha,
        indicator_snapshot_entry=indicator_snapshot_entry,
        indicator_snapshot_exit=indicator_snapshot_exit,
    )


def _ensure_series(series: pd.Series | None, index: pd.Index) -> pd.Series:
    if series is None or len(series) == 0:
        return pd.Series([False] * len(index), index=index, dtype=bool)
    if not series.index.equals(index):
        series = series.reindex(index, fill_value=False)
    return series.astype(bool)


def _calculate_position_size(
    cash: float,
    total_capital: float,
    price: float,
    position_size_type: str,
    position_size_value: float,
    allow_fractional: bool,
    stop_price: float | None = None,
    direction: str = "LONG",
) -> float:
    if price <= 0:
        return 0.0

    if position_size_type == "full_capital":
        amount_to_invest = cash
        raw_shares = amount_to_invest / price
    elif position_size_type == "percent_capital":
        amount_to_invest = (position_size_value / 100.0) * total_capital
        amount_to_invest = min(amount_to_invest, cash)
        raw_shares = amount_to_invest / price
    elif position_size_type == "fixed_amount":
        amount_to_invest = position_size_value
        amount_to_invest = min(amount_to_invest, cash)
        raw_shares = amount_to_invest / price
    elif position_size_type == "risk_based":
        if stop_price is None:
            raise ValueError("risk_based position sizing requires stop_price")

        if direction == "LONG":
            stop_distance = price - stop_price
        else:
            stop_distance = stop_price - price

        if stop_distance <= 0:
            return 0.0

        risk_amount = total_capital * (position_size_value / 100.0)
        raw_shares = risk_amount / stop_distance

        position_value = raw_shares * price
        if position_value > cash:
            raw_shares = cash / price
    else:
        raise ValueError(f"Unsupported position_size_type: {position_size_type}")

    if allow_fractional:
        return raw_shares
    else:
        return float(int(raw_shares))


def _apply_slippage(price: float, slippage_pct: float, is_buy: bool) -> float:
    """
    Apply slippage to execution price.

    For LONG: entry=buy (pay more), exit=sell (receive less)
    For SHORT: entry=sell (receive less), exit=buy (pay more)

    Args:
        price: The quoted price
        slippage_pct: Slippage percentage (e.g., 0.05 for 0.05%)
        is_buy: True if buying (LONG entry or SHORT exit), False if selling

    Returns:
        Adjusted price after slippage
    """
    if slippage_pct == 0:
        return price

    slippage_factor = slippage_pct / 100.0

    if is_buy:
        return price * (1.0 + slippage_factor)
    else:
        return price * (1.0 - slippage_factor)


def _calculate_commission(
    shares: float,
    price: float,
    commission_per_trade: float,
    commission_pct: float,
) -> float:
    trade_value = shares * price
    fixed_cost = commission_per_trade
    pct_cost = (commission_pct / 100.0) * trade_value
    return fixed_cost + pct_cost


def _calculate_exit_proceeds(
    shares: float,
    exit_price: float,
    exit_commission: float,
    cash: float,
) -> tuple[float, float]:
    position_value = shares * exit_price
    proceeds = position_value - exit_commission

    if proceeds < 0 and cash + proceeds < 0:
        max_affordable_commission = position_value + cash
        actual_commission = max(0.0, max_affordable_commission)
        proceeds = position_value - actual_commission
        return proceeds, actual_commission

    return proceeds, exit_commission


def _execute_exit(
    pos: PositionState,
    exit_price_raw: float,
    exit_date: pd.Timestamp,
    exit_reason: str,
    cash: float,
    slippage_pct: float,
    commission_per_trade: float,
    commission_pct: float,
    enable_attribution: bool,
    df: pd.DataFrame,
    exit_bar_idx: int,
    exit_attribution_data: dict[str, Any] | None = None,
) -> tuple[TradeRecord, float]:
    """
    Execute an exit for a position. Returns (trade_record, new_cash).

    Handles direction-aware PnL, slippage, commission.
    """
    direction = pos.direction

    # Slippage: LONG exit = sell (receive less), SHORT exit = buy (pay more)
    is_buy = direction == "SHORT"
    execution_price = _apply_slippage(exit_price_raw, slippage_pct, is_buy=is_buy)

    exit_commission = _calculate_commission(
        pos.shares, execution_price, commission_per_trade, commission_pct
    )

    proceeds, actual_exit_commission = _calculate_exit_proceeds(
        pos.shares, execution_price, exit_commission, cash
    )

    entry_price = pos.entry_price or exit_price_raw

    # Direction-aware PnL
    if direction == "LONG":
        pnl = (execution_price - entry_price) * pos.shares - pos.entry_commission - actual_exit_commission
    else:
        pnl = (entry_price - execution_price) * pos.shares - pos.entry_commission - actual_exit_commission

    trade_cost = entry_price * pos.shares + pos.entry_commission
    pnl_pct = (pnl / trade_cost) if trade_cost > 0 else 0.0
    trade_duration_days = (
        (exit_date - pos.entry_date).days if pos.entry_date is not None else 0
    )

    trade = _create_trade_record_with_attribution(
        entry_date=pos.entry_date or exit_date,
        entry_price=entry_price,
        exit_date=exit_date,
        exit_price=execution_price,
        shares=pos.shares,
        pnl=pnl,
        pnl_pct=pnl_pct,
        trade_duration_days=trade_duration_days,
        exit_reason=exit_reason,
        entry_commission=pos.entry_commission,
        exit_commission=actual_exit_commission,
        direction=direction,
        enable_attribution=enable_attribution,
        df=df,
        entry_bar_idx=pos.entry_bar_idx,
        exit_bar_idx=exit_bar_idx,
        entry_attribution_data=pos.entry_attribution_data,
        exit_attribution_data=exit_attribution_data,
    )

    # For SHORT: proceeds = entry_notional + pnl - commissions (already deducted)
    # Simplified: we use same model as long — cash += shares * exit_price - commission
    new_cash = cash + proceeds
    if abs(new_cash) < 1e-8:
        new_cash = 0.0

    return trade, new_cash


def _fill_entry(
    pos: PositionState,
    open_price: float,
    row: pd.Series,
    cash: float,
    df: pd.DataFrame,
    slippage_pct: float,
    commission_per_trade: float,
    commission_pct: float,
    position_size_type: str,
    position_size_value: float,
    allow_fractional: bool,
    stop_loss_pct: float | None,
    dynamic_stop_column: str | None,
    ts: pd.Timestamp,
) -> float:
    """
    Fill a pending entry for a position. Modifies pos in place, returns new cash.
    """
    direction = pos.direction

    # Slippage: LONG entry = buy (pay more), SHORT entry = sell (receive less)
    is_buy = direction == "LONG"
    execution_price = _apply_slippage(open_price, slippage_pct, is_buy=is_buy)

    # Calculate stop price for risk-based sizing
    stop_price = None
    if position_size_type == "risk_based":
        if dynamic_stop_column is not None:
            if dynamic_stop_column in df.columns:
                stop_price = float(row[dynamic_stop_column])
                if pd.isna(stop_price):
                    pos.pending_entry = False
                    return cash
        elif stop_loss_pct is not None:
            if direction == "LONG":
                stop_price = execution_price * (1.0 - stop_loss_pct / 100.0)
            else:
                stop_price = execution_price * (1.0 + stop_loss_pct / 100.0)

    total_capital = cash
    shares = _calculate_position_size(
        cash=cash,
        total_capital=total_capital,
        price=execution_price,
        position_size_type=position_size_type,
        position_size_value=position_size_value,
        allow_fractional=allow_fractional,
        stop_price=stop_price,
        direction=direction,
    )

    if shares <= 0:
        pos.pending_entry = False
        return cash

    entry_commission = _calculate_commission(
        shares, execution_price, commission_per_trade, commission_pct
    )

    total_cost = (shares * execution_price) + entry_commission

    if total_cost > cash:
        affordable_amount = cash - commission_per_trade
        if affordable_amount <= 0:
            pos.pending_entry = False
            return cash

        price_with_pct_commission = execution_price * (1.0 + commission_pct / 100.0)
        max_shares = affordable_amount / price_with_pct_commission
        shares = max_shares if allow_fractional else float(int(max_shares))

        if shares <= 0:
            pos.pending_entry = False
            return cash

        entry_commission = _calculate_commission(
            shares, execution_price, commission_per_trade, commission_pct
        )
        total_cost = (shares * execution_price) + entry_commission

    cash = cash - total_cost
    if abs(cash) < 1e-8:
        cash = 0.0

    pos.shares = shares
    pos.entry_price = execution_price
    pos.entry_date = ts
    pos.entry_commission = entry_commission
    pos.pending_entry = False

    return cash


def _check_stops(
    pos: PositionState,
    current_price: float,
    ts: pd.Timestamp,
    i: int,
    df: pd.DataFrame,
    cash: float,
    trade_log: list[TradeRecord],
    slippage_pct: float,
    commission_per_trade: float,
    commission_pct: float,
    enable_attribution: bool,
    stop_loss_pct: float | None,
    take_profit_pct: float | None,
    dynamic_stop_column: str | None,
) -> float:
    """
    Check dynamic stop, stop loss, and take profit for a position.
    Handles direction-aware comparisons. Returns updated cash.
    """
    if not pos.in_position or pos.entry_price is None:
        return cash

    direction = pos.direction

    # Check dynamic stop first
    if dynamic_stop_column is not None:
        if dynamic_stop_column not in df.columns:
            raise ValueError(f"Dynamic stop column not found: {dynamic_stop_column}")

        dynamic_stop_value = float(df.iloc[i][dynamic_stop_column])

        should_exit = False
        if not pd.isna(dynamic_stop_value):
            # LONG: price crosses BELOW stop. SHORT: price crosses ABOVE stop.
            if direction == "LONG":
                triggered = current_price < dynamic_stop_value
            else:
                triggered = current_price > dynamic_stop_value

            if triggered:
                if i == 0:
                    should_exit = True
                else:
                    prev_close = float(df.iloc[i - 1]["close"])
                    prev_stop = float(df.iloc[i - 1][dynamic_stop_column])

                    if pd.isna(prev_stop):
                        should_exit = True
                    else:
                        if direction == "LONG":
                            if prev_close >= prev_stop:
                                should_exit = True
                        else:
                            if prev_close <= prev_stop:
                                should_exit = True

        if should_exit:
            trade, cash = _execute_exit(
                pos=pos,
                exit_price_raw=current_price,
                exit_date=ts,
                exit_reason="trailing_stop" if _calc_pnl_sign(pos, current_price) >= 0 else "stop_loss",
                cash=cash,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                df=df,
                exit_bar_idx=i,
            )
            trade_log.append(trade)
            pos.reset()
            return cash

    # Check percentage-based stops
    if pos.in_position and pos.entry_price is not None:
        if direction == "LONG":
            price_change_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100.0
        else:
            # SHORT: profit when price goes down
            price_change_pct = ((pos.entry_price - current_price) / pos.entry_price) * 100.0

        # Stop loss: position losing money
        if stop_loss_pct is not None and price_change_pct <= -stop_loss_pct:
            trade, cash = _execute_exit(
                pos=pos,
                exit_price_raw=current_price,
                exit_date=ts,
                exit_reason="stop_loss",
                cash=cash,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                df=df,
                exit_bar_idx=i,
            )
            trade_log.append(trade)
            pos.reset()
            return cash

        # Take profit: position making money
        if take_profit_pct is not None and price_change_pct >= take_profit_pct:
            trade, cash = _execute_exit(
                pos=pos,
                exit_price_raw=current_price,
                exit_date=ts,
                exit_reason="take_profit",
                cash=cash,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                df=df,
                exit_bar_idx=i,
            )
            trade_log.append(trade)
            pos.reset()
            return cash

    return cash


def _calc_pnl_sign(pos: PositionState, current_price: float) -> float:
    """Quick check whether position is profitable at current_price."""
    if pos.entry_price is None:
        return 0.0
    if pos.direction == "LONG":
        return current_price - pos.entry_price
    else:
        return pos.entry_price - current_price


def _mark_to_market(pos: PositionState, current_price: float) -> float:
    """Calculate mark-to-market value of a position."""
    if not pos.in_position or pos.entry_price is None:
        return 0.0
    if pos.direction == "LONG":
        return pos.shares * current_price
    else:
        # SHORT MTM: notional committed + unrealized PnL
        return pos.shares * (2 * pos.entry_price - current_price)


def run_backtest(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    exit_signal: pd.Series,
    initial_capital: float,
    asset_class: str = "STOCK",
    shares: float = 0.0,
    periodic_contribution: dict[str, Any] | None = None,
    position_size_type: str = "full_capital",
    position_size_value: float = 100.0,
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    dynamic_stop_column: str | None = None,
    commission_per_trade: float = 0.0,
    commission_pct: float = 0.0,
    slippage_pct: float = 0.0,
    enable_attribution: bool = True,
    entry_conditions: dict[str, Any] | None = None,
    exit_conditions: dict[str, Any] | None = None,
    # Short selling parameters (optional, backward compatible)
    short_entry_signal: pd.Series | None = None,
    short_exit_signal: pd.Series | None = None,
    short_entry_conditions: dict[str, Any] | None = None,
    short_exit_conditions: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], pd.Series]:
    if df.empty:
        return [], pd.Series([], dtype=float, name="equity")

    for col in ("open", "close"):
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    if position_size_type not in {"full_capital", "percent_capital", "fixed_amount", "risk_based"}:
        raise ValueError(
            f"Invalid position_size_type: {position_size_type}. "
            "Must be 'full_capital', 'percent_capital', 'fixed_amount', or 'risk_based'"
        )
    if position_size_type == "percent_capital":
        if position_size_value <= 0 or position_size_value > 100:
            raise ValueError(
                f"position_size_value must be between 0 and 100 for percent_capital, got {position_size_value}"
            )
    if position_size_type == "fixed_amount":
        if position_size_value <= 0:
            raise ValueError(
                f"position_size_value must be positive for fixed_amount, got {position_size_value}"
            )
    if position_size_type == "risk_based":
        if position_size_value <= 0 or position_size_value > 10:
            raise ValueError(
                f"position_size_value (risk%) must be between 0 and 10 for risk_based, got {position_size_value}"
            )
        if stop_loss_pct is None and dynamic_stop_column is None:
            raise ValueError(
                "risk_based position sizing requires either stop_loss_pct or dynamic_stop_column to be configured"
            )

    if stop_loss_pct is not None and stop_loss_pct <= 0:
        raise ValueError(f"stop_loss_pct must be positive, got {stop_loss_pct}")
    if take_profit_pct is not None and take_profit_pct <= 0:
        raise ValueError(f"take_profit_pct must be positive, got {take_profit_pct}")

    if commission_per_trade < 0:
        raise ValueError(f"commission_per_trade must be non-negative, got {commission_per_trade}")
    if commission_pct < 0:
        raise ValueError(f"commission_pct must be non-negative, got {commission_pct}")
    if slippage_pct < 0:
        raise ValueError(f"slippage_pct must be non-negative, got {slippage_pct}")

    entry_signal = _ensure_series(entry_signal, df.index)
    exit_signal = _ensure_series(exit_signal, df.index)

    # Determine if short selling is active
    has_short = short_entry_signal is not None
    if has_short:
        short_entry_signal = _ensure_series(short_entry_signal, df.index)
        short_exit_signal = _ensure_series(short_exit_signal, df.index)
    else:
        short_entry_signal = _ensure_series(None, df.index)
        short_exit_signal = _ensure_series(None, df.index)

    allow_fractional = asset_class.upper() != "STOCK"

    # Backward-compatible handling if periodic_contribution was passed positionally.
    if isinstance(shares, dict) and periodic_contribution is None:
        periodic_contribution = shares
        shares = 0.0

    cash = float(initial_capital)

    trade_log: list[TradeRecord] = []
    equity_curve = pd.Series(index=df.index, dtype=float, name="equity")

    # Position state machines
    long_pos = PositionState(direction="LONG")
    short_pos = PositionState(direction="SHORT")

    # Periodic contributions setup
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
        # ─── Periodic contributions ───
        if contribution_amount > 0:
            key = period_key(ts)
            if last_period_key is None:
                last_period_key = key
                if include_start:
                    cash += contribution_amount
            elif key != last_period_key:
                cash += contribution_amount
                last_period_key = key

        open_price = float(row["open"])
        close_price = float(row["close"])

        # ─── Fill pending LONG entry ───
        if long_pos.pending_entry and not long_pos.in_position:
            cash = _fill_entry(
                pos=long_pos,
                open_price=open_price,
                row=row,
                cash=cash,
                df=df,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                position_size_type=position_size_type,
                position_size_value=position_size_value,
                allow_fractional=allow_fractional,
                stop_loss_pct=stop_loss_pct,
                dynamic_stop_column=dynamic_stop_column,
                ts=ts,
            )

        # ─── Fill pending SHORT entry ───
        if has_short and short_pos.pending_entry and not short_pos.in_position:
            cash = _fill_entry(
                pos=short_pos,
                open_price=open_price,
                row=row,
                cash=cash,
                df=df,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                position_size_type=position_size_type,
                position_size_value=position_size_value,
                allow_fractional=allow_fractional,
                stop_loss_pct=stop_loss_pct,
                dynamic_stop_column=dynamic_stop_column,
                ts=ts,
            )

        # ─── Fill pending LONG exit ───
        if long_pos.pending_exit and long_pos.in_position:
            trade, cash = _execute_exit(
                pos=long_pos,
                exit_price_raw=open_price,
                exit_date=ts,
                exit_reason="signal",
                cash=cash,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                df=df,
                exit_bar_idx=long_pos.exit_bar_idx or i,
                exit_attribution_data=long_pos.exit_attribution_data,
            )
            trade_log.append(trade)
            long_pos.reset()

        # ─── Fill pending SHORT exit ───
        if has_short and short_pos.pending_exit and short_pos.in_position:
            trade, cash = _execute_exit(
                pos=short_pos,
                exit_price_raw=open_price,
                exit_date=ts,
                exit_reason="signal",
                cash=cash,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                df=df,
                exit_bar_idx=short_pos.exit_bar_idx or i,
                exit_attribution_data=short_pos.exit_attribution_data,
            )
            trade_log.append(trade)
            short_pos.reset()

        # ─── Check stops for LONG ───
        if long_pos.in_position:
            cash = _check_stops(
                pos=long_pos,
                current_price=open_price,
                ts=ts,
                i=i,
                df=df,
                cash=cash,
                trade_log=trade_log,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                dynamic_stop_column=dynamic_stop_column,
            )

        # ─── Check stops for SHORT ───
        if has_short and short_pos.in_position:
            cash = _check_stops(
                pos=short_pos,
                current_price=open_price,
                ts=ts,
                i=i,
                df=df,
                cash=cash,
                trade_log=trade_log,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                dynamic_stop_column=dynamic_stop_column,
            )

        # ─── Mark-to-market equity at bar close ───
        long_mtm = _mark_to_market(long_pos, close_price)
        short_mtm = _mark_to_market(short_pos, close_price)
        equity_curve.iloc[i] = cash + long_mtm + short_mtm

        # ─── Evaluate signals for next bar ───
        # LONG signals
        if not long_pos.in_position and not long_pos.pending_entry and entry_signal.iloc[i]:
            long_pos.pending_entry = True
            long_pos.entry_bar_idx = i
            if enable_attribution:
                long_pos.entry_attribution_data = _capture_entry_attribution(
                    df, i, entry_conditions
                )
        elif long_pos.in_position and not long_pos.pending_exit and exit_signal.iloc[i]:
            long_pos.pending_exit = True
            long_pos.exit_bar_idx = i
            if enable_attribution:
                long_pos.exit_attribution_data = _capture_exit_attribution(
                    df, i, exit_conditions
                )

        # SHORT signals
        if has_short:
            if not short_pos.in_position and not short_pos.pending_entry and short_entry_signal.iloc[i]:
                short_pos.pending_entry = True
                short_pos.entry_bar_idx = i
                if enable_attribution:
                    short_pos.entry_attribution_data = _capture_entry_attribution(
                        df, i, short_entry_conditions
                    )
            elif short_pos.in_position and not short_pos.pending_exit and short_exit_signal.iloc[i]:
                short_pos.pending_exit = True
                short_pos.exit_bar_idx = i
                if enable_attribution:
                    short_pos.exit_attribution_data = _capture_exit_attribution(
                        df, i, short_exit_conditions
                    )

    # ─── Handle pending entries on last bar ───
    for pos, is_short in [(long_pos, False), (short_pos, True)]:
        if is_short and not has_short:
            continue
        if pos.pending_entry and not pos.in_position:
            last_ts = df.index[-1]
            last_close = float(df.iloc[-1]["close"])

            cash = _fill_entry(
                pos=pos,
                open_price=last_close,
                row=df.iloc[-1],
                cash=cash,
                df=df,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                position_size_type=position_size_type,
                position_size_value=position_size_value,
                allow_fractional=allow_fractional,
                stop_loss_pct=stop_loss_pct,
                dynamic_stop_column=dynamic_stop_column,
                ts=last_ts,
            )

            if pos.in_position:
                # Immediately force-close
                trade, cash = _execute_exit(
                    pos=pos,
                    exit_price_raw=last_close,
                    exit_date=last_ts,
                    exit_reason="last_bar_entry_force_close",
                    cash=cash,
                    slippage_pct=slippage_pct,
                    commission_per_trade=commission_per_trade,
                    commission_pct=commission_pct,
                    enable_attribution=enable_attribution,
                    df=df,
                    exit_bar_idx=len(df) - 1,
                )
                trade_log.append(trade)
                pos.reset()
                equity_curve.iloc[-1] = cash + _mark_to_market(long_pos, last_close) + _mark_to_market(short_pos, last_close)

    # ─── Force-close any open positions at last bar ───
    for pos, is_short in [(long_pos, False), (short_pos, True)]:
        if is_short and not has_short:
            continue
        if pos.in_position:
            last_ts = df.index[-1]
            last_close = float(df.iloc[-1]["close"])

            trade, cash = _execute_exit(
                pos=pos,
                exit_price_raw=last_close,
                exit_date=last_ts,
                exit_reason="force_close",
                cash=cash,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                df=df,
                exit_bar_idx=len(df) - 1,
            )
            trade_log.append(trade)
            pos.reset()
            equity_curve.iloc[-1] = cash + _mark_to_market(long_pos, last_close) + _mark_to_market(short_pos, last_close)

    return [t.to_dict() for t in trade_log], equity_curve
