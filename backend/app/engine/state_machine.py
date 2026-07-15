from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


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
    exit_signal_strength: float | None = None  # ATTR-007
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
        if self.exit_signal_strength is not None:
            result["exit_signal_strength"] = self.exit_signal_strength
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
    entry_bar_idx: int | None = None  # Signal bar index (when signal fired)
    exit_bar_idx: int | None = None   # Signal bar index (when signal fired)
    # ATTR-001 FIX: Track fill bar indices separately from signal bar indices
    entry_fill_bar_idx: int | None = None  # Actual fill bar index (bar after signal)
    exit_fill_bar_idx: int | None = None   # Actual fill bar index (bar after signal)
    entry_attribution_data: dict[str, Any] | None = None
    exit_attribution_data: dict[str, Any] | None = None
    dynamic_tp_pct: float | None = None
    dynamic_exit_ref: float | None = None
    leverage: float = 1.0
    margin: float = 0.0
    liquidation_price: float | None = None
    exit_rule_states: list[dict] | None = None
    pending_exit_reason: str | None = None
    # DYN-002 FIX: Track high-water mark for actual trailing stop
    trailing_stop_high_water: float | None = None
    # CT-NEW-005 FIX: Track counter-trade specific leverage (used at fill time)
    pending_leverage: float | None = None

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
        self.entry_fill_bar_idx = None
        self.exit_fill_bar_idx = None
        self.entry_attribution_data = None
        self.exit_attribution_data = None
        self.dynamic_tp_pct = None
        self.dynamic_exit_ref = None
        self.leverage = 1.0
        self.margin = 0.0
        self.liquidation_price = None
        self.exit_rule_states = None
        self.pending_exit_reason = None
        self.trailing_stop_high_water = None
        self.pending_leverage = None


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
    except (KeyError, ValueError, TypeError, ImportError) as e:
        logger.debug("Failed to capture entry attribution at bar %d: %s", bar_idx, e)
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
    except (KeyError, ValueError, TypeError, ImportError) as e:
        logger.debug("Failed to capture exit attribution at bar %d: %s", bar_idx, e)
        return None


