"""
Signal Strength Calculator - Pluggable Architecture

This module provides the abstract base class and registry for signal strength
calculation. Different calculators can be plugged in for different phases:

Phase 1A: ConfluenceStrengthCalculator (simple)
Phase 1B: Indicator-aware calculators (sophisticated)
Phase 2+: ML-based or percentile-based calculators

The state machine doesn't need to change - it just calls the registry.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import pandas as pd


class SignalStrengthCalculator(ABC):
    """
    Abstract base class for signal strength calculators.

    All calculators must implement the calculate() method which returns
    a strength score between 0.0 and 1.0.
    """

    @abstractmethod
    def calculate(
        self,
        df: pd.DataFrame,
        bar_idx: int,
        conditions_met: List[Dict[str, Any]],
        all_conditions: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate signal strength score.

        Args:
            df: Full DataFrame with OHLCV + indicators
            bar_idx: Current bar index where signal triggered
            conditions_met: List of conditions that were true
                Format: [{'id': uuid, 'type': 'GT', 'left_operand': 'rsi_14', ...}, ...]
            all_conditions: List of all conditions in the group
            context: Optional context (timeframe, strategy config, etc.)

        Returns:
            float: Strength score between 0.0 and 1.0
        """
        pass


class StrengthCalculatorRegistry:
    """
    Registry for strength calculators.

    Allows plugging in different calculators for different phases
    without modifying the state machine.
    """

    _calculators: Dict[str, SignalStrengthCalculator] = {}
    _active_calculator: str = "confluence"  # Default to Phase 1A

    @classmethod
    def register(cls, name: str, calculator: SignalStrengthCalculator):
        """Register a calculator with a name."""
        cls._calculators[name] = calculator

    @classmethod
    def set_active(cls, name: str):
        """Set the active calculator."""
        if name not in cls._calculators:
            raise ValueError(f"Calculator '{name}' not registered")
        cls._active_calculator = name

    @classmethod
    def get_active(cls) -> SignalStrengthCalculator:
        """Get the currently active calculator."""
        if cls._active_calculator not in cls._calculators:
            raise ValueError(f"Active calculator '{cls._active_calculator}' not found")
        return cls._calculators[cls._active_calculator]

    @classmethod
    def calculate_strength(
        cls,
        df: pd.DataFrame,
        bar_idx: int,
        conditions_met: List[Dict[str, Any]],
        all_conditions: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate signal strength using the active calculator.

        This is the main entry point called by the state machine.
        The calculator can be swapped out without changing this interface.
        """
        calculator = cls.get_active()
        return calculator.calculate(df, bar_idx, conditions_met, all_conditions, context)


def get_indicators_used_in_conditions(conditions: List[Dict[str, Any]]) -> set:
    """
    Extract indicator aliases used in conditions.

    Parses left_operand and right_operand of each condition to find
    which indicators are referenced. Used for indicator snapshots.

    Args:
        conditions: List of condition dicts with operands

    Returns:
        set: Set of indicator aliases (e.g., {'rsi_14', 'sma_50'})
    """
    indicators = set()

    for condition in conditions:
        # Check left operand
        if condition.get('left_operand_type') == 'INDICATOR':
            indicators.add(condition['left_operand_value'])

        # Check right operand
        if condition.get('right_operand_type') == 'INDICATOR':
            indicators.add(condition['right_operand_value'])

    return indicators


def get_indicator_snapshot(
    df: pd.DataFrame,
    bar_idx: int,
    indicator_aliases: set
) -> Dict[str, float]:
    """
    Get indicator values at a specific bar.

    Args:
        df: DataFrame with indicator columns
        bar_idx: Index of the bar (integer position, not datetime)
        indicator_aliases: Set of indicator aliases to snapshot

    Returns:
        dict: {alias: value} for each indicator
    """
    if bar_idx < 0 or bar_idx >= len(df):
        return {}

    snapshot = {}

    for alias in indicator_aliases:
        if alias in df.columns:
            value = df.iloc[bar_idx][alias]
            # Convert numpy types to Python types for JSON serialization
            if pd.notna(value):
                snapshot[alias] = float(value)
            else:
                snapshot[alias] = None

    return snapshot


def calculate_market_return(
    df: pd.DataFrame,
    entry_idx: int,
    exit_idx: int,
    direction: str
) -> float:
    """
    Calculate close-to-close market return during trade period.

    This represents what you would have made just buying and holding
    (or shorting and holding) during the trade period.

    Args:
        df: DataFrame with 'close' column
        entry_idx: Entry bar index (integer position, not datetime)
        exit_idx: Exit bar index (integer position, not datetime)
        direction: 'LONG' or 'SHORT'

    Returns:
        float: Market return as percentage (5.0 = 5%)
    """
    if entry_idx < 0 or entry_idx >= len(df):
        return 0.0
    if exit_idx < 0 or exit_idx >= len(df):
        return 0.0

    entry_close = df.iloc[entry_idx]['close']
    exit_close = df.iloc[exit_idx]['close']

    if entry_close <= 0:
        return 0.0

    if direction == 'LONG':
        # Long: profit when price goes up
        return ((exit_close - entry_close) / entry_close) * 100.0
    elif direction == 'SHORT':
        # Short: profit when price goes down
        return ((entry_close - exit_close) / entry_close) * 100.0
    else:
        # Default to LONG if invalid direction
        return ((exit_close - entry_close) / entry_close) * 100.0
