"""
Tests for signal_transformers.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.signal_transformers import (
    apply_counter_trade_signals,
    apply_deferred_entry,
    apply_regime_filter,
    chain_transformers,
)


def test_apply_deferred_entry_basic():
    """Deferred entry waits for confirmation condition."""
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "close": [100, 98, 96, 94, 105, 110, 115, 120, 125, 130],
            "sma_50": [100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
        },
        index=index,
    )

    # Entry signal at bar 1, confirmation (close > sma) not until bar 4
    entry_signal = pd.Series([False, True, False, False, False, False, False, False, False, False], index=index)
    df["confirmation"] = df["close"] > df["sma_50"]

    deferred = apply_deferred_entry(df, entry_signal, "confirmation")

    # Signal at bar 1 arms (98 < 100, not confirmed)
    # Bar 2, 3: still waiting (96, 94 < 100)
    # Bar 4: 105 > 100, fires!
    assert not deferred.iloc[1]  # Armed but not confirmed
    assert not deferred.iloc[2]  # Still waiting
    assert not deferred.iloc[3]  # Still waiting
    assert deferred.iloc[4]  # Confirmation met!
    assert deferred.sum() == 1  # Only one entry


def test_apply_deferred_entry_immediate_confirmation():
    """Deferred entry fires immediately if already confirmed."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "close": [110, 115, 120, 125, 130],
            "sma_50": [100, 100, 100, 100, 100],
        },
        index=index,
    )

    entry_signal = pd.Series([False, True, False, False, False], index=index)
    df["confirmation"] = df["close"] > df["sma_50"]  # Always true

    deferred = apply_deferred_entry(df, entry_signal, "confirmation")

    # Should fire at bar 1 (same bar as signal since already confirmed)
    assert deferred.iloc[1]
    assert deferred.sum() == 1


def test_apply_deferred_entry_never_confirms():
    """Deferred entry never fires if confirmation never happens."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "close": [95, 90, 85, 80, 75],
            "sma_50": [100, 100, 100, 100, 100],
        },
        index=index,
    )

    entry_signal = pd.Series([False, True, False, False, False], index=index)
    df["confirmation"] = df["close"] > df["sma_50"]  # Always false

    deferred = apply_deferred_entry(df, entry_signal, "confirmation")

    # Should never fire
    assert deferred.sum() == 0


def test_apply_regime_filter_allows_only_specified_regimes():
    """Regime filter blocks entries in excluded regimes."""
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "close": [100] * 10,
            "regime": ["BULL", "BULL", "RANGING", "RANGING", "BEAR", "BEAR", "BULL", "CHOPPY", "BULL", "RANGING"],
        },
        index=index,
    )

    # Entry signals every bar
    entry_signal = pd.Series([True] * 10, index=index)

    # Only allow BULL and BEAR
    filtered = apply_regime_filter(df, entry_signal, "regime", ["BULL", "BEAR"])

    # Should only have True at bars 0,1,4,5,6,8 (BULL or BEAR)
    assert filtered.iloc[0]  # BULL
    assert filtered.iloc[1]  # BULL
    assert not filtered.iloc[2]  # RANGING (blocked)
    assert not filtered.iloc[3]  # RANGING (blocked)
    assert filtered.iloc[4]  # BEAR
    assert filtered.iloc[5]  # BEAR
    assert filtered.iloc[6]  # BULL
    assert not filtered.iloc[7]  # CHOPPY (blocked)
    assert filtered.iloc[8]  # BULL
    assert not filtered.iloc[9]  # RANGING (blocked)
    assert filtered.sum() == 6


def test_apply_regime_filter_empty_allowed_list():
    """Regime filter with empty allowed list blocks all entries."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "close": [100] * 5,
            "regime": ["BULL", "BEAR", "RANGING", "CHOPPY", "BULL"],
        },
        index=index,
    )

    entry_signal = pd.Series([True] * 5, index=index)

    filtered = apply_regime_filter(df, entry_signal, "regime", [])

    # Nothing allowed
    assert filtered.sum() == 0


