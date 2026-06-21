from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_OPERATORS = {"LT", "GT"}


@dataclass
class ExitRule:
    """Configurable exit rule evaluated per-bar during backtest.

    Two comparison modes (mutually exclusive):
    1. ref_col mode: captures `ref_col` value at entry, compares `monitor_col`
       against it each bar using `operator`.
    2. fixed_threshold mode: compares `monitor_col` against a static value.

    Optionally gated by an activation threshold on the captured value and a
    minimum loss requirement.
    """
    name: str = "exit_rule"
    ref_col: str = ""
    monitor_col: str = ""
    operator: str = "LT"
    activation_threshold: float | None = None
    activation_operator: str = "LT"
    min_loss_pct: float | None = None
    skip_col: str | None = None
    fixed_threshold: float | None = None

    def __post_init__(self) -> None:
        """Validate ExitRule configuration."""
        # monitor_col is always required
        if not self.monitor_col:
            raise ValueError(
                f"ExitRule '{self.name}': monitor_col is required"
            )

        # Mutual exclusion: ref_col vs fixed_threshold
        has_ref = bool(self.ref_col)
        has_fixed = self.fixed_threshold is not None

        if has_ref and has_fixed:
            raise ValueError(
                f"ExitRule '{self.name}': cannot set both ref_col and "
                f"fixed_threshold (mutually exclusive)"
            )

        if not has_ref and not has_fixed:
            raise ValueError(
                f"ExitRule '{self.name}': must set either ref_col or "
                f"fixed_threshold (one comparison mode required)"
            )

        # Validate operator
        if self.operator not in SUPPORTED_OPERATORS:
            raise ValueError(
                f"ExitRule '{self.name}': operator must be one of "
                f"{SUPPORTED_OPERATORS}, got '{self.operator}'"
            )

        # Validate activation_operator
        if self.activation_operator not in SUPPORTED_OPERATORS:
            raise ValueError(
                f"ExitRule '{self.name}': activation_operator must be one of "
                f"{SUPPORTED_OPERATORS}, got '{self.activation_operator}'"
            )

        # Validate min_loss_pct is non-negative if set
        if self.min_loss_pct is not None and self.min_loss_pct < 0:
            raise ValueError(
                f"ExitRule '{self.name}': min_loss_pct must be non-negative, "
                f"got {self.min_loss_pct}"
            )

        # Validate activation_threshold is non-negative if set
        if self.activation_threshold is not None and self.activation_threshold < 0:
            raise ValueError(
                f"ExitRule '{self.name}': activation_threshold must be "
                f"non-negative, got {self.activation_threshold}"
            )
