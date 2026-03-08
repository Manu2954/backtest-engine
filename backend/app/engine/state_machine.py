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
    exit_reason: str
    entry_commission: float
    exit_commission: float
    total_commission: float

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
            "exit_reason": self.exit_reason,
            "entry_commission": self.entry_commission,
            "exit_commission": self.exit_commission,
            "total_commission": self.total_commission,
        }


def _ensure_series(series: pd.Series, index: pd.Index) -> pd.Series:
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
) -> float:
    """
    Calculate how many shares to buy based on position sizing rules.

    Args:
        cash: Available cash to invest
        total_capital: Total account value (cash + position value)
        price: Current price per share
        position_size_type: "full_capital", "percent_capital", or "fixed_amount"
        position_size_value: The percentage or dollar amount
        allow_fractional: Whether fractional shares are allowed (True for crypto, False for stocks)

    Returns:
        Number of shares to buy (may be fractional or integer)
    """
    if price <= 0:
        return 0.0

    # Determine the dollar amount to invest
    if position_size_type == "full_capital":
        # Use all available cash (original behavior)
        amount_to_invest = cash
    elif position_size_type == "percent_capital":
        # Use X% of total capital (not just cash)
        # Example: If you have $100,000 total and position_size_value=25,
        # invest $25,000 (even if you have $80,000 cash)
        amount_to_invest = (position_size_value / 100.0) * total_capital
        # But can't invest more than available cash
        amount_to_invest = min(amount_to_invest, cash)
    else:  # fixed_amount
        # Use fixed dollar amount
        # Example: Always invest $10,000 per trade
        amount_to_invest = position_size_value
        # But can't invest more than available cash
        amount_to_invest = min(amount_to_invest, cash)

    # Convert dollar amount to shares
    raw_shares = amount_to_invest / price

    # Apply fractional/integer constraint
    if allow_fractional:
        return raw_shares
    else:
        # For stocks, must buy whole shares
        return float(int(raw_shares))


def _apply_slippage(price: float, slippage_pct: float, is_entry: bool) -> float:
    """
    Apply slippage to execution price.

    Args:
        price: The quoted price
        slippage_pct: Slippage percentage (e.g., 0.05 for 0.05%)
        is_entry: True for entry (pay more), False for exit (receive less)

    Returns:
        Adjusted price after slippage
    """
    if slippage_pct == 0:
        return price

    slippage_factor = slippage_pct / 100.0

    if is_entry:
        # On entry, pay MORE (worse price for buying)
        return price * (1.0 + slippage_factor)
    else:
        # On exit, receive LESS (worse price for selling)
        return price * (1.0 - slippage_factor)


def _calculate_commission(
    shares: float,
    price: float,
    commission_per_trade: float,
    commission_pct: float,
) -> float:
    """
    Calculate total commission for a trade.

    Args:
        shares: Number of shares traded
        price: Price per share
        commission_per_trade: Fixed commission per trade
        commission_pct: Commission as percentage of trade value

    Returns:
        Total commission cost
    """
    trade_value = shares * price

    # Fixed commission
    fixed_cost = commission_per_trade

    # Percentage commission
    pct_cost = (commission_pct / 100.0) * trade_value

    # Total commission
    return fixed_cost + pct_cost


def _calculate_exit_proceeds(
    shares: float,
    exit_price: float,
    exit_commission: float,
    cash: float,
) -> tuple[float, float]:
    """
    Calculate proceeds from exit and validate cash doesn't go negative.

    Args:
        shares: Number of shares being sold
        exit_price: Exit price per share
        exit_commission: Commission charged for exit
        cash: Current available cash

    Returns:
        Tuple of (proceeds, actual_commission_charged)
        - If proceeds would be negative and cause negative cash, commission is capped
    """
    position_value = shares * exit_price
    proceeds = position_value - exit_commission

    # Check if proceeds are negative and would cause negative cash
    if proceeds < 0 and cash + proceeds < 0:
        # Cap commission at position value + available cash
        # This prevents cash from going negative
        max_affordable_commission = position_value + cash
        actual_commission = max(0.0, max_affordable_commission)
        proceeds = position_value - actual_commission
        return proceeds, actual_commission

    return proceeds, exit_commission


