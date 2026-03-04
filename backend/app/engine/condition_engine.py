from __future__ import annotations

from typing import Any

import pandas as pd

OPERATORS = {
    "CROSSES_ABOVE",
    "CROSSES_BELOW",
    "GT",
    "LT",
    "EQ",
    "GTE",
    "LTE",
}

OPERAND_TYPES = {"INDICATOR", "OHLCV", "SCALAR"}


def _get_operand_series(df: pd.DataFrame, operand_type: str, value: str) -> pd.Series:
    kind = operand_type.upper()
    if kind == "SCALAR":
        raise ValueError("SCALAR operands must be handled separately")

    if kind == "OHLCV":
        col = value.lower()
    else:
        col = value

    if col not in df.columns:
        raise ValueError(f"Operand column not found: {value}")

    series = df[col]
    # Ensure numeric comparison behavior (convert None/object to NaN)
    return pd.to_numeric(series, errors="coerce")


def _get_operand(
    df: pd.DataFrame, operand_type: str, value: str
) -> pd.Series | float:
    kind = operand_type.upper()
    if kind not in OPERAND_TYPES:
        raise ValueError(f"Unsupported operand type: {operand_type}")

    if kind == "SCALAR":
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"Invalid scalar value: {value}") from exc

    return _get_operand_series(df, kind, value)


def _apply_operator(
    left: pd.Series | float, right: pd.Series | float, operator: str
) -> pd.Series:
    op = operator.upper()
    if op not in OPERATORS:
        raise ValueError(f"Unsupported operator: {operator}")

    if op == "GT":
        return left > right
    if op == "LT":
        return left < right
    if op == "EQ":
        return left == right
    if op == "GTE":
        return left >= right
    if op == "LTE":
        return left <= right

    if not isinstance(left, pd.Series) or not isinstance(right, pd.Series):
        raise ValueError(f"{operator} requires Series operands")

    if op == "CROSSES_ABOVE":
        prev = (left.shift(1) < right.shift(1))
        now = (left > right)
        result = prev & now
    else:  # CROSSES_BELOW
        prev = (left.shift(1) > right.shift(1))
        now = (left < right)
        result = prev & now

    if len(result) > 0:
        result.iloc[0] = False
    return result.fillna(False)


def evaluate_conditions(df: pd.DataFrame, condition_group: dict[str, Any]) -> pd.Series:
    """
    Evaluate a condition group against a DataFrame of OHLCV + indicator columns.

    condition_group:
      {
        "logic": "AND"|"OR",
        "conditions": [
           {
             "left_operand_type": "INDICATOR"|"OHLCV"|"SCALAR",
             "left_operand_value": "rsi_14"|"close"|"42",
             "operator": "CROSSES_ABOVE"|"CROSSES_BELOW"|"GT"|"LT"|"EQ"|"GTE"|"LTE",
             "right_operand_type": "INDICATOR"|"OHLCV"|"SCALAR",
             "right_operand_value": "ema_20"|"close"|"70",
           },
        ]
      }
    """
    if df.empty:
        return pd.Series([], dtype=bool, index=df.index)

    logic = str(condition_group.get("logic", "AND")).upper()
    conditions = condition_group.get("conditions", []) or []

    if not conditions:
        return pd.Series([False] * len(df), index=df.index, dtype=bool)

    results: list[pd.Series] = []
    for cond in conditions:
        left_type = cond.get("left_operand_type")
        right_type = cond.get("right_operand_type")
        operator = cond.get("operator")
        left_value = cond.get("left_operand_value")
        right_value = cond.get("right_operand_value")

        if not all([left_type, right_type, operator, left_value, right_value]):
            raise ValueError(f"Condition is missing required fields: {cond}")

        left = _get_operand(df, left_type, str(left_value))
        right = _get_operand(df, right_type, str(right_value))
        result = _apply_operator(left, right, str(operator))

        if not isinstance(result, pd.Series):
            raise ValueError("Condition evaluation must return a Series")

        results.append(result.fillna(False))

    if logic == "OR":
        combined = results[0].copy()
        for series in results[1:]:
            combined = combined | series
        return combined.fillna(False)

    if logic != "AND":
        raise ValueError(f"Unsupported condition group logic: {logic}")

    combined = results[0].copy()
    for series in results[1:]:
        combined = combined & series
    return combined.fillna(False)