def test_apply_regime_filter_all_regimes_allowed():
    """Regime filter with all regimes allowed passes everything through."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "close": [100] * 5,
            "regime": ["BULL", "BEAR", "RANGING", "CHOPPY", "BULL"],
        },
        index=index,
    )

    entry_signal = pd.Series([True] * 5, index=index)

    filtered = apply_regime_filter(df, entry_signal, "regime", ["BULL", "BEAR", "RANGING", "CHOPPY"])

    # All allowed
    assert filtered.sum() == 5


def test_chain_transformers_regime_then_deferred():
    """Chain regime filter followed by deferred entry."""
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "close": [95, 96, 97, 98, 105, 110, 115, 120, 125, 130],
            "sma_50": [100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
            "regime": ["RANGING", "RANGING", "BULL", "BULL", "BULL", "BULL", "RANGING", "BULL", "BULL", "BULL"],
        },
        index=index,
    )

    # Entry signal at bar 2 (BULL regime)
    entry_signal = pd.Series([False, False, True, False, False, False, False, False, False, False], index=index)
    df["confirmation"] = df["close"] > df["sma_50"]  # True from bar 4 onward

    transformers = [
        ("regime_filter", {"regime_column": "regime", "allowed_regimes": ["BULL", "BEAR"]}),
        ("deferred_entry", {"confirmation_column": "confirmation"}),
    ]

    final_signal = chain_transformers(df, entry_signal, transformers)

    # Bar 2: BULL (passes regime filter), arms deferred
    # Bar 3: confirmation still false
    # Bar 4: confirmation true, fires entry
    assert not final_signal.iloc[2]  # Armed but not confirmed
    assert not final_signal.iloc[3]  # Still waiting
    assert final_signal.iloc[4]  # Fires!
    assert final_signal.sum() == 1


def test_chain_transformers_deferred_then_regime():
    """Chain deferred entry followed by regime filter."""
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "close": [95, 96, 105, 110, 115, 120, 125, 130, 135, 140],
            "sma_50": [100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
            "regime": ["BULL", "BULL", "BULL", "RANGING", "RANGING", "BULL", "BULL", "BULL", "BULL", "BULL"],
        },
        index=index,
    )

    # Entry signal at bar 1
    entry_signal = pd.Series([False, True, False, False, False, False, False, False, False, False], index=index)
    df["confirmation"] = df["close"] > df["sma_50"]  # True from bar 2 onward

    transformers = [
        ("deferred_entry", {"confirmation_column": "confirmation"}),
        ("regime_filter", {"regime_column": "regime", "allowed_regimes": ["BULL", "BEAR"]}),
    ]

    final_signal = chain_transformers(df, entry_signal, transformers)

    # Bar 1: arms deferred
    # Bar 2: confirmation true, deferred fires → then regime filter checks bar 2 = BULL (passes)
    assert final_signal.iloc[2]
    assert final_signal.sum() == 1


def test_apply_counter_trade_signals_long_loss():
    """Counter-trade signals inject SHORT after LONG loss."""
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 100, 90, 90, 85, 85, 85, 85, 85],
            "close": [100, 100, 100, 90, 90, 85, 85, 85, 85, 85],
        },
        index=index,
    )

    # LONG: signal at bar 1, exit at bar 3
    long_entry = pd.Series([False, True, False, False, False, False, False, False, False, False], index=index)
    long_exit = pd.Series([False, False, False, True, False, False, False, False, False, False], index=index)
    short_entry = pd.Series([False] * 10, index=index)
    short_exit = pd.Series([False] * 10, index=index)

    long_e, long_x, short_e, short_x = apply_counter_trade_signals(
        df, long_entry, long_exit, short_entry, short_exit
    )

    # Original signals preserved
    assert long_e.iloc[1]
    assert long_x.iloc[3]

    # SHORT entry injected after LONG loss
    # Exit fills at bar 4, counter-trade enters at bar 5
    assert short_e.iloc[4]  # Counter-trade SHORT entry


def test_apply_counter_trade_signals_short_loss():
    """Counter-trade signals inject LONG after SHORT loss."""
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 100, 110, 110, 115, 115, 115, 115, 115],
            "close": [100, 100, 100, 110, 110, 115, 115, 115, 115, 115],
        },
        index=index,
    )

    # SHORT: signal at bar 1, exit at bar 3
    long_entry = pd.Series([False] * 10, index=index)
    long_exit = pd.Series([False] * 10, index=index)
    short_entry = pd.Series([False, True, False, False, False, False, False, False, False, False], index=index)
    short_exit = pd.Series([False, False, False, True, False, False, False, False, False, False], index=index)

    long_e, long_x, short_e, short_x = apply_counter_trade_signals(
        df, long_entry, long_exit, short_entry, short_exit
    )

    # Original signals preserved
    assert short_e.iloc[1]
    assert short_x.iloc[3]

    # LONG entry injected after SHORT loss
    assert long_e.iloc[4]  # Counter-trade LONG entry


def test_apply_counter_trade_signals_no_injection_on_profit():
    """Counter-trade does not inject signals when trade is profitable."""
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 100, 110, 110, 115, 115, 115, 115, 115],
            "close": [100, 100, 100, 110, 110, 115, 115, 115, 115, 115],
        },
        index=index,
    )

    # LONG: signal at bar 1, exit at bar 3 (profit)
    long_entry = pd.Series([False, True, False, False, False, False, False, False, False, False], index=index)
    long_exit = pd.Series([False, False, False, True, False, False, False, False, False, False], index=index)
    short_entry = pd.Series([False] * 10, index=index)
    short_exit = pd.Series([False] * 10, index=index)

    long_e, long_x, short_e, short_x = apply_counter_trade_signals(
        df, long_entry, long_exit, short_entry, short_exit
    )

    # Original signals preserved
    assert long_e.iloc[1]
    assert long_x.iloc[3]

    # No counter-trade (profitable)
    assert short_e.sum() == 0


def test_apply_deferred_entry_missing_column():
    """Deferred entry raises error if confirmation column missing."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame({"close": [100, 105, 110, 115, 120]}, index=index)
    entry_signal = pd.Series([True] * 5, index=index)

    with pytest.raises(ValueError, match="Confirmation column .* not found"):
        apply_deferred_entry(df, entry_signal, "nonexistent_column")


def test_apply_regime_filter_missing_column():
    """Regime filter raises error if regime column missing."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame({"close": [100, 105, 110, 115, 120]}, index=index)
    entry_signal = pd.Series([True] * 5, index=index)

    with pytest.raises(ValueError, match="Regime column .* not found"):
        apply_regime_filter(df, entry_signal, "nonexistent_column", ["BULL"])


def test_chain_transformers_unknown_transformer():
    """Chain transformers raises error for unknown transformer."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame({"close": [100, 105, 110, 115, 120]}, index=index)
    entry_signal = pd.Series([True] * 5, index=index)

    transformers = [("unknown_transformer", {})]

    with pytest.raises(ValueError, match="Unknown transformer"):
        chain_transformers(df, entry_signal, transformers)
