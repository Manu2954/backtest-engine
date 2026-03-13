from __future__ import annotations

import re
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
    "IS_RISING",
    "IS_FALLING",
}

OPERAND_TYPES = {"INDICATOR", "OHLCV", "SCALAR", "LOOKBACK"}


def _parse_lookback(value: str) -> tuple[str, int]:
    """
    Parse LOOKBACK operand format: "column:offset"

    Args:
        value: String in format "column:offset" (e.g., "adx:-3", "close:-26")

    Returns:
        Tuple of (column_name, offset)

    Examples:
        "adx:-3" -> ("adx", -3)  # 3 bars ago
        "close:-26" -> ("close", -26)  # 26 bars ago
        "span_a:+26" -> ("span_a", 26)  # 26 bars ahead (future)

    Raises:
        ValueError: If format is invalid
    """
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid LOOKBACK format: '{value}'. "
            f"Expected 'column:offset' (e.g., 'adx:-3' for 3 bars ago)"
        )

    column_name = parts[0].strip()
    offset_str = parts[1].strip()

    if not column_name:
        raise ValueError(f"Invalid LOOKBACK format: '{value}'. Column name cannot be empty")

    try:
        offset = int(offset_str)
    except ValueError as exc:
        raise ValueError(
            f"Invalid offset in LOOKBACK: '{offset_str}'. Must be an integer"
        ) from exc

    # Validate offset bounds (prevent extreme values that might cause issues)
    if abs(offset) > 1000:
        raise ValueError(
            f"Invalid offset in LOOKBACK: {offset}. "
            f"Offset must be between -1000 and +1000"
        )

    return column_name, offset


def _get_lookback_series(df: pd.DataFrame, value: str) -> pd.Series:
    """
    Get a Series shifted by the specified offset.

    Args:
        df: DataFrame containing the data
        value: LOOKBACK format string "column:offset"

    Returns:
        Shifted Series

    Notes:
        - Negative offset (e.g., -3) means look back 3 bars (shift forward in time)
        - Positive offset (e.g., +3) means look ahead 3 bars (shift backward in time)
        - Pandas shift() convention: shift(1) moves data DOWN (forward in time)
        - So we use shift(-offset) to convert our offset to pandas convention

    Examples:
        If df has index [0, 1, 2, 3, 4] and column "value" = [10, 20, 30, 40, 50]:

        value="value:-1" (1 bar ago):
            shift(-(-1)) = shift(1) = [NaN, 10, 20, 30, 40]
            At index 2, lookback value is 20 (value from index 1)

        value="value:-3" (3 bars ago):
            shift(-(-3)) = shift(3) = [NaN, NaN, NaN, 10, 20]
            At index 4, lookback value is 20 (value from index 1)
    """
    column_name, offset = _parse_lookback(value)

    # Check if column exists
    if column_name not in df.columns:
        raise ValueError(
            f"Column not found in LOOKBACK: '{column_name}'. "
            f"Available columns: {', '.join(df.columns[:10])}..."
            if len(df.columns) > 10
            else f"Available columns: {', '.join(df.columns)}"
        )

    # Get the series
    series = df[column_name]

    # Shift by negative offset to get lookback
    # offset=-3 means "3 bars ago" -> shift(3) moves data down
    shifted = series.shift(-offset)

    # Ensure numeric for comparison
    return pd.to_numeric(shifted, errors="coerce")


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

    if kind == "LOOKBACK":
        return _get_lookback_series(df, value)

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

    # Operators that require Series operands
    if not isinstance(left, pd.Series):
        raise ValueError(f"{operator} requires left operand to be a Series (indicator/OHLCV)")

    if op == "IS_RISING":
        # Current value > previous value
        result = left > left.shift(1)
        if len(result) > 0:
            result.iloc[0] = False
        return result.fillna(False)

    if op == "IS_FALLING":
        # Current value < previous value
        result = left < left.shift(1)
        if len(result) > 0:
            result.iloc[0] = False
        return result.fillna(False)

    if not isinstance(right, pd.Series):
        raise ValueError(f"{operator} requires both operands to be Series")

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
             "left_operand_type": "INDICATOR"|"OHLCV"|"SCALAR"|"LOOKBACK",
             "left_operand_value": "rsi_14"|"close"|"42"|"adx:-3",
             "operator": "CROSSES_ABOVE"|"CROSSES_BELOW"|"GT"|"LT"|"EQ"|"GTE"|"LTE"|"IS_RISING"|"IS_FALLING",
             "right_operand_type": "INDICATOR"|"OHLCV"|"SCALAR"|"LOOKBACK",
             "right_operand_value": "ema_20"|"close"|"70"|"close:-26",
           },
        ]
      }

    Operand Types:
      - INDICATOR: Reference to a computed indicator column (e.g., "rsi_14", "sma_20")
      - OHLCV: Reference to OHLCV data column (e.g., "open", "high", "low", "close", "volume")
      - SCALAR: Constant numeric value (e.g., "50", "0.5", "-10")
      - LOOKBACK: Reference to a column value N bars ago (e.g., "adx:-3", "close:-26")
        Format: "column:offset" where offset is negative for lookback, positive for lookahead

    Operators:
      - GT, LT, EQ, GTE, LTE: Comparison operators (work with any operands)
      - CROSSES_ABOVE, CROSSES_BELOW: Detect crossovers (require two Series operands)
      - IS_RISING: True when left operand > previous value (requires Series, right operand ignored)
      - IS_FALLING: True when left operand < previous value (requires Series, right operand ignored)

    LOOKBACK Examples:
      - Check if ADX is rising over 3 bars:
        {"left": "adx", "operator": "GT", "right_type": "LOOKBACK", "right": "adx:-3"}

      - Check if price is above price from 26 bars ago (Ichimoku Chikou validation):
        {"left": "close", "operator": "GT", "right_type": "LOOKBACK", "right": "close:-26"}

      - Check if RSI crossed above its value from 5 bars ago:
        {"left": "rsi", "operator": "CROSSES_ABOVE", "right_type": "LOOKBACK", "right": "rsi:-5"}
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

        # Check for None instead of truthiness to allow 0, empty string, etc.
        required_fields = [
            ("left_operand_type", left_type),
            ("right_operand_type", right_type),
            ("operator", operator),
            ("left_operand_value", left_value),
            ("right_operand_value", right_value),
        ]
        missing = [name for name, value in required_fields if value is None]
        if missing:
            raise ValueError(f"Condition is missing required fields: {missing}. Condition: {cond}")

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


