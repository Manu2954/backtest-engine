"""
Confluence Strength Calculator - Phase 1A

Simple signal strength calculation based on confluence:
How many conditions were met vs total conditions.

Formula: strength = len(conditions_met) / len(all_conditions)

This is the Phase 1A implementation. It will be replaced/augmented
in Phase 1B with indicator-aware calculators, but the interface remains
the same (pluggable architecture).
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from ..strength_calculator import SignalStrengthCalculator


class ConfluenceStrengthCalculator(SignalStrengthCalculator):
    """
    Phase 1A: Simple confluence-based strength calculation.

    Strength = (number of conditions met) / (total conditions)

    Examples:
    - 3/3 conditions met → strength = 1.0 (all conditions fired)
    - 2/4 conditions met → strength = 0.5 (half conditions fired)
    - 1/5 conditions met → strength = 0.2 (weak signal, only one condition)
    """

    def calculate(
        self,
        df: pd.DataFrame,
        bar_idx: int,
        conditions_met: List[Dict[str, Any]],
        all_conditions: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate signal strength based on confluence.

        Args:
            df: Not used in Phase 1A (but required by interface)
            bar_idx: Not used in Phase 1A
            conditions_met: Conditions that were true
            all_conditions: All conditions in the group
            context: Not used in Phase 1A

        Returns:
            float: Confluence score (0.0 to 1.0)
        """
        if len(all_conditions) == 0:
            return 0.5  # Neutral if no conditions (shouldn't happen)

        # Simple ratio
        confluence = len(conditions_met) / len(all_conditions)

        # Ensure bounds [0.0, 1.0]
        return max(0.0, min(1.0, confluence))
