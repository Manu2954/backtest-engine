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
        elif kind == "EMA":
            period = int(_require_param(params, "period"))
            series = _get_series(df_out, source)
            df_out[alias] = ta.ema(series, length=period)
        elif kind == "SMA":
            period = int(_require_param(params, "period"))
            series = _get_series(df_out, source)
            df_out[alias] = ta.sma(series, length=period)
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
        elif kind == "ATR":
            period = int(_require_param(params, "period"))
            df_out[alias] = ta.atr(
                df_out["high"],
                df_out["low"],
                df_out["close"],
                length=period,
            )
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
        else:
            raise ValueError(f"Unsupported indicator type: {indicator_type}")

    return df_out