def run_backtest(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    exit_signal: pd.Series,
    initial_capital: float,
    asset_class: str = "STOCK",
    shares: float = 0.0,
    periodic_contribution: dict[str, Any] | None = None,
    # Position sizing parameters
    position_size_type: str = "full_capital",
    position_size_value: float = 100.0,
    # Risk management parameters
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    dynamic_stop_column: str | None = None,
    # Transaction cost parameters
    commission_per_trade: float = 0.0,
    commission_pct: float = 0.0,
    slippage_pct: float = 0.0,
) -> tuple[list[dict[str, Any]], pd.Series]:
    if df.empty:
        return [], pd.Series([], dtype=float, name="equity")

    for col in ("open", "close"):
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # NEW: Validate position sizing parameters
    if position_size_type not in {"full_capital", "percent_capital", "fixed_amount"}:
        raise ValueError(
            f"Invalid position_size_type: {position_size_type}. "
            "Must be 'full_capital', 'percent_capital', or 'fixed_amount'"
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

    # NEW: Validate risk management parameters
    if stop_loss_pct is not None and stop_loss_pct <= 0:
        raise ValueError(f"stop_loss_pct must be positive, got {stop_loss_pct}")
    if take_profit_pct is not None and take_profit_pct <= 0:
        raise ValueError(f"take_profit_pct must be positive, got {take_profit_pct}")

    # NEW: Validate transaction cost parameters
    if commission_per_trade < 0:
        raise ValueError(f"commission_per_trade must be non-negative, got {commission_per_trade}")
    if commission_pct < 0:
        raise ValueError(f"commission_pct must be non-negative, got {commission_pct}")
    if slippage_pct < 0:
        raise ValueError(f"slippage_pct must be non-negative, got {slippage_pct}")

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
    entry_commission: float = 0.0  # Track commission paid on entry for PnL calculation

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
            # Apply slippage to entry price (pay more)
            execution_price = _apply_slippage(open_price, slippage_pct, is_entry=True)

            # Calculate position size based on sizing rules
            total_capital = cash  # When flat, total capital = cash
            shares = _calculate_position_size(
                cash=cash,
                total_capital=total_capital,
                price=execution_price,
                position_size_type=position_size_type,
                position_size_value=position_size_value,
                allow_fractional=allow_fractional,
            )

            # Skip entry if no shares can be purchased
            if shares <= 0:
                pending_entry = False
            else:
                # Calculate commission for entry
                entry_commission = _calculate_commission(
                    shares, execution_price, commission_per_trade, commission_pct
                )

                # Validate that total cost doesn't exceed available cash
                total_cost = (shares * execution_price) + entry_commission

                if total_cost > cash:
                    # Reduce shares to fit within budget after commission
                    # Reserve commission amount first
                    affordable_amount = cash - commission_per_trade

                    if affordable_amount <= 0:
                        # Can't even afford the flat commission
                        pending_entry = False
                        shares = 0.0
                    else:
                        # Calculate max shares that fit within budget
                        # Formula: cash = shares * price * (1 + commission_pct/100) + commission_per_trade
                        # Solving for shares: shares = (cash - commission_per_trade) / (price * (1 + commission_pct/100))
                        price_with_pct_commission = execution_price * (1.0 + commission_pct / 100.0)
                        max_shares = affordable_amount / price_with_pct_commission

                        # Apply fractional constraint
                        shares = max_shares if allow_fractional else float(int(max_shares))

                        if shares <= 0:
                            # After adjustment, still can't afford any shares
                            pending_entry = False
                            shares = 0.0
                        else:
                            # Recalculate commission with adjusted shares
                            entry_commission = _calculate_commission(
                                shares, execution_price, commission_per_trade, commission_pct
                            )
                            total_cost = (shares * execution_price) + entry_commission

                # Only proceed with entry if we have shares to buy
                if shares > 0:
                    # Deduct cost (shares + commission) from cash
                    cash = cash - total_cost
                    if abs(cash) < 1e-8:
                        cash = 0.0

                    entry_price = execution_price
                    entry_date = ts
                    pending_entry = False
                else:
                    pending_entry = False

        # Fill pending exit at current bar open
        if pending_exit and shares > 0.0:
            # Apply slippage to exit price (receive less)
            execution_price = _apply_slippage(open_price, slippage_pct, is_entry=False)

            # Calculate commission for exit
            exit_commission = _calculate_commission(
                shares, execution_price, commission_per_trade, commission_pct
            )

            # Calculate proceeds and validate cash won't go negative
            proceeds, actual_exit_commission = _calculate_exit_proceeds(
                shares, execution_price, exit_commission, cash
            )

            exit_price = execution_price
            exit_date = ts
            exit_reason = "signal"  # Exit triggered by strategy signal

            pnl = (exit_price - (entry_price or 0.0)) * shares - entry_commission - actual_exit_commission
            trade_cost = (entry_price or 0.0) * shares + entry_commission
            pnl_pct = (pnl / trade_cost * 100.0) if trade_cost > 0 else 0.0
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
                    exit_reason=exit_reason,
                    entry_commission=entry_commission,
                    exit_commission=actual_exit_commission,
                    total_commission=entry_commission + actual_exit_commission,
                )
            )

            # Add proceeds to cash
            cash = cash + proceeds
            if abs(cash) < 1e-8:
                cash = 0.0
            shares = 0.0
            entry_date = None
            entry_price = None
            entry_commission = 0.0  # Reset for next trade
            pending_exit = False

        # NEW: Check stop loss and take profit WHILE in position (after any exits processed)
        # This happens at the bar's open price (realistic - you'd see the price and exit)
        if shares > 0.0 and entry_price is not None:
            current_price = open_price

            # Check dynamic stop first (takes priority over percentage stops)
            if dynamic_stop_column is not None:
                if dynamic_stop_column not in df.columns:
                    raise ValueError(f"Dynamic stop column not found: {dynamic_stop_column}")

                dynamic_stop_value = float(row[dynamic_stop_column])

                # Exit only on crossover (price crosses below stop)
                should_exit = False
                if not pd.isna(dynamic_stop_value) and current_price < dynamic_stop_value:
                    # Check if this is a genuine cross-below
                    if i == 0:
                        # First bar - use simple comparison
                        should_exit = True
                    else:
                        # Check previous bar's relationship
                        prev_close = float(df.iloc[i - 1]["close"])
                        prev_stop = float(df.iloc[i - 1][dynamic_stop_column])

                        if pd.isna(prev_stop):
                            # No previous stop value - treat as first trigger
                            should_exit = True
                        elif prev_close >= prev_stop:
                            # Was above stop on previous bar, now below - genuine cross
                            should_exit = True
                        # else: Already below stop on previous bar - don't re-exit

                if should_exit:
                    # Apply slippage to exit price (receive less)
                    execution_price = _apply_slippage(current_price, slippage_pct, is_entry=False)

                    # Calculate commission for exit
                    exit_commission = _calculate_commission(
                        shares, execution_price, commission_per_trade, commission_pct
                    )

                    # Calculate proceeds and validate cash won't go negative
                    proceeds, actual_exit_commission = _calculate_exit_proceeds(
                        shares, execution_price, exit_commission, cash
                    )

                    exit_price = execution_price
                    exit_date = ts

                    # Calculate P&L to determine exit reason
                    pnl = (exit_price - entry_price) * shares - entry_commission - actual_exit_commission

                    # Label as trailing_stop (profit) or stop_loss (loss)
                    exit_reason = "trailing_stop" if pnl >= 0 else "stop_loss"

                    trade_cost = entry_price * shares + entry_commission
                    pnl_pct = (pnl / trade_cost * 100.0) if trade_cost > 0 else 0.0
                    trade_duration_days = (
                        (exit_date - entry_date).days if entry_date is not None else 0
                    )
                    trade_log.append(
                        TradeRecord(
                            entry_date=entry_date or ts,
                            entry_price=entry_price,
                            exit_date=exit_date,
                            exit_price=exit_price,
                            shares=shares,
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            trade_duration_days=trade_duration_days,
                            exit_reason=exit_reason,
                            entry_commission=entry_commission,
                            exit_commission=actual_exit_commission,
                            total_commission=entry_commission + actual_exit_commission,
                        )
                    )

                    # Add proceeds to cash
                    cash = cash + proceeds
                    if abs(cash) < 1e-8:
                        cash = 0.0
                    shares = 0.0
                    entry_date = None
                    entry_price = None
                    entry_commission = 0.0  # Reset for next trade
                    pending_exit = False  # Clear any pending signal exit

            # Check percentage-based stops (only if dynamic stop didn't trigger)
            if shares > 0.0 and entry_price is not None:
                price_change_pct = ((current_price - entry_price) / entry_price) * 100.0

                # Check stop loss (price dropped too much)
                if stop_loss_pct is not None and price_change_pct <= -stop_loss_pct:
                    # Apply slippage to exit price (receive less)
                    execution_price = _apply_slippage(current_price, slippage_pct, is_entry=False)

                    # Calculate commission for exit
                    exit_commission = _calculate_commission(
                        shares, execution_price, commission_per_trade, commission_pct
                    )

                    # Calculate proceeds and validate cash won't go negative
                    proceeds, actual_exit_commission = _calculate_exit_proceeds(
                        shares, execution_price, exit_commission, cash
                    )

                    exit_price = execution_price
                    exit_date = ts
                    exit_reason = "stop_loss"

                    pnl = (exit_price - entry_price) * shares - entry_commission - actual_exit_commission
                    trade_cost = entry_price * shares + entry_commission
                    pnl_pct = (pnl / trade_cost * 100.0) if trade_cost > 0 else 0.0
                    trade_duration_days = (
                        (exit_date - entry_date).days if entry_date is not None else 0
                    )
                    trade_log.append(
                        TradeRecord(
                            entry_date=entry_date or ts,
                            entry_price=entry_price,
                            exit_date=exit_date,
                            exit_price=exit_price,
                            shares=shares,
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            trade_duration_days=trade_duration_days,
                            exit_reason=exit_reason,
                            entry_commission=entry_commission,
                            exit_commission=actual_exit_commission,
                            total_commission=entry_commission + actual_exit_commission,
                        )
                    )

                    # Add proceeds to cash
                    cash = cash + proceeds
                    if abs(cash) < 1e-8:
                        cash = 0.0
                    shares = 0.0
                    entry_date = None
                    entry_price = None
                    entry_commission = 0.0  # Reset for next trade
                    pending_exit = False  # Clear any pending signal exit

                # Check take profit (price gained enough)
                elif take_profit_pct is not None and price_change_pct >= take_profit_pct:
                    # Apply slippage to exit price (receive less)
                    execution_price = _apply_slippage(current_price, slippage_pct, is_entry=False)

                    # Calculate commission for exit
                    exit_commission = _calculate_commission(
                        shares, execution_price, commission_per_trade, commission_pct
                    )

                    # Calculate proceeds and validate cash won't go negative
                    proceeds, actual_exit_commission = _calculate_exit_proceeds(
                        shares, execution_price, exit_commission, cash
                    )

                    exit_price = execution_price
                    exit_date = ts
                    exit_reason = "take_profit"

                    pnl = (exit_price - entry_price) * shares - entry_commission - actual_exit_commission
                    trade_cost = entry_price * shares + entry_commission
                    pnl_pct = (pnl / trade_cost * 100.0) if trade_cost > 0 else 0.0
                    trade_duration_days = (
                        (exit_date - entry_date).days if entry_date is not None else 0
                    )
                    trade_log.append(
                        TradeRecord(
                            entry_date=entry_date or ts,
                            entry_price=entry_price,
                            exit_date=exit_date,
                            exit_price=exit_price,
                            shares=shares,
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            trade_duration_days=trade_duration_days,
                            exit_reason=exit_reason,
                            entry_commission=entry_commission,
                            exit_commission=actual_exit_commission,
                            total_commission=entry_commission + actual_exit_commission,
                        )
                    )

                    # Add proceeds to cash
                    cash = cash + proceeds
                    if abs(cash) < 1e-8:
                        cash = 0.0
                    shares = 0.0
                    entry_date = None
                    entry_price = None
                    entry_commission = 0.0  # Reset for next trade
                    pending_exit = False  # Clear any pending signal exit

        # Mark-to-market equity at bar close
        equity_curve.iloc[i] = cash + (shares * close_price)

        # Evaluate signals for next bar
        if shares == 0.0 and not pending_entry and entry_signal.iloc[i]:
            pending_entry = True
        elif shares > 0.0 and not pending_exit and exit_signal.iloc[i]:
            pending_exit = True

    # Handle pending entry on last bar
    if pending_entry and shares == 0.0:
        # Entry signal triggered on last bar but loop ended
        # Fill entry at last bar close, then immediately force-close
        last_ts = df.index[-1]
        last_close = float(df.iloc[-1]["close"])

        # Apply slippage to entry price
        execution_price = _apply_slippage(last_close, slippage_pct, is_entry=True)

        # Calculate position size
        total_capital = cash
        shares = _calculate_position_size(
            cash=cash,
            total_capital=total_capital,
            price=execution_price,
            position_size_type=position_size_type,
            position_size_value=position_size_value,
            allow_fractional=allow_fractional,
        )

        if shares > 0:
            # Calculate commission for entry
            entry_commission = _calculate_commission(
                shares, execution_price, commission_per_trade, commission_pct
            )

            # Validate affordability
            total_cost = (shares * execution_price) + entry_commission

            if total_cost > cash:
                # Reduce shares to fit budget
                affordable_amount = cash - commission_per_trade
                if affordable_amount > 0:
                    price_with_pct_commission = execution_price * (1.0 + commission_pct / 100.0)
                    max_shares = affordable_amount / price_with_pct_commission
                    shares = max_shares if allow_fractional else float(int(max_shares))

                    if shares > 0:
                        entry_commission = _calculate_commission(
                            shares, execution_price, commission_per_trade, commission_pct
                        )
                        total_cost = (shares * execution_price) + entry_commission
                    else:
                        shares = 0.0
                else:
                    shares = 0.0

            if shares > 0:
                # Execute entry
                cash = cash - total_cost
                if abs(cash) < 1e-8:
                    cash = 0.0

                entry_price = execution_price
                entry_date = last_ts

                # Immediately force-close since backtest is ending
                exit_commission = _calculate_commission(
                    shares, execution_price, commission_per_trade, commission_pct
                )

                proceeds, actual_exit_commission = _calculate_exit_proceeds(
                    shares, execution_price, exit_commission, cash
                )

                # Since entry and exit at same price, P&L is just commissions
                pnl = -(entry_commission + actual_exit_commission)
                trade_cost = entry_price * shares + entry_commission
                pnl_pct = (pnl / trade_cost * 100.0) if trade_cost > 0 else 0.0

                trade_log.append(
                    TradeRecord(
                        entry_date=entry_date,
                        entry_price=entry_price,
                        exit_date=last_ts,
                        exit_price=execution_price,
                        shares=shares,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        trade_duration_days=0,
                        exit_reason="last_bar_entry_force_close",
                        entry_commission=entry_commission,
                        exit_commission=actual_exit_commission,
                        total_commission=entry_commission + actual_exit_commission,
                    )
                )

                cash = cash + proceeds
                if abs(cash) < 1e-8:
                    cash = 0.0
                shares = 0.0

    # Force-close at last bar close if still in position
    if shares > 0.0:
        last_ts = df.index[-1]
        last_close = float(df.iloc[-1]["close"])

        # Apply slippage to force-close exit
        execution_price = _apply_slippage(last_close, slippage_pct, is_entry=False)

        # Calculate commission for force-close exit
        exit_commission = _calculate_commission(
            shares, execution_price, commission_per_trade, commission_pct
        )

        # Calculate proceeds and validate cash won't go negative
        proceeds, actual_exit_commission = _calculate_exit_proceeds(
            shares, execution_price, exit_commission, cash
        )

        pnl = (execution_price - (entry_price or 0.0)) * shares - entry_commission - actual_exit_commission
        trade_cost = (entry_price or last_close) * shares + entry_commission
        pnl_pct = (pnl / trade_cost * 100.0) if trade_cost > 0 else 0.0
        trade_duration_days = (
            (last_ts - entry_date).days if entry_date is not None else 0
        )
        trade_log.append(
            TradeRecord(
                entry_date=entry_date or last_ts,
                entry_price=entry_price or last_close,
                exit_date=last_ts,
                exit_price=execution_price,
                shares=shares,
                pnl=pnl,
                pnl_pct=pnl_pct,
                trade_duration_days=trade_duration_days,
                exit_reason="force_close",
                entry_commission=entry_commission,
                exit_commission=actual_exit_commission,
                total_commission=entry_commission + actual_exit_commission,
            )
        )

        # Add proceeds to cash
        cash = cash + proceeds
        if abs(cash) < 1e-8:
            cash = 0.0
        shares = 0.0
        equity_curve.iloc[-1] = cash

    return [t.to_dict() for t in trade_log], equity_curve
