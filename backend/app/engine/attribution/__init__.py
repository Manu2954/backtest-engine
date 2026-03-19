"""
Trade Attribution Module

Provides signal strength calculation for attributing trade performance
to specific conditions and measuring signal quality.

Phase 1A: Simple confluence-based strength
Phase 1B: Indicator-aware sophisticated calculators
Phase 2+: ML-based or percentile-based calculators

Usage:
    from app.engine.attribution import StrengthCalculatorRegistry

    # Calculate signal strength (uses active calculator)
    strength = StrengthCalculatorRegistry.calculate_strength(
        df, bar_idx, conditions_met, all_conditions
    )

    # Switch calculators (Phase 1A → Phase 1B)
    StrengthCalculatorRegistry.set_active('indicator_aware')
"""

from .calculators.confluence import ConfluenceStrengthCalculator
from .strength_calculator import (
    SignalStrengthCalculator,
    StrengthCalculatorRegistry,
    calculate_market_return,
    get_indicator_snapshot,
    get_indicators_used_in_conditions,
)

# Register Phase 1A calculator
StrengthCalculatorRegistry.register('confluence', ConfluenceStrengthCalculator())

# Set Phase 1A as active (will be changed to 'indicator_aware' in Phase 1B)
StrengthCalculatorRegistry.set_active('confluence')

__all__ = [
    'SignalStrengthCalculator',
    'StrengthCalculatorRegistry',
    'ConfluenceStrengthCalculator',
    'get_indicators_used_in_conditions',
    'get_indicator_snapshot',
    'calculate_market_return',
]