def evaluate_expression(
    df: pd.DataFrame,
    condition_groups: dict[str, dict[str, Any]],
    expression: str,
) -> pd.Series:
    """
    Evaluate a boolean expression combining multiple condition groups.

    Args:
        df: DataFrame with OHLCV + indicator columns
        condition_groups: Dictionary mapping group names to condition group definitions
        expression: Boolean expression combining groups (e.g., "(A && B) || C")

    Returns:
        Boolean Series indicating when the expression evaluates to True

    Example:
        groups = {
            "oversold": {
                "logic": "AND",
                "conditions": [
                    {"left_operand_type": "INDICATOR", "left_operand_value": "rsi_14",
                     "operator": "LT", "right_operand_type": "SCALAR", "right_operand_value": "30"}
                ]
            },
            "trending": {
                "logic": "AND",
                "conditions": [
                    {"left_operand_type": "INDICATOR", "left_operand_value": "adx_14",
                     "operator": "GT", "right_operand_type": "SCALAR", "right_operand_value": "25"}
                ]
            }
        }

        result = evaluate_expression(df, groups, "oversold && trending")
        # Returns True when RSI < 30 AND ADX > 25

    Supported operators in expression:
        - && or & : AND
        - || or | : OR
        - ! or ~ : NOT
        - () : Grouping

    Expression examples:
        - "A && B" : A AND B
        - "A || B" : A OR B
        - "(A && B) || C" : (A AND B) OR C
        - "A && (B || C)" : A AND (B OR C)
        - "!A && B" : NOT A AND B
        - "(A || B) && (C || D)" : (A OR B) AND (C OR D)
    """
    if df.empty:
        return pd.Series([], dtype=bool, index=df.index)

    if not condition_groups:
        raise ValueError("condition_groups cannot be empty")

    if not expression or not expression.strip():
        raise ValueError("expression cannot be empty")

    # Step 1: Normalize operators (convert && to &, || to |, ! to ~)
    normalized_expr = expression.replace("&&", "&").replace("||", "|").replace("!", "~")

    # Step 2: Validate expression contains only safe characters
    # Allowed: alphanumeric, underscore, operators (&|~), parentheses, whitespace
    if not re.match(r'^[A-Za-z0-9_&|~()\s]+$', normalized_expr):
        raise ValueError(
            f"Invalid characters in expression: '{expression}'. "
            f"Only alphanumeric, _, &&, ||, !, and () are allowed."
        )

    # Step 3: Extract variable names from expression
    var_names = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', normalized_expr)

    # Step 4: Validate all referenced groups exist
    missing = set(var_names) - set(condition_groups.keys())
    if missing:
        raise ValueError(
            f"Expression references undefined condition groups: {sorted(missing)}. "
            f"Available groups: {sorted(condition_groups.keys())}"
        )

    # Step 5: Evaluate each condition group
    evaluated_groups: dict[str, pd.Series] = {}
    for name in var_names:
        if name not in evaluated_groups:  # Avoid re-evaluating same group
            group = condition_groups[name]
            evaluated_groups[name] = evaluate_conditions(df, group)

    # Step 6: Build safe namespace for eval (only the evaluated Series)
    namespace = {name: evaluated_groups[name] for name in var_names}

    # Step 7: Safely evaluate expression
    try:
        result = eval(normalized_expr, {"__builtins__": {}}, namespace)
    except Exception as e:
        raise ValueError(
            f"Failed to evaluate expression: '{expression}'. Error: {e}"
        ) from e

    # Step 8: Validate result is a boolean Series
    if not isinstance(result, pd.Series):
        raise ValueError(
            f"Expression must evaluate to a boolean Series. Got: {type(result)}"
        )

    return result.fillna(False).astype(bool)
