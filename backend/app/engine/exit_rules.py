from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExitRule:
    """Configurable exit rule evaluated per-bar during backtest.

    At entry, captures `ref_col` value. Each bar, checks if `monitor_col`
    crosses the captured ref (per `operator`). Optionally gated by an
    activation threshold on the captured value and a minimum loss requirement.
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
