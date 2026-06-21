"""
Signal transformation utilities for advanced strategy preprocessing.

These functions modify entry/exit signals before passing to run_backtest(),
enabling patterns like:
- Counter-trade signal injection
- Deferred entry (confirmation candles)
- Regime-based filtering

All functions are chainable and return modified signal Series.
"""
from __future__ import annotations

import pandas as pd


def apply_counter_trade_signals(
    df: pd.DataFrame,
    long_entry: pd.Series,
    long_exit: pd.Series,
    short_entry: pd.Series,
    short_exit: pd.Series,
    tp_multiplier: float = 1.5,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Inject counter-trade signals after failed trend attempts.

    When a trade exits with loss via signal, this adds an opposite-direction
    entry signal at the next bar with dynamic TP target.

    Note: This is a pre-processor alternative to enable_counter_trades=True
    in run_backtest(). Use this when you need custom counter-trade logic
    or want to inspect/modify the generated signals.

    Args:
        df: DataFrame with OHLCV data
        long_entry: Boolean series for LONG entry signals
        long_exit: Boolean series for LONG exit signals
        short_entry: Boolean series for SHORT entry signals
        short_exit: Boolean series for SHORT exit signals
        tp_multiplier: TP percentage = abs(loss_pct) × multiplier

    Returns:
        Tuple of (long_entry, long_exit, short_entry, short_exit) with
        counter-trade signals injected

    Warning: This requires simulating the backtest to know which trades lose.
    For most use cases, prefer enable_counter_trades=True in run_backtest().
    """
    # Copy signals to avoid modifying originals
    long_entry_out = long_entry.copy()
    long_exit_out = long_exit.copy()
    short_entry_out = short_entry.copy()
    short_exit_out = short_exit.copy()

    # Simple simulation to detect losing trades
    # Note: This is a simplified version and won't match exact backtest behavior
    # For production use, prefer enable_counter_trades=True in run_backtest()

    position = None  # {"direction": str, "entry_idx": int, "entry_price": float}

    for i in range(len(df)):
        bar = df.iloc[i]

        # Check for exits
        if position is not None:
            exit_triggered = False

            if position["direction"] == "LONG" and long_exit_out.iloc[i]:
                exit_triggered = True
                # Estimate exit at next bar open
                if i + 1 < len(df):
                    exit_price = df.iloc[i + 1]["open"]
                    entry_price = position["entry_price"]
                    pnl_pct = (exit_price - entry_price) / entry_price

                    # If loss, inject SHORT counter-trade
                    if pnl_pct < 0 and i + 1 < len(df):
                        short_entry_out.iloc[i + 1] = True

                position = None

            elif position["direction"] == "SHORT" and short_exit_out.iloc[i]:
                exit_triggered = True
                # Estimate exit at next bar open
                if i + 1 < len(df):
                    exit_price = df.iloc[i + 1]["open"]
                    entry_price = position["entry_price"]
                    pnl_pct = (entry_price - exit_price) / entry_price

                    # If loss, inject LONG counter-trade
                    if pnl_pct < 0 and i + 1 < len(df):
                        long_entry_out.iloc[i + 1] = True

                position = None

        # Check for entries
        if position is None:
            if long_entry_out.iloc[i]:
                # Entry fills at next bar open
                if i + 1 < len(df):
                    position = {
                        "direction": "LONG",
                        "entry_idx": i + 1,
                        "entry_price": df.iloc[i + 1]["open"],
                    }
            elif short_entry_out.iloc[i]:
                # Entry fills at next bar open
                if i + 1 < len(df):
                    position = {
                        "direction": "SHORT",
                        "entry_idx": i + 1,
                        "entry_price": df.iloc[i + 1]["open"],
                    }

    return long_entry_out, long_exit_out, short_entry_out, short_exit_out


def apply_deferred_entry(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    confirmation_column: str,
) -> pd.Series:
    """
    Defer entry until confirmation condition is met.

    When an entry signal triggers, it "arms" the entry but doesn't execute.
    Entry only happens when the confirmation condition becomes true.

    Example: SMA crossover arms entry, but wait until close > SMA50 to enter.

    Args:
        df: DataFrame with OHLCV and indicators
        entry_signal: Boolean series for entry signals
        confirmation_column: Column name with boolean confirmation values

    Returns:
        Modified entry signal with deferred entries

    Example:
        >>> armed_signal = evaluate_conditions(df, entry_conditions)
        >>> above_sma = df["close"] > df["sma_50"]
        >>> df["confirmation"] = above_sma
        >>> deferred_entry = apply_deferred_entry(df, armed_signal, "confirmation")
    """
    if confirmation_column not in df.columns:
        raise ValueError(f"Confirmation column '{confirmation_column}' not found in DataFrame")

    deferred_signal = pd.Series(False, index=df.index)
    armed = False

    for i in range(len(df)):
        # Arm on entry signal
        if entry_signal.iloc[i]:
            armed = True

        # Fire when armed AND confirmation is true
        if armed and bool(df.iloc[i][confirmation_column]):
            deferred_signal.iloc[i] = True
            armed = False  # Disarm after firing

    return deferred_signal


def apply_regime_filter(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    regime_column: str,
    allowed_regimes: list[str],
) -> pd.Series:
    """
    Filter entry signals to only trade in specific market regimes.

    Args:
        df: DataFrame with regime labels
        entry_signal: Boolean series for entry signals
        regime_column: Column name with regime labels (e.g., "regime_pelt")
        allowed_regimes: List of regime names to allow trading in

    Returns:
        Filtered entry signal (False for bars in excluded regimes)

    Example:
        >>> # Only trade in BULL and BEAR, skip RANGING
        >>> from app.engine.robustness.regime_detection import detect_regimes
        >>> regimes = detect_regimes(df, strategy="pelt_directional")
        >>> df["regime"] = regimes["regime_labels"]
        >>> filtered = apply_regime_filter(df, entry_signal, "regime", ["BULL", "BEAR"])
    """
    if regime_column not in df.columns:
        raise ValueError(f"Regime column '{regime_column}' not found in DataFrame")

    # Create mask for allowed regimes
    regime_mask = df[regime_column].isin(allowed_regimes)

    # Apply filter: keep entry signals only in allowed regimes
    filtered_signal = entry_signal & regime_mask

    return filtered_signal


def chain_transformers(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    transformers: list[tuple[str, dict]],
) -> pd.Series:
    """
    Chain multiple signal transformers in sequence.

    Args:
        df: DataFrame with OHLCV and indicators
        entry_signal: Initial entry signal
        transformers: List of (transformer_name, kwargs) tuples

    Returns:
        Final transformed signal after applying all transformers

    Example:
        >>> transformers = [
        ...     ("regime_filter", {"regime_column": "regime", "allowed_regimes": ["BULL", "BEAR"]}),
        ...     ("deferred_entry", {"confirmation_column": "above_sma50"}),
        ... ]
        >>> final_signal = chain_transformers(df, base_signal, transformers)
    """
    signal = entry_signal.copy()

    for transformer_name, kwargs in transformers:
        if transformer_name == "regime_filter":
            signal = apply_regime_filter(df, signal, **kwargs)
        elif transformer_name == "deferred_entry":
            signal = apply_deferred_entry(df, signal, **kwargs)
        else:
            raise ValueError(f"Unknown transformer: {transformer_name}")

    return signal
