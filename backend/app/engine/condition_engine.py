from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

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

OPERAND_TYPES = {"INDICATOR", "OHLCV", "SCALAR", "LOOKBACK", "EXPRESSION"}


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
        "rsi:-1" -> ("rsi", -1)  # Previous bar

    Note:
        Only negative offsets (lookback) are allowed. Positive offsets would
        access future data, creating lookahead bias that invalidates backtests.

    Raises:
        ValueError: If format is invalid or offset is positive (lookahead)
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
            f"Offset must be between -1000 and 0"
        )

    # Block positive offsets (lookahead bias)
    if offset > 0:
        raise ValueError(
            f"Invalid offset in LOOKBACK: +{offset}. "
            f"Positive offsets access future data (lookahead bias). "
            f"Use negative offsets only (e.g., 'close:-3' for 3 bars ago)."
        )

    return column_name, offset


def _get_lookback_series(df: pd.DataFrame, value: str) -> pd.Series:
    """
    Get a Series shifted by the specified offset (lookback only).

    Args:
        df: DataFrame containing the data
        value: LOOKBACK format string "column:offset" (offset must be <= 0)

    Returns:
        Shifted Series representing historical values

    Notes:
        - Negative offset (e.g., -3) means look back 3 bars
        - Zero offset returns the current value (no shift)
        - Positive offsets are rejected by _parse_lookback() to prevent lookahead bias
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

    # Check if column exists, with multi-column indicator mapping
    if column_name not in df.columns:
        # Handle multi-column indicators by mapping base alias to primary sub-column
        mapped_col = None

        # Try MACD mapping
        if f"{column_name}_macd" in df.columns:
            mapped_col = f"{column_name}_macd"
        # Try BB mapping
        elif f"{column_name}_mid" in df.columns:
            mapped_col = f"{column_name}_mid"
        # Try STOCH mapping
        elif f"{column_name}_k" in df.columns:
            mapped_col = f"{column_name}_k"
        # Try ICHIMOKU mapping
        elif f"{column_name}_tenkan" in df.columns:
            mapped_col = f"{column_name}_tenkan"

        if mapped_col:
            column_name = mapped_col
        else:
            available = ', '.join(df.columns[:10]) + "..." if len(df.columns) > 10 else ', '.join(df.columns)
            raise ValueError(
                f"Column not found in LOOKBACK: '{column_name}'. "
                f"Available columns: {available}"
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
        # Handle multi-column indicators by mapping base alias to primary sub-column
        # MACD: base_alias -> base_alias_macd
        # BB: base_alias -> base_alias_mid
        # STOCH: base_alias -> base_alias_k
        # ICHIMOKU: base_alias -> base_alias_tenkan
        # ADX creates base alias directly, so no mapping needed

        mapped_col = None

        # Try MACD mapping
        if f"{col}_macd" in df.columns:
            mapped_col = f"{col}_macd"
        # Try BB mapping
        elif f"{col}_mid" in df.columns:
            mapped_col = f"{col}_mid"
        # Try STOCH mapping
        elif f"{col}_k" in df.columns:
            mapped_col = f"{col}_k"
        # Try ICHIMOKU mapping
        elif f"{col}_tenkan" in df.columns:
            mapped_col = f"{col}_tenkan"

        if mapped_col:
            col = mapped_col
        else:
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

    if kind == "EXPRESSION":
        return _evaluate_expression(df, value)

    return _get_operand_series(df, kind, value)


def _tokenize_expression(expression: str) -> list[str]:
    """Tokenize an arithmetic expression into operands and operators."""
    tokens = []
    # Match: lookback refs (word:number), numbers (with decimals), column names, operators
    pattern = r'(\w+:-?\d+|\d*\.\d+|\d+|\w+|[+\-*/()])'
    raw_tokens = re.findall(pattern, expression)
    if not raw_tokens:
        raise ValueError(f"Invalid expression: '{expression}'")

    # Handle unary minus: if '-' appears at start or after an operator/open-paren,
    # merge it with the next token as a negative number
    i = 0
    while i < len(raw_tokens):
        token = raw_tokens[i]
        if token == '-' and (i == 0 or raw_tokens[i - 1] in ('+', '-', '*', '/', '(')):
            if i + 1 < len(raw_tokens) and re.match(r'^\d+\.?\d*$', raw_tokens[i + 1]):
                tokens.append(f"-{raw_tokens[i + 1]}")
                i += 2
                continue
        tokens.append(token)
        i += 1

    return tokens


def _resolve_expr_token(df: pd.DataFrame, token: str) -> pd.Series | float:
    """Resolve a single expression token to a Series or float."""
    # Numeric literal (integers, decimals, negative numbers)
    if re.match(r'^-?(\d+\.?\d*|\d*\.\d+)$', token):
        return float(token)
    # Lookback reference (contains colon with integer offset)
    if re.match(r'^\w+:-?\d+$', token):
        return _get_lookback_series(df, token)
    # Column name (indicator or OHLCV)
    return _get_operand_series(df, "INDICATOR", token)


def _evaluate_expression(df: pd.DataFrame, expression: str) -> pd.Series | float:
    """
    Evaluate arithmetic expression with standard operator precedence.

    Supports +, -, *, / on column references, lookback refs, and numeric literals.
    Examples: "close:-12 * 0.98", "sma_200 + atr_14 * 2", "vol_sma_20 * 2.0"
    """
    tokens = _tokenize_expression(expression)

    # Shunting-yard for operator precedence
    precedence = {'+': 1, '-': 1, '*': 2, '/': 2}
    output_queue: list = []
    operator_stack: list[str] = []

    for token in tokens:
        if token in precedence:
            while (operator_stack and operator_stack[-1] in precedence
                   and precedence[operator_stack[-1]] >= precedence[token]):
                output_queue.append(operator_stack.pop())
            operator_stack.append(token)
        elif token == '(':
            operator_stack.append(token)
        elif token == ')':
            while operator_stack and operator_stack[-1] != '(':
                output_queue.append(operator_stack.pop())
            if not operator_stack:
                raise ValueError(f"Mismatched parentheses in expression: '{expression}'")
            operator_stack.pop()  # Remove '('
        else:
            output_queue.append(_resolve_expr_token(df, token))

    while operator_stack:
        op = operator_stack.pop()
        if op in ('(', ')'):
            raise ValueError(f"Mismatched parentheses in expression: '{expression}'")
        output_queue.append(op)

    # Evaluate RPN
    eval_stack: list = []
    for item in output_queue:
        if isinstance(item, str) and item in precedence:
            if len(eval_stack) < 2:
                raise ValueError(f"Invalid expression: '{expression}'")
            right_val = eval_stack.pop()
            left_val = eval_stack.pop()
            if item == '+':
                eval_stack.append(left_val + right_val)
            elif item == '-':
                eval_stack.append(left_val - right_val)
            elif item == '*':
                eval_stack.append(left_val * right_val)
            elif item == '/':
                eval_stack.append(left_val / right_val)
        else:
            eval_stack.append(item)

    if len(eval_stack) != 1:
        raise ValueError(f"Invalid expression: '{expression}'")

    return eval_stack[0]


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
        # Cross above: was below or equal (<=), now is above (>)
        # Requires two consecutive bars to detect transition
        prev_not_above = left.shift(1) <= right.shift(1)
        now_above = left > right
        result = prev_not_above & now_above
    else:  # CROSSES_BELOW
        # Cross below: was above or equal (>=), now is below (<)
        prev_not_below = left.shift(1) >= right.shift(1)
        now_below = left < right
        result = prev_not_below & now_below

    # First bar cannot be a crossover - requires prior bar for comparison
    # NaN from shift propagates correctly (NaN & True = NaN -> fillna(False))
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


def evaluate_conditions_with_attribution(
    df: pd.DataFrame,
    condition_group: dict[str, Any],
    bar_idx: int,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Evaluate conditions at a specific bar and return attribution data.

    This is the attribution-aware version of evaluate_conditions().
    It evaluates conditions at a specific bar and tracks which conditions
    triggered, plus calculates signal strength.

    Args:
        df: DataFrame with OHLCV + indicator columns
        condition_group: Condition group definition (same format as evaluate_conditions)
        bar_idx: Specific bar index to evaluate
        context: Optional context (timeframe, strategy config) for strength calculation

    Returns:
        Tuple of (triggered, attribution_data):
        - triggered: bool - True if conditions met at this bar
        - attribution_data: dict or None - Attribution data if triggered, else None
            {
                'conditions_met': [list of condition dicts that were true],
                'all_conditions': [list of all condition dicts],
                'signal_strength': float (0-1)
            }

    Example:
        triggered, attr = evaluate_conditions_with_attribution(df, entry_group, 100)
        if triggered:
            print(f"Strength: {attr['signal_strength']}")
            print(f"Conditions met: {len(attr['conditions_met'])}/{len(attr['all_conditions'])}")
    """
    # Evaluate all conditions as boolean Series
    result_series = evaluate_conditions(df, condition_group)

    # Check if triggered at this specific bar
    if bar_idx < 0 or bar_idx >= len(result_series):
        return False, None

    triggered = bool(result_series.iloc[bar_idx])

    if not triggered:
        return False, None

    # Attribution data - track which conditions were true
    logic = str(condition_group.get("logic", "AND")).upper()
    conditions = condition_group.get("conditions", []) or []

    if not conditions:
        return False, None

    # Evaluate each condition individually at this bar
    conditions_met = []
    all_conditions = []

    for cond in conditions:
        # Store condition reference
        all_conditions.append(cond)

        # Evaluate this single condition at the bar
        left_type = cond.get("left_operand_type")
        right_type = cond.get("right_operand_type")
        operator = cond.get("operator")
        left_value = cond.get("left_operand_value")
        right_value = cond.get("right_operand_value")

        try:
            left = _get_operand(df, left_type, str(left_value))
            right = _get_operand(df, right_type, str(right_value))
            cond_result = _apply_operator(left, right, str(operator))

            # Check if this condition was true at bar_idx
            if isinstance(cond_result, pd.Series) and 0 <= bar_idx < len(cond_result):
                if cond_result.iloc[bar_idx]:
                    conditions_met.append(cond)
        except Exception:
            # If condition evaluation fails, skip it
            continue

    # Calculate signal strength using the attribution module
    try:
        from app.engine.attribution import (
            StrengthCalculatorRegistry,
            get_indicators_used_in_conditions,
            get_indicator_snapshot,
        )

        signal_strength = StrengthCalculatorRegistry.calculate_strength(
            df=df,
            bar_idx=bar_idx,
            conditions_met=conditions_met,
            all_conditions=all_conditions,
            context=context
        )

        # Get indicator snapshot at this bar
        indicators_used = get_indicators_used_in_conditions(all_conditions)
        indicator_snapshot = get_indicator_snapshot(df, bar_idx, indicators_used)
    except Exception:
        # Fallback if attribution module not available
        signal_strength = len(conditions_met) / len(all_conditions) if all_conditions else 0.5
        indicator_snapshot = {}

    attribution_data = {
        'conditions_met': conditions_met,
        'all_conditions': all_conditions,
        'signal_strength': signal_strength,
        'indicator_snapshot': indicator_snapshot,
    }

    return triggered, attribution_data