def _calculate_trade_attribution(
    df: pd.DataFrame,
    entry_bar_idx: int,
    exit_bar_idx: int,
    pnl_pct: float,
    direction: str = "LONG",
    entry_fill_bar_idx: int | None = None,
    exit_fill_bar_idx: int | None = None,
    actual_entry_price: float | None = None,
    actual_exit_price: float | None = None,
) -> tuple[float | None, float | None]:
    """
    Calculate market return and alpha for a trade.

    ATTR-001/ATTR-002 FIX:
    - Uses fill bar indices (when available) instead of signal bar indices
    - Uses open prices to match actual execution (fills happen at bar open)

    ATTR-003 FIX:
    - For SL/TP exits, pass actual_exit_price to use the stop level instead of bar open

    Args:
        df: DataFrame with OHLCV data
        entry_bar_idx: Signal bar index (legacy, used if fill idx not provided)
        exit_bar_idx: Signal bar index (legacy, used if fill idx not provided)
        pnl_pct: Trade PnL percentage
        direction: 'LONG' or 'SHORT'
        entry_fill_bar_idx: Actual fill bar index (preferred)
        exit_fill_bar_idx: Actual fill bar index (preferred)
        actual_entry_price: Override entry price (for slippage-adjusted fills)
        actual_exit_price: Override exit price (for SL/TP exits at stop level)

    Returns:
        Tuple of (market_return, alpha) or (None, None) on error
    """
    try:
        from app.engine.attribution import calculate_market_return

        # ATTR-001 FIX: Prefer fill bar indices over signal bar indices
        actual_entry_idx = entry_fill_bar_idx if entry_fill_bar_idx is not None else entry_bar_idx
        actual_exit_idx = exit_fill_bar_idx if exit_fill_bar_idx is not None else exit_bar_idx

        # ATTR-002/ATTR-003 FIX: Use open prices, but allow actual prices for SL/TP
        market_return = calculate_market_return(
            df, actual_entry_idx, actual_exit_idx, direction, use_open_prices=True,
            actual_entry_price=actual_entry_price,
            actual_exit_price=actual_exit_price,
        )
        alpha = pnl_pct - market_return
        return market_return, alpha
    except (KeyError, ValueError, TypeError, ImportError) as e:
        logger.debug(
            "Failed to calculate trade attribution for bars %d-%d: %s",
            entry_bar_idx, exit_bar_idx, e
        )
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
    entry_fill_bar_idx: int | None = None,
    exit_fill_bar_idx: int | None = None,
    use_actual_prices_for_market_return: bool = False,
) -> TradeRecord:
    market_return = None
    alpha = None
    entry_conditions_met = None
    exit_conditions_met = None
    entry_signal_strength = None
    exit_signal_strength = None  # ATTR-007
    indicator_snapshot_entry = None
    indicator_snapshot_exit = None

    if enable_attribution:
        if df is not None and entry_bar_idx is not None and exit_bar_idx is not None:
            # ATTR-001/ATTR-002/ATTR-003 FIX: Pass fill bar indices and actual prices
            # For SL/TP exits, use actual entry/exit prices for market return calculation
            actual_entry = entry_price if use_actual_prices_for_market_return else None
            actual_exit = exit_price if use_actual_prices_for_market_return else None
            market_return, alpha = _calculate_trade_attribution(
                df, entry_bar_idx, exit_bar_idx, pnl_pct, direction=direction,
                entry_fill_bar_idx=entry_fill_bar_idx,
                exit_fill_bar_idx=exit_fill_bar_idx,
                actual_entry_price=actual_entry,
                actual_exit_price=actual_exit,
            )

        if entry_attribution_data:
            entry_conditions_met = entry_attribution_data.get('condition_ids', [])
            entry_signal_strength = entry_attribution_data.get('signal_strength')
            indicator_snapshot_entry = entry_attribution_data.get('indicator_snapshot')

        if exit_attribution_data:
            exit_conditions_met = exit_attribution_data.get('condition_ids', [])
            # ATTR-007: Extract exit signal strength
            exit_signal_strength = exit_attribution_data.get('signal_strength')
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
        exit_signal_strength=exit_signal_strength,  # ATTR-007
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
    commission_per_trade: float = 0.0,
    commission_pct: float = 0.0,
    leverage: float = 1.0,
    kelly_win_rate: float | None = None,
    kelly_payoff_ratio: float | None = None,
    kelly_fraction: float = 1.0,
) -> float:
    """
    Calculate position size based on sizing type.

    Sizing types:
    - full_capital: Use all available cash
    - percent_capital: Use position_size_value% of total capital
    - fixed_amount: Use fixed dollar amount
    - risk_based: Size based on stop distance and risk % (requires stop_price)
    - kelly: Kelly criterion sizing (requires kelly_win_rate, kelly_payoff_ratio)

    Kelly criterion formula (ta4j reference):
        f* = W - (1-W)/R
    where:
        W = win probability (0-1)
        R = payoff ratio (avg_win / avg_loss)
        f* = optimal fraction of capital to bet

    kelly_fraction (default 1.0) scales the result:
        - 0.5 = half-Kelly (more conservative, commonly used)
        - 1.0 = full Kelly
        - Values > 1.0 allowed but risky
    """
    if price <= 0:
        return 0.0

    # SIZE-005 FIX: Reserve commission before calculating max shares
    # This prevents the recalculation loop in _fill_entry
    available_cash = cash - commission_per_trade
    if available_cash <= 0:
        return 0.0

    if position_size_type == "full_capital":
        # For full_capital with commission_pct, solve for max shares:
        # total_cost = shares * price / leverage + shares * price * (pct/100) + fixed_commission
        # available_cash = shares * price * (1/leverage + pct/100)
        # shares = available_cash / (price * (1/leverage + pct/100))
        effective_price = price * (1.0 / leverage + commission_pct / 100.0)
        raw_shares = available_cash / effective_price
    elif position_size_type == "percent_capital":
        amount_to_invest = (position_size_value / 100.0) * total_capital
        amount_to_invest = min(amount_to_invest, available_cash)
        # Account for commission when sizing
        effective_price = price * (1.0 / leverage + commission_pct / 100.0)
        raw_shares = amount_to_invest / effective_price
    elif position_size_type == "fixed_amount":
        amount_to_invest = position_size_value
        amount_to_invest = min(amount_to_invest, available_cash)
        effective_price = price * (1.0 / leverage + commission_pct / 100.0)
        raw_shares = amount_to_invest / effective_price
    elif position_size_type == "risk_based":
        if stop_price is None:
            raise ValueError("risk_based position sizing requires stop_price")

        if direction == "LONG":
            stop_distance = price - stop_price
        else:
            stop_distance = stop_price - price

        if stop_distance <= 0:
            return 0.0

        # SIZE-003 FIX: For risk_based, calculate shares to achieve target risk
        # Do NOT multiply by leverage afterward - that would multiply the risk
        # With leverage, you need FEWER shares to achieve the same dollar risk
        # because each share moves leverage times more in dollar terms
        risk_amount = total_capital * (position_size_value / 100.0)
        raw_shares = risk_amount / stop_distance

        # Verify position fits in available capital (with leverage)
        margin_required = raw_shares * price / leverage
        commission = raw_shares * price * commission_pct / 100.0 + commission_per_trade
        if margin_required + commission > cash:
            # Scale down to fit budget
            effective_price = price * (1.0 / leverage + commission_pct / 100.0)
            raw_shares = available_cash / effective_price
    elif position_size_type == "kelly":
        # Kelly criterion sizing (ta4j pattern)
        # f* = W - (1-W)/R where W=win_rate, R=payoff_ratio
        if kelly_win_rate is None or kelly_payoff_ratio is None:
            raise ValueError("kelly position sizing requires kelly_win_rate and kelly_payoff_ratio")
        if kelly_win_rate <= 0 or kelly_win_rate >= 1:
            raise ValueError("kelly_win_rate must be between 0 and 1 (exclusive)")
        if kelly_payoff_ratio <= 0:
            raise ValueError("kelly_payoff_ratio must be positive")

        # Kelly formula
        kelly_f = kelly_win_rate - (1.0 - kelly_win_rate) / kelly_payoff_ratio

        # Apply fraction (e.g., 0.5 for half-Kelly)
        kelly_f = kelly_f * kelly_fraction

        # Kelly can be negative (don't bet) or > 1 (bet more than capital)
        # Clamp to [0, 1] for safety
        if kelly_f <= 0:
            return 0.0
        kelly_f = min(kelly_f, 1.0)

        # Invest kelly_f fraction of total capital
        amount_to_invest = kelly_f * total_capital
        amount_to_invest = min(amount_to_invest, available_cash)
        effective_price = price * (1.0 / leverage + commission_pct / 100.0)
        raw_shares = amount_to_invest / effective_price
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
    exit_fill_bar_idx: int | None = None,
    use_actual_prices_for_market_return: bool = False,
) -> tuple[TradeRecord, float]:
    """
    Execute an exit for a position. Returns (trade_record, new_cash).

    Handles direction-aware PnL, slippage, commission.

    ATTR-001 FIX: Added exit_fill_bar_idx parameter for accurate market return calculation.
    ATTR-003 FIX: Added use_actual_prices_for_market_return for SL/TP exits.
    """
    direction = pos.direction

    # Slippage: LONG exit = sell (receive less), SHORT exit = buy (pay more)
    is_buy = direction == "SHORT"
    execution_price = _apply_slippage(exit_price_raw, slippage_pct, is_buy=is_buy)

    exit_commission = _calculate_commission(
        pos.shares, execution_price, commission_per_trade, commission_pct
    )

    entry_price = pos.entry_price or exit_price_raw

    if pos.leverage > 1.0:
        # Leveraged exit: proceeds = margin + PnL - commission, clamped to 0
        if direction == "LONG":
            unrealized_pnl = (execution_price - entry_price) * pos.shares
        else:
            unrealized_pnl = (entry_price - execution_price) * pos.shares
        position_value = pos.margin + unrealized_pnl
        if position_value < 0:
            position_value = 0.0
        proceeds = position_value - exit_commission
        actual_exit_commission = exit_commission
        if proceeds < 0:
            proceeds = 0.0
            actual_exit_commission = position_value
    elif direction == "LONG":
        proceeds, actual_exit_commission = _calculate_exit_proceeds(
            pos.shares, execution_price, exit_commission, cash
        )
    else:
        # SHORT exit (no leverage): return collateral adjusted for PnL
        entry_price_for_proceeds = entry_price
        short_position_value = pos.shares * (2 * entry_price_for_proceeds - execution_price)
        if short_position_value < 0:
            short_position_value = 0.0
        proceeds = short_position_value - exit_commission
        actual_exit_commission = exit_commission
        if proceeds < 0 and cash + proceeds < 0:
            actual_exit_commission = max(0.0, short_position_value + cash)
            proceeds = short_position_value - actual_exit_commission

    # Direction-aware PnL
    if direction == "LONG":
        pnl = (execution_price - entry_price) * pos.shares - pos.entry_commission - actual_exit_commission
    else:
        pnl = (entry_price - execution_price) * pos.shares - pos.entry_commission - actual_exit_commission

    if pos.leverage > 1.0:
        trade_cost = pos.margin + pos.entry_commission
    else:
        trade_cost = entry_price * pos.shares + pos.entry_commission
    pnl_pct = (pnl / trade_cost * 100) if trade_cost > 0 else 0.0
    trade_duration_days = (
        (exit_date - pos.entry_date).days if pos.entry_date is not None else 0
    )

    # ATTR-001/ATTR-003 FIX: Pass fill bar indices and actual prices for accurate market return
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
        entry_fill_bar_idx=pos.entry_fill_bar_idx,
        exit_fill_bar_idx=exit_fill_bar_idx,
        use_actual_prices_for_market_return=use_actual_prices_for_market_return,
    )

    # For SHORT: proceeds = entry_notional + pnl - commissions (already deducted)
    # Simplified: we use same model as long — cash += shares * exit_price - commission
    new_cash = cash + proceeds
    if abs(new_cash) < 1e-8:
        new_cash = 0.0

    # Prevent negative cash - should not happen in normal operation
    if new_cash < 0.0:
        logger.warning(
            "Negative cash detected after %s exit (%.6f), clamping to 0.0",
            direction, new_cash
        )
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
    leverage: float = 1.0,
    long_pos_for_equity: "PositionState | None" = None,
    short_pos_for_equity: "PositionState | None" = None,
    fill_bar_idx: int | None = None,
    kelly_win_rate: float | None = None,
    kelly_payoff_ratio: float | None = None,
    kelly_fraction: float = 1.0,
) -> float:
    """
    Fill a pending entry for a position. Modifies pos in place, returns new cash.

    SIZE-001 FIX: Pass long_pos_for_equity and short_pos_for_equity to calculate
    equity (cash + position MTM) for percent_capital and risk_based sizing.

    ATTR-001 FIX: Added fill_bar_idx to track actual fill bar for attribution.

    Kelly sizing: Pass kelly_win_rate, kelly_payoff_ratio, kelly_fraction for
    position_size_type="kelly".
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

    # SIZE-001 FIX: Use equity (cash + position MTM) for sizing, not just cash
    # This ensures position sizing scales with account equity, not depleted cash
    total_capital = cash
    if long_pos_for_equity is not None:
        total_capital += _mark_to_market(long_pos_for_equity, execution_price)
    if short_pos_for_equity is not None:
        total_capital += _mark_to_market(short_pos_for_equity, execution_price)

    # SIZE-003 FIX: Pass leverage to _calculate_position_size
    # For risk_based, it calculates correct shares without multiplying by leverage after
    # For other modes, leverage is factored into effective_price calculation
    shares = _calculate_position_size(
        cash=cash,
        total_capital=total_capital,
        price=execution_price,
        position_size_type=position_size_type,
        position_size_value=position_size_value,
        allow_fractional=allow_fractional,
        stop_price=stop_price,
        direction=direction,
        commission_per_trade=commission_per_trade,
        commission_pct=commission_pct,
        leverage=leverage,
        kelly_win_rate=kelly_win_rate,
        kelly_payoff_ratio=kelly_payoff_ratio,
        kelly_fraction=kelly_fraction,
    )

    # SIZE-003 FIX: Don't multiply by leverage here anymore for risk_based
    # _calculate_position_size now handles leverage internally
    # For non-risk_based modes, shares are already calculated with leverage in mind

    if shares <= 0:
        pos.pending_entry = False
        return cash

    entry_commission = _calculate_commission(
        shares, execution_price, commission_per_trade, commission_pct
    )

    # With leverage, cash deducted = margin (notional / leverage) + commission
    if leverage > 1.0:
        margin = (shares * execution_price) / leverage
        total_cost = margin + entry_commission
    else:
        margin = shares * execution_price
        total_cost = margin + entry_commission

    # SIZE-005/006 FIX: Position sizing now accounts for commission upfront,
    # so this recalculation should rarely be needed (only for edge cases)
    if total_cost > cash:
        affordable_amount = cash - commission_per_trade
        if affordable_amount <= 0:
            pos.pending_entry = False
            return cash

        # SIZE-006 FIX: Correct formula for leveraged positions
        # total_cost = S*P/L + S*P*(C/100) = S*P*(1/L + C/100)
        # S = affordable_amount / (P * (1/L + C/100))
        effective_price = execution_price * (1.0 / leverage + commission_pct / 100.0)
        max_shares = affordable_amount / effective_price
        shares = max_shares if allow_fractional else float(int(max_shares))

        if shares <= 0:
            pos.pending_entry = False
            return cash

        entry_commission = _calculate_commission(
            shares, execution_price, commission_per_trade, commission_pct
        )
        if leverage > 1.0:
            margin = (shares * execution_price) / leverage
            total_cost = margin + entry_commission
        else:
            margin = shares * execution_price
            total_cost = margin + entry_commission

    cash = cash - total_cost
    if abs(cash) < 1e-8:
        cash = 0.0

    pos.shares = shares
    pos.entry_price = execution_price
    pos.entry_date = ts
    pos.entry_commission = entry_commission
    pos.pending_entry = False
    pos.leverage = leverage
    pos.margin = margin
    # ATTR-001 FIX: Track fill bar index for accurate market return calculation
    pos.entry_fill_bar_idx = fill_bar_idx

    # Calculate liquidation price for leveraged positions
    if leverage > 1.0:
        if direction == "LONG":
            pos.liquidation_price = execution_price * (1.0 - 1.0 / leverage)
        else:
            pos.liquidation_price = execution_price * (1.0 + 1.0 / leverage)

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
    dynamic_stop_type: str = "distance",  # "distance", "price", "percentage"
    dynamic_tp_pct: float | None = None,
) -> float:
    """
    Check dynamic stop, stop loss, and take profit for a position.
    Handles direction-aware comparisons. Returns updated cash.
    """
    if not pos.in_position or pos.entry_price is None:
        return cash

    direction = pos.direction

    # Check liquidation first (leveraged positions only)
    if pos.leverage > 1.0 and pos.liquidation_price is not None:
        bar_high = float(df.iloc[i]["high"]) if "high" in df.columns else current_price
        bar_low = float(df.iloc[i]["low"]) if "low" in df.columns else current_price

        liquidated = False
        if direction == "LONG" and bar_low <= pos.liquidation_price:
            liquidated = True
        elif direction == "SHORT" and bar_high >= pos.liquidation_price:
            liquidated = True

        if liquidated:
            # Liquidation: entire margin is lost, proceeds = 0
            entry_price = pos.entry_price
            pnl = -(pos.margin + pos.entry_commission)
            trade_cost = pos.margin + pos.entry_commission
            pnl_pct = (pnl / trade_cost * 100) if trade_cost > 0 else -100.0
            trade_duration_days = (
                (ts - pos.entry_date).days if pos.entry_date is not None else 0
            )

            # ATTR-004 FIX: Use _create_trade_record_with_attribution for liquidation
            trade = _create_trade_record_with_attribution(
                entry_date=pos.entry_date or ts,
                entry_price=entry_price,
                exit_date=ts,
                exit_price=pos.liquidation_price,
                shares=pos.shares,
                pnl=pnl,
                pnl_pct=pnl_pct,
                trade_duration_days=trade_duration_days,
                exit_reason="liquidation",
                entry_commission=pos.entry_commission,
                exit_commission=0.0,
                direction=direction,
                enable_attribution=enable_attribution,
                df=df,
                entry_bar_idx=pos.entry_bar_idx,
                exit_bar_idx=i,
                entry_attribution_data=pos.entry_attribution_data,
                exit_attribution_data=None,  # Liquidation has no exit signal
            )
            trade_log.append(trade)
            pos.reset()
            return cash

    # DYN-002 FIX: Implement actual trailing stop with high-water mark
    # Trailing stop only moves in favorable direction (up for LONG, down for SHORT)
    # dynamic_stop_type determines how to interpret the column value:
    #   - "distance": Column is absolute distance (e.g., ATR value). Stop = high_water - distance
    #   - "price": Column is the stop price directly (e.g., SMA). No trailing, just use the value.
    #   - "percentage": Column is a percentage (e.g., 0.05 = 5%). Stop = high_water * (1 - pct) for LONG
    if dynamic_stop_column is not None:
        if dynamic_stop_column not in df.columns:
            raise ValueError(f"Dynamic stop column not found: {dynamic_stop_column}")

        col_value = float(df.iloc[i][dynamic_stop_column])
        bar_high = float(df.iloc[i]["high"]) if "high" in df.columns else current_price
        bar_low = float(df.iloc[i]["low"]) if "low" in df.columns else current_price

        should_exit = False
        stop_price = None

        if not pd.isna(col_value):
            if dynamic_stop_type == "price":
                # Column IS the stop price (e.g., SMA, support level)
                # No trailing - just use the indicator value directly
                stop_price = col_value
                if direction == "LONG":
                    if bar_low <= stop_price:
                        should_exit = True
                else:
                    if bar_high >= stop_price:
                        should_exit = True

            elif dynamic_stop_type == "percentage":
                # Column is a percentage (e.g., 0.05 for 5%, or 5.0 for 5%)
                # Normalize: if > 1, assume it's already percentage points (5.0 = 5%)
                pct = col_value if col_value < 1 else col_value / 100.0

                # Initialize high-water mark if not set
                if pos.trailing_stop_high_water is None:
                    pos.trailing_stop_high_water = pos.entry_price

                if direction == "LONG":
                    pos.trailing_stop_high_water = max(pos.trailing_stop_high_water, bar_high)
                    # ta4j style: stop = highest × (1 - percentage)
                    stop_price = pos.trailing_stop_high_water * (1.0 - pct)
                    if bar_low <= stop_price:
                        should_exit = True
                else:
                    pos.trailing_stop_high_water = min(pos.trailing_stop_high_water, bar_low)
                    # SHORT: stop = lowest × (1 + percentage)
                    stop_price = pos.trailing_stop_high_water * (1.0 + pct)
                    if bar_high >= stop_price:
                        should_exit = True

            else:  # "distance" (default)
                # Column is absolute distance (e.g., ATR value)
                stop_distance = col_value
                if stop_distance > 0:
                    # Initialize high-water mark if not set
                    if pos.trailing_stop_high_water is None:
                        pos.trailing_stop_high_water = pos.entry_price

                    if direction == "LONG":
                        pos.trailing_stop_high_water = max(pos.trailing_stop_high_water, bar_high)
                        stop_price = pos.trailing_stop_high_water - stop_distance
                        if bar_low <= stop_price:
                            should_exit = True
                    else:
                        pos.trailing_stop_high_water = min(pos.trailing_stop_high_water, bar_low)
                        stop_price = pos.trailing_stop_high_water + stop_distance
                        if bar_high >= stop_price:
                            should_exit = True

        if should_exit and stop_price is not None:
            trade, cash = _execute_exit(
                pos=pos,
                exit_price_raw=stop_price,  # Use calculated stop price, not current_price
                exit_date=ts,
                exit_reason="trailing_stop",
                cash=cash,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                df=df,
                exit_bar_idx=i,
                # ATTR-001: For stop exits, fill happens on same bar as trigger
                exit_fill_bar_idx=i,
                # ATTR-003: Use actual stop price for market return calculation
                use_actual_prices_for_market_return=True,
            )
            trade_log.append(trade)
            pos.reset()
            return cash

    # Check percentage-based stops using intra-bar high/low
    if pos.in_position and pos.entry_price is not None:
        entry_price = pos.entry_price
        bar_high = float(df.iloc[i]["high"]) if "high" in df.columns else current_price
        bar_low = float(df.iloc[i]["low"]) if "low" in df.columns else current_price

        # Calculate stop and TP price levels
        sl_price = None
        if stop_loss_pct is not None:
            if direction == "LONG":
                sl_price = entry_price * (1.0 - stop_loss_pct / 100.0)
            else:
                sl_price = entry_price * (1.0 + stop_loss_pct / 100.0)

        effective_tp = dynamic_tp_pct if dynamic_tp_pct is not None else take_profit_pct
        tp_price = None
        if effective_tp is not None:
            if direction == "LONG":
                tp_price = entry_price * (1.0 + effective_tp / 100.0)
            else:
                tp_price = entry_price * (1.0 - effective_tp / 100.0)

        # Check if both SL and TP hit in the same bar — SL takes priority
        sl_hit = False
        tp_hit = False
        if direction == "LONG":
            if sl_price is not None and bar_low <= sl_price:
                sl_hit = True
            if tp_price is not None and bar_high >= tp_price:
                tp_hit = True
        else:
            if sl_price is not None and bar_high >= sl_price:
                sl_hit = True
            if tp_price is not None and bar_low <= tp_price:
                tp_hit = True

        if sl_hit:
            trade, cash = _execute_exit(
                pos=pos,
                exit_price_raw=sl_price,
                exit_date=ts,
                exit_reason="stop_loss",
                cash=cash,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                df=df,
                exit_bar_idx=i,
                # ATTR-001: For stop exits, fill happens on same bar as trigger
                exit_fill_bar_idx=i,
                # ATTR-003: Use actual stop price for market return calculation
                use_actual_prices_for_market_return=True,
            )
            trade_log.append(trade)
            pos.reset()
            return cash

        if tp_hit:
            # ATTR-008: Distinguish dynamic TP from static TP in exit_reason
            tp_exit_reason = "dynamic_take_profit" if dynamic_tp_pct is not None else "take_profit"
            trade, cash = _execute_exit(
                pos=pos,
                exit_price_raw=tp_price,
                exit_date=ts,
                exit_reason=tp_exit_reason,
                cash=cash,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                df=df,
                exit_bar_idx=i,
                # ATTR-001: For TP exits, fill happens on same bar as trigger
                exit_fill_bar_idx=i,
                # ATTR-003: Use actual TP price for market return calculation
                use_actual_prices_for_market_return=True,
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

    if pos.leverage > 1.0:
        # Leveraged MTM: margin + unrealized PnL, clamped to 0
        if pos.direction == "LONG":
            unrealized_pnl = (current_price - pos.entry_price) * pos.shares
        else:
            unrealized_pnl = (pos.entry_price - current_price) * pos.shares
        mtm = pos.margin + unrealized_pnl
        return max(0.0, mtm)

    if pos.direction == "LONG":
        return pos.shares * current_price
    else:
        # SHORT MTM: notional committed + unrealized PnL
        return pos.shares * (2 * pos.entry_price - current_price)


def _capture_exit_rule_states(exit_rules: list, df: pd.DataFrame, entry_bar_idx: int | None) -> list[dict]:
    states = []
    for rule in exit_rules:
        if rule.fixed_threshold is not None:
            # EXIT-005 FIX: Validate monitor_col exists before marking active
            if rule.monitor_col not in df.columns:
                logger.warning(
                    "ExitRule '%s': monitor_col '%s' not found in DataFrame, rule inactive",
                    rule.name, rule.monitor_col
                )
                states.append({"ref_value": rule.fixed_threshold, "active": False})
            else:
                states.append({"ref_value": rule.fixed_threshold, "active": True})
            continue
        if rule.ref_col not in df.columns or entry_bar_idx is None:
            states.append({"ref_value": None, "active": False})
            continue
        # EXIT-005 FIX: Validate monitor_col exists
        if rule.monitor_col not in df.columns:
            logger.warning(
                "ExitRule '%s': monitor_col '%s' not found in DataFrame, rule inactive",
                rule.name, rule.monitor_col
            )
            states.append({"ref_value": None, "active": False})
            continue
        val = float(df.iloc[entry_bar_idx][rule.ref_col])
        if pd.isna(val):
            states.append({"ref_value": None, "active": False})
            continue
        active = True
        if rule.activation_threshold is not None:
            # EXIT-001 FIX: Use GTE/LTE for activation threshold (not strict inequality)
            if rule.activation_operator == "LT":
                active = val < rule.activation_threshold
            elif rule.activation_operator == "LTE":
                active = val <= rule.activation_threshold
            elif rule.activation_operator == "GT":
                active = val > rule.activation_threshold
            elif rule.activation_operator == "GTE":
                active = val >= rule.activation_threshold
            else:
                active = val > rule.activation_threshold
        states.append({"ref_value": val, "active": active})
    return states


def _check_exit_rules(
    exit_rules: list,
    pos: PositionState,
    df: pd.DataFrame,
    i: int,
    close_price: float,
    direction: str,
) -> None:
    for idx, rule in enumerate(exit_rules):
        state = pos.exit_rule_states[idx]
        if not state["active"] or state["ref_value"] is None:
            continue
        if rule.monitor_col not in df.columns:
            continue
        # EXIT-003 FIX: Check pd.notna() before bool() - NaN should not skip
        if rule.skip_col and rule.skip_col in df.columns:
            skip_val = df.iloc[i][rule.skip_col]
            if pd.notna(skip_val) and bool(skip_val):
                continue
        monitor_val = float(df.iloc[i][rule.monitor_col])
        if pd.isna(monitor_val):
            continue
        # EXIT-007 FIX: Support GTE/LTE operators
        if rule.operator == "LT":
            triggered = monitor_val < state["ref_value"]
        elif rule.operator == "LTE":
            triggered = monitor_val <= state["ref_value"]
        elif rule.operator == "GT":
            triggered = monitor_val > state["ref_value"]
        elif rule.operator == "GTE":
            triggered = monitor_val >= state["ref_value"]
        else:
            triggered = monitor_val > state["ref_value"]
        if not triggered:
            continue
        if rule.min_loss_pct is not None and pos.entry_price is not None:
            if direction == "LONG":
                pnl_pct = (close_price - pos.entry_price) / pos.entry_price * 100
            else:
                pnl_pct = (pos.entry_price - close_price) / pos.entry_price * 100
            if pnl_pct > -abs(rule.min_loss_pct):
                continue
        pos.pending_exit = True
        pos.exit_bar_idx = i
        pos.pending_exit_reason = rule.name
        break


def run_backtest(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    exit_signal: pd.Series,
    initial_capital: float,
    asset_class: str = "STOCK",
    shares: float = 0.0,
    periodic_contribution: dict[str, Any] | None = None,  # Deprecated: use periodic_cash_injection
    periodic_cash_injection: dict[str, Any] | None = None,  # DCA-001: Honest naming (does NOT add to positions)
    position_size_type: str = "full_capital",
    position_size_value: float = 100.0,
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    dynamic_stop_column: str | None = None,
    dynamic_stop_type: str = "distance",  # "distance" (ATR), "price" (SMA), "percentage" (ta4j style)
    dynamic_tp_pct_column: str | None = None,
    dynamic_exit_monitor_column: str | None = None,
    dynamic_exit_ref_column: str | None = None,
    dynamic_exit_skip_column: str | None = None,
    dynamic_exit_min_loss_pct: float | None = None,
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
    leverage: float = 1.0,
    exit_rules: list | None = None,
    # Counter-trade parameters
    enable_counter_trades: bool = False,
    counter_tp_multiplier: float = 1.5,
    counter_leverage: float | None = None,  # CT-NEW-005: Separate leverage for counter-trades (default: 1.0)
    # Kelly sizing parameters (ta4j pattern)
    kelly_win_rate: float | None = None,
    kelly_payoff_ratio: float | None = None,
    kelly_fraction: float = 1.0,
) -> tuple[list[dict[str, Any]], pd.Series]:
    if initial_capital <= 0:
        raise ValueError(f"initial_capital must be positive, got {initial_capital}")

    if df.empty:
        return [], pd.Series([], dtype=float, name="equity")

    for col in ("open", "close"):
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    if position_size_type not in {"full_capital", "percent_capital", "fixed_amount", "risk_based", "kelly"}:
        raise ValueError(
            f"Invalid position_size_type: {position_size_type}. "
            "Must be 'full_capital', 'percent_capital', 'fixed_amount', 'risk_based', or 'kelly'"
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
    if position_size_type == "kelly":
        if kelly_win_rate is None or kelly_payoff_ratio is None:
            raise ValueError(
                "kelly position sizing requires kelly_win_rate and kelly_payoff_ratio"
            )
        if kelly_win_rate <= 0 or kelly_win_rate >= 1:
            raise ValueError(
                f"kelly_win_rate must be between 0 and 1 (exclusive), got {kelly_win_rate}"
            )
        if kelly_payoff_ratio <= 0:
            raise ValueError(
                f"kelly_payoff_ratio must be positive, got {kelly_payoff_ratio}"
            )
        if kelly_fraction <= 0:
            raise ValueError(
                f"kelly_fraction must be positive, got {kelly_fraction}"
            )

    if stop_loss_pct is not None and stop_loss_pct <= 0:
        raise ValueError(f"stop_loss_pct must be positive, got {stop_loss_pct}")
    if take_profit_pct is not None and take_profit_pct <= 0:
        raise ValueError(f"take_profit_pct must be positive, got {take_profit_pct}")

    # Validate dynamic_stop_type
    valid_stop_types = {"distance", "price", "percentage"}
    if dynamic_stop_type not in valid_stop_types:
        raise ValueError(
            f"dynamic_stop_type must be one of {valid_stop_types}, got '{dynamic_stop_type}'"
        )

    if commission_per_trade < 0:
        raise ValueError(f"commission_per_trade must be non-negative, got {commission_per_trade}")
    if commission_pct < 0:
        raise ValueError(f"commission_pct must be non-negative, got {commission_pct}")
    if slippage_pct < 0:
        raise ValueError(f"slippage_pct must be non-negative, got {slippage_pct}")

    # Leverage bounds validation (Binance max is 125x for futures)
    if leverage < 1.0 or leverage > 125.0:
        raise ValueError(
            f"leverage must be between 1.0 and 125.0 (Binance max), got {leverage}"
        )

    if counter_tp_multiplier <= 0:
        raise ValueError(f"counter_tp_multiplier must be positive, got {counter_tp_multiplier}")

    # CT-NEW-005 FIX: Validate counter_leverage if provided (default to 1.0 for safety)
    effective_counter_leverage = counter_leverage if counter_leverage is not None else 1.0
    if effective_counter_leverage < 1.0 or effective_counter_leverage > 125.0:
        raise ValueError(
            f"counter_leverage must be between 1.0 and 125.0, got {effective_counter_leverage}"
        )

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
    # DCA-001 FIX: Support both old and new parameter names with deprecation warning
    if isinstance(shares, dict) and periodic_contribution is None and periodic_cash_injection is None:
        periodic_contribution = shares
        shares = 0.0

    # Merge periodic_cash_injection (new) with periodic_contribution (deprecated)
    effective_cash_injection = periodic_cash_injection or periodic_contribution
    if periodic_contribution is not None and periodic_cash_injection is None:
        import warnings
        warnings.warn(
            "periodic_contribution is deprecated, use periodic_cash_injection instead. "
            "Note: This feature adds cash to your account, it does NOT add to existing positions (true DCA).",
            DeprecationWarning,
            stacklevel=2
        )

    cash = float(initial_capital)

    trade_log: list[TradeRecord] = []
    equity_curve = pd.Series(index=df.index, dtype=float, name="equity")

    # Position state machines
    long_pos = PositionState(direction="LONG")
    short_pos = PositionState(direction="SHORT")

    # Counter-trade state
    counter_trade_pending: dict[str, Any] | None = None  # {"direction": str, "tp_pct": float, "bar_idx": int, "leverage": float}

    # Periodic cash injection setup (formerly "contributions")
    # NOTE: This adds cash to the account, it does NOT automatically add to existing positions
    contribution_amount = 0.0
    contribution_frequency = ""
    interval_days = 0
    include_start = False
    if effective_cash_injection:
        contribution_amount = float(effective_cash_injection.get("amount", 0.0))
        contribution_frequency = str(
            effective_cash_injection.get("frequency", "monthly")
        ).lower()
        interval_days = int(effective_cash_injection.get("interval_days", 0))
        include_start = bool(effective_cash_injection.get("include_start", False))

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
                # CT-NEW-005 FIX: Use pending_leverage for counter-trades, else global leverage
                leverage=long_pos.pending_leverage if long_pos.pending_leverage is not None else leverage,
                # SIZE-001: Pass positions for equity calculation
                long_pos_for_equity=long_pos,
                short_pos_for_equity=short_pos if has_short else None,
                # ATTR-001: Pass fill bar index for accurate market return
                fill_bar_idx=i,
                # Kelly sizing params
                kelly_win_rate=kelly_win_rate,
                kelly_payoff_ratio=kelly_payoff_ratio,
                kelly_fraction=kelly_fraction,
            )
            # Clear pending_leverage after fill
            long_pos.pending_leverage = None
            if long_pos.in_position and dynamic_tp_pct_column:
                if dynamic_tp_pct_column in df.columns and long_pos.entry_bar_idx is not None:
                    val = float(df.iloc[long_pos.entry_bar_idx][dynamic_tp_pct_column])
                    # DYN-003 FIX: Validate dynamic TP > 0 (negative/zero would cause instant trigger)
                    if not pd.isna(val) and val > 0:
                        long_pos.dynamic_tp_pct = val
                    elif not pd.isna(val):
                        logger.warning(
                            "Invalid dynamic TP value %.2f at bar %d (must be > 0), ignoring",
                            val, long_pos.entry_bar_idx
                        )
            if long_pos.in_position and dynamic_exit_ref_column:
                if dynamic_exit_ref_column in df.columns and long_pos.entry_bar_idx is not None:
                    val = float(df.iloc[long_pos.entry_bar_idx][dynamic_exit_ref_column])
                    if not pd.isna(val):
                        long_pos.dynamic_exit_ref = val
            if long_pos.in_position and exit_rules:
                long_pos.exit_rule_states = _capture_exit_rule_states(exit_rules, df, long_pos.entry_bar_idx)

        # ─── Fill pending SHORT entry ───
        # CT-NEW-009 FIX: Also check pending_entry when counter-trades enabled (counter-trade may arm SHORT)
        if (has_short or enable_counter_trades) and short_pos.pending_entry and not short_pos.in_position:
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
                # CT-NEW-005 FIX: Use pending_leverage for counter-trades, else global leverage
                leverage=short_pos.pending_leverage if short_pos.pending_leverage is not None else leverage,
                # SIZE-001: Pass positions for equity calculation
                long_pos_for_equity=long_pos,
                short_pos_for_equity=short_pos,
                # ATTR-001: Pass fill bar index for accurate market return
                fill_bar_idx=i,
                # Kelly sizing params
                kelly_win_rate=kelly_win_rate,
                kelly_payoff_ratio=kelly_payoff_ratio,
                kelly_fraction=kelly_fraction,
            )
            # Clear pending_leverage after fill
            short_pos.pending_leverage = None
            if short_pos.in_position and dynamic_tp_pct_column:
                if dynamic_tp_pct_column in df.columns and short_pos.entry_bar_idx is not None:
                    val = float(df.iloc[short_pos.entry_bar_idx][dynamic_tp_pct_column])
                    # DYN-003 FIX: Validate dynamic TP > 0 (negative/zero would cause instant trigger)
                    if not pd.isna(val) and val > 0:
                        short_pos.dynamic_tp_pct = val
                    elif not pd.isna(val):
                        logger.warning(
                            "Invalid dynamic TP value %.2f at bar %d (must be > 0), ignoring",
                            val, short_pos.entry_bar_idx
                        )
            if short_pos.in_position and dynamic_exit_ref_column:
                if dynamic_exit_ref_column in df.columns and short_pos.entry_bar_idx is not None:
                    val = float(df.iloc[short_pos.entry_bar_idx][dynamic_exit_ref_column])
                    if not pd.isna(val):
                        short_pos.dynamic_exit_ref = val
            if short_pos.in_position and exit_rules:
                short_pos.exit_rule_states = _capture_exit_rule_states(exit_rules, df, short_pos.entry_bar_idx)

        # ─── Check stops for LONG (BEFORE pending exits - TP/SL takes priority) ───
        # If TP/SL is hit during this bar, it overrides any pending signal exit
        long_exited_via_stops = False
        if long_pos.in_position:
            prev_in_position = long_pos.in_position
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
                dynamic_stop_type=dynamic_stop_type,
                dynamic_tp_pct=long_pos.dynamic_tp_pct,
            )
            # Check if stops triggered an exit
            if prev_in_position and not long_pos.in_position:
                long_exited_via_stops = True
                # Clear any pending exit since we already exited via stops
                long_pos.pending_exit = False
                long_pos.pending_exit_reason = None

        # ─── Check stops for SHORT (BEFORE pending exits - TP/SL takes priority) ───
        short_exited_via_stops = False
        # CT-NEW-009 FIX: Also check stops when counter-trades enabled
        if (has_short or enable_counter_trades) and short_pos.in_position:
            prev_in_position = short_pos.in_position
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
                dynamic_stop_type=dynamic_stop_type,
                dynamic_tp_pct=short_pos.dynamic_tp_pct,
            )
            # Check if stops triggered an exit
            if prev_in_position and not short_pos.in_position:
                short_exited_via_stops = True
                # Clear any pending exit since we already exited via stops
                short_pos.pending_exit = False
                short_pos.pending_exit_reason = None

        # ─── Fill pending LONG exit (only if not already exited via stops) ───
        if long_pos.pending_exit and long_pos.in_position and not long_exited_via_stops:
            trade, cash = _execute_exit(
                pos=long_pos,
                exit_price_raw=open_price,
                exit_date=ts,
                exit_reason=long_pos.pending_exit_reason or "signal",
                cash=cash,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                df=df,
                exit_bar_idx=long_pos.exit_bar_idx or i,
                exit_attribution_data=long_pos.exit_attribution_data,
                # ATTR-001: Signal fired on previous bar, fill on current bar
                exit_fill_bar_idx=i,
            )
            trade_log.append(trade)

            # ─── Counter-trade triggering (LONG exit) ───
            if enable_counter_trades:
                exit_reason = trade.to_dict()["exit_reason"]
                pnl = trade.to_dict()["pnl"]
                # Only trigger on signal exits with loss
                if exit_reason == "signal" and pnl < 0:
                    # CT-NEW-006 FIX: Use raw price-based loss %, not pnl_pct (which includes costs)
                    # This makes the TP target achievable without needing to overcome transaction costs
                    entry_price = trade.to_dict()["entry_price"]
                    exit_price = trade.to_dict()["exit_price"]
                    if entry_price > 0:
                        price_loss_pct = abs((exit_price - entry_price) / entry_price * 100)
                    else:
                        price_loss_pct = abs(trade.to_dict()["pnl_pct"])
                    counter_tp_pct = price_loss_pct * counter_tp_multiplier
                    counter_trade_pending = {
                        "direction": "SHORT",
                        "tp_pct": counter_tp_pct,
                        "bar_idx": i,
                        # CT-NEW-005 FIX: Store counter_leverage for use at fill time
                        "leverage": effective_counter_leverage,
                    }

            long_pos.reset()

        # ─── Fill pending SHORT exit (only if not already exited via stops) ───
        # CT-NEW-009 FIX: Also allow exit when counter-trades enabled
        if (has_short or enable_counter_trades) and short_pos.pending_exit and short_pos.in_position and not short_exited_via_stops:
            trade, cash = _execute_exit(
                pos=short_pos,
                exit_price_raw=open_price,
                exit_date=ts,
                exit_reason=short_pos.pending_exit_reason or "signal",
                cash=cash,
                slippage_pct=slippage_pct,
                commission_per_trade=commission_per_trade,
                commission_pct=commission_pct,
                enable_attribution=enable_attribution,
                df=df,
                exit_bar_idx=short_pos.exit_bar_idx or i,
                exit_attribution_data=short_pos.exit_attribution_data,
                # ATTR-001: Signal fired on previous bar, fill on current bar
                exit_fill_bar_idx=i,
            )
            trade_log.append(trade)

            # ─── Counter-trade triggering (SHORT exit) ───
            if enable_counter_trades:
                exit_reason = trade.to_dict()["exit_reason"]
                pnl = trade.to_dict()["pnl"]
                # Only trigger on signal exits with loss
                if exit_reason == "signal" and pnl < 0:
                    # CT-NEW-006 FIX: Use raw price-based loss %, not pnl_pct (which includes costs)
                    entry_price = trade.to_dict()["entry_price"]
                    exit_price = trade.to_dict()["exit_price"]
                    if entry_price > 0:
                        # For SHORT: loss = exit > entry, so price_loss_pct = (exit - entry) / entry
                        price_loss_pct = abs((exit_price - entry_price) / entry_price * 100)
                    else:
                        price_loss_pct = abs(trade.to_dict()["pnl_pct"])
                    counter_tp_pct = price_loss_pct * counter_tp_multiplier
                    counter_trade_pending = {
                        "direction": "LONG",
                        "tp_pct": counter_tp_pct,
                        "bar_idx": i,
                        # CT-NEW-005 FIX: Store counter_leverage for use at fill time
                        "leverage": effective_counter_leverage,
                    }

            short_pos.reset()

        # ─── Check dynamic exit reference (indicator < captured threshold) ───
        if dynamic_exit_monitor_column and dynamic_exit_monitor_column in df.columns:
            skip_exit = False
            if dynamic_exit_skip_column and dynamic_exit_skip_column in df.columns:
                skip_exit = bool(df.iloc[i][dynamic_exit_skip_column])
            if not skip_exit:
                monitor_val = float(df.iloc[i][dynamic_exit_monitor_column])
                if long_pos.in_position and not long_pos.pending_exit and long_pos.dynamic_exit_ref is not None:
                    if monitor_val < long_pos.dynamic_exit_ref:
                        # Skip exit if trade hasn't lost enough (min loss threshold)
                        if dynamic_exit_min_loss_pct is not None and long_pos.entry_price is not None:
                            pnl_pct = (close_price - long_pos.entry_price) / long_pos.entry_price * 100
                            if pnl_pct > -abs(dynamic_exit_min_loss_pct):
                                pass  # not losing enough, skip exit
                            else:
                                long_pos.pending_exit = True
                                long_pos.exit_bar_idx = i
                                long_pos.pending_exit_reason = "atr_exit"
                        else:
                            long_pos.pending_exit = True
                            long_pos.exit_bar_idx = i
                            long_pos.pending_exit_reason = "atr_exit"
                if has_short and short_pos.in_position and not short_pos.pending_exit and short_pos.dynamic_exit_ref is not None:
                    if monitor_val < short_pos.dynamic_exit_ref:
                        if dynamic_exit_min_loss_pct is not None and short_pos.entry_price is not None:
                            pnl_pct = (short_pos.entry_price - close_price) / short_pos.entry_price * 100
                            if pnl_pct > -abs(dynamic_exit_min_loss_pct):
                                pass
                            else:
                                short_pos.pending_exit = True
                                short_pos.exit_bar_idx = i
                                short_pos.pending_exit_reason = "atr_exit"
                        else:
                            short_pos.pending_exit = True
                            short_pos.exit_bar_idx = i
                            short_pos.pending_exit_reason = "atr_exit"

        # ─── Check pluggable exit rules ───
        if exit_rules:
            if long_pos.in_position and not long_pos.pending_exit and long_pos.exit_rule_states:
                _check_exit_rules(exit_rules, long_pos, df, i, close_price, "LONG")
            if has_short and short_pos.in_position and not short_pos.pending_exit and short_pos.exit_rule_states:
                _check_exit_rules(exit_rules, short_pos, df, i, close_price, "SHORT")

        # ─── Mark-to-market equity at bar close ───
        long_mtm = _mark_to_market(long_pos, close_price)
        short_mtm = _mark_to_market(short_pos, close_price)
        equity_curve.iloc[i] = cash + long_mtm + short_mtm

        # ─── Evaluate signals for next bar ───
        # Counter-trades have priority over regular signals
        counter_trade_armed_direction: str | None = None
        if enable_counter_trades and counter_trade_pending is not None:
            # Counter-trade enters at NEXT bar (i+1), so arm it now
            target_direction = counter_trade_pending["direction"]
            target_pos = long_pos if target_direction == "LONG" else short_pos

            # Only arm if target position is empty
            if not target_pos.in_position and not target_pos.pending_entry:
                target_pos.pending_entry = True
                target_pos.entry_bar_idx = i
                # Set dynamic TP for counter-trade
                target_pos.dynamic_tp_pct = counter_trade_pending["tp_pct"]
                # CT-NEW-005 FIX: Store counter-trade leverage for use at fill time
                target_pos.pending_leverage = counter_trade_pending.get("leverage", 1.0)
                # Mark direction to skip regular signals
                counter_trade_armed_direction = target_direction
                # Clear counter-trade
                counter_trade_pending = None

        # LONG signals (skip if counter-trade is arming SHORT)
        if counter_trade_armed_direction != "SHORT":
            if not long_pos.in_position and not long_pos.pending_entry and entry_signal.iloc[i]:
                # Binance Futures constraint: no simultaneous long/short on same symbol
                # Skip long entry if short position is currently active
                if not (short_pos.in_position or short_pos.pending_entry):
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

        # SHORT signals (skip if counter-trade is arming LONG)
        if has_short:
            if counter_trade_armed_direction != "LONG":
                if not short_pos.in_position and not short_pos.pending_entry and short_entry_signal.iloc[i]:
                    # Binance Futures constraint: no simultaneous long/short on same symbol
                    # Skip short entry if long position is currently active
                    if not (long_pos.in_position or long_pos.pending_entry):
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
                leverage=leverage,
                # SIZE-001: Pass positions for equity calculation
                long_pos_for_equity=long_pos,
                short_pos_for_equity=short_pos if has_short else None,
                # ATTR-001: Pass fill bar index for accurate market return
                fill_bar_idx=len(df) - 1,
                # Kelly sizing params
                kelly_win_rate=kelly_win_rate,
                kelly_payoff_ratio=kelly_payoff_ratio,
                kelly_fraction=kelly_fraction,
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
                    # ATTR-001: Pass fill bar index
                    exit_fill_bar_idx=len(df) - 1,
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
                # ATTR-001: Force close happens on last bar
                exit_fill_bar_idx=len(df) - 1,
            )
            trade_log.append(trade)
            pos.reset()
            equity_curve.iloc[-1] = cash + _mark_to_market(long_pos, last_close) + _mark_to_market(short_pos, last_close)

    return [t.to_dict() for t in trade_log], equity_curve
