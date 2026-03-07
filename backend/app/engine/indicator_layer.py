from __future__ import annotations

from typing import Any

import pandas as pd
import pandas_ta as ta

REQUIRED_OHLCV_COLUMNS = ("open", "high", "low", "close", "volume")


def _require_param(params: dict[str, Any], key: str) -> Any:
    if key not in params:
        raise ValueError(f"Missing required param: {key}")
    return params[key]


def _get_series(df: pd.DataFrame, source: str) -> pd.Series:
    source_key = source.lower()
    if source_key not in df.columns:
        raise ValueError(f"Source column not found: {source}")
    return df[source_key]


def _ensure_ohlcv(df: pd.DataFrame) -> None:
    missing = set(REQUIRED_OHLCV_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")


def _pick_first_col(frame: pd.DataFrame, prefix: str) -> pd.Series:
    matches = [col for col in frame.columns if str(col).startswith(prefix)]
    if not matches:
        raise ValueError(f"Expected column with prefix '{prefix}' not found")
    return frame[matches[0]]


def compute_indicators(df: pd.DataFrame, indicators: list[dict[str, Any]]) -> pd.DataFrame:
    """
    Compute indicators using pandas-ta and append them to the DataFrame.

    Expected indicator definition shape:
      {
        "indicator_type": "RSI"|"EMA"|"SMA"|"MACD"|"BB"|"ATR"|"STOCH",
        "alias": "rsi_14",
        "params": {...}
      }
    """
    if df.empty or not indicators:
        return df

    df_out = df.copy()
    _ensure_ohlcv(df_out)

    # Track all indicator column names for warmup detection
    indicator_columns = []

    for indicator in indicators:
        indicator_type = indicator.get("indicator_type") or indicator.get("type")
        alias = indicator.get("alias")
        params = indicator.get("params", {}) or {}

        if not indicator_type:
            raise ValueError("Indicator type is required")
        if not alias:
            raise ValueError("Indicator alias is required")

        kind = str(indicator_type).upper()
        source = params.get("source", "close")

        if kind == "RSI":
            period = int(_require_param(params, "period"))
            series = _get_series(df_out, source)
            df_out[alias] = ta.rsi(series, length=period)
            indicator_columns.append(alias)
        elif kind == "EMA":
            period = int(_require_param(params, "period"))
            series = _get_series(df_out, source)
            df_out[alias] = ta.ema(series, length=period)
            indicator_columns.append(alias)
        elif kind == "SMA":
            period = int(_require_param(params, "period"))
            series = _get_series(df_out, source)
            df_out[alias] = ta.sma(series, length=period)
            indicator_columns.append(alias)
        elif kind == "MACD":
            fast = int(_require_param(params, "fast"))
            slow = int(_require_param(params, "slow"))
            signal = int(_require_param(params, "signal"))
            series = _get_series(df_out, source)
            macd_df = ta.macd(series, fast=fast, slow=slow, signal=signal)
            if macd_df is None or macd_df.empty:
                raise ValueError("MACD computation returned empty data")
            df_out[f"{alias}_macd"] = macd_df.iloc[:, 0]
            df_out[f"{alias}_signal"] = macd_df.iloc[:, 1]
            df_out[f"{alias}_hist"] = macd_df.iloc[:, 2]
            indicator_columns.extend([f"{alias}_macd", f"{alias}_signal", f"{alias}_hist"])
        elif kind in {"BB", "BBANDS", "BOLLINGER"}:
            length = int(_require_param(params, "period"))
            std = float(_require_param(params, "std_dev"))
            series = _get_series(df_out, source)
            bb_df = ta.bbands(series, length=length, std=std)
            if bb_df is None or bb_df.empty:
                raise ValueError("Bollinger Bands computation returned empty data")
            df_out[f"{alias}_upper"] = _pick_first_col(bb_df, "BBU")
            df_out[f"{alias}_mid"] = _pick_first_col(bb_df, "BBM")
            df_out[f"{alias}_lower"] = _pick_first_col(bb_df, "BBL")
            indicator_columns.extend([f"{alias}_upper", f"{alias}_mid", f"{alias}_lower"])
        elif kind == "ATR":
            period = int(_require_param(params, "period"))
            df_out[alias] = ta.atr(
                df_out["high"],
                df_out["low"],
                df_out["close"],
                length=period,
            )
            indicator_columns.append(alias)
        elif kind in {"STOCH", "STOCHASTIC"}:
            k_period = int(_require_param(params, "k_period"))
            d_period = int(_require_param(params, "d_period"))
            stoch_df = ta.stoch(
                df_out["high"],
                df_out["low"],
                df_out["close"],
                k=k_period,
                d=d_period,
            )
            if stoch_df is None or stoch_df.empty:
                raise ValueError("Stochastic computation returned empty data")
            df_out[f"{alias}_k"] = _pick_first_col(stoch_df, "STOCHk")
            df_out[f"{alias}_d"] = _pick_first_col(stoch_df, "STOCHd")
            indicator_columns.extend([f"{alias}_k", f"{alias}_d"])
        elif kind == "ADX":
            period = int(_require_param(params, "period"))
            adx_df = ta.adx(
                df_out["high"],
                df_out["low"],
                df_out["close"],
                length=period,
            )
            if adx_df is None or adx_df.empty:
                raise ValueError("ADX computation returned empty data")
            # ADX returns: ADX, DMP (+DI), DMN (-DI)
            df_out[alias] = _pick_first_col(adx_df, "ADX")
            df_out[f"{alias}_dmp"] = _pick_first_col(adx_df, "DMP")  # +DI
            df_out[f"{alias}_dmn"] = _pick_first_col(adx_df, "DMN")  # -DI
            indicator_columns.extend([alias, f"{alias}_dmp", f"{alias}_dmn"])
        elif kind in {"ICHIMOKU", "CLOUD"}:
            # Ichimoku Cloud with standard or custom periods
            tenkan = int(params.get("tenkan", 9))
            kijun = int(params.get("kijun", 26))
            senkou = int(params.get("senkou", 52))

            ichimoku_result = ta.ichimoku(
                df_out["high"],
                df_out["low"],
                df_out["close"],
                tenkan=tenkan,
                kijun=kijun,
                senkou=senkou,
            )

            # pandas_ta ichimoku returns a tuple of (df, span_a, span_b)
            if isinstance(ichimoku_result, tuple):
                ichimoku_df = ichimoku_result[0]
            else:
                ichimoku_df = ichimoku_result

            if ichimoku_df is None or ichimoku_df.empty:
                raise ValueError("Ichimoku computation returned empty data")

            # Ichimoku returns 5 lines:
            # - ITS_9 (Tenkan-sen / Conversion Line)
            # - IKS_26 (Kijun-sen / Base Line)
            # - ISA_9 (Senkou Span A / Leading Span A)
            # - ISB_26 (Senkou Span B / Leading Span B)
            # - ICS_26 (Chikou Span / Lagging Span)

            # Map to standard names
            df_out[f"{alias}_tenkan"] = _pick_first_col(ichimoku_df, f"ITS_{tenkan}")
            df_out[f"{alias}_kijun"] = _pick_first_col(ichimoku_df, f"IKS_{kijun}")
            df_out[f"{alias}_span_a"] = _pick_first_col(ichimoku_df, f"ISA_{tenkan}")
            df_out[f"{alias}_span_b"] = _pick_first_col(ichimoku_df, f"ISB_{kijun}")
            df_out[f"{alias}_chikou"] = _pick_first_col(ichimoku_df, f"ICS_{kijun}")

            indicator_columns.extend([
                f"{alias}_tenkan",
                f"{alias}_kijun",
                f"{alias}_span_a",
                f"{alias}_span_b",
                f"{alias}_chikou",
            ])
        else:
            raise ValueError(f"Unsupported indicator type: {indicator_type}")

    # Store indicator columns as metadata for warmup detection
    df_out.attrs["indicator_columns"] = indicator_columns

    return df_out


def get_warmup_period(df: pd.DataFrame) -> int:
    """
    Determine the warmup period (number of bars to skip) based on indicator NaN values.

    The warmup period is the first bar where ALL indicators have valid (non-NaN) values.

    Args:
        df: DataFrame with computed indicators

    Returns:
        Number of bars to skip (0 if no warmup needed)
    """
    if df.empty:
        return 0

    # Get indicator columns from metadata
    indicator_columns = df.attrs.get("indicator_columns", [])

    if not indicator_columns:
        # No indicators, no warmup needed
        return 0

    # Find first row where all indicators are non-NaN
    indicator_data = df[indicator_columns]
    valid_rows = indicator_data.notna().all(axis=1)

    if not valid_rows.any():
        # All rows have at least one NaN - no valid data
        raise ValueError(
            "All bars contain NaN values in indicators. "
            "Need more historical data or reduce indicator periods."
        )

    # First True value is the first valid bar
    first_valid_idx = valid_rows.idxmax()
    warmup_bars = df.index.get_loc(first_valid_idx)

    return warmup_bars


def trim_warmup_period(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Remove warmup period from DataFrame where indicators have NaN values.

    Args:
        df: DataFrame with computed indicators

    Returns:
        Tuple of (trimmed_df, warmup_bars_skipped)
    """
    warmup_bars = get_warmup_period(df)

    if warmup_bars == 0:
        return df, 0

    # Trim the warmup period
    trimmed_df = df.iloc[warmup_bars:].copy()

    # Preserve indicator column metadata
    if "indicator_columns" in df.attrs:
        trimmed_df.attrs["indicator_columns"] = df.attrs["indicator_columns"]

    return trimmed_df, warmup_bars
