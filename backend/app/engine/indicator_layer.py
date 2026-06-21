from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)

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


def _validate_period(period: int, indicator_name: str) -> None:
    """Validate that period is positive."""
    if period <= 0:
        raise ValueError(f"{indicator_name}: period must be positive, got {period}")


def _validate_std_dev(std_dev: float, indicator_name: str) -> None:
    """Validate that standard deviation is positive."""
    if std_dev <= 0:
        raise ValueError(f"{indicator_name}: std_dev must be positive, got {std_dev}")


def _validate_macd_periods(fast: int, slow: int) -> None:
    """Validate MACD periods relationship."""
    if fast >= slow:
        raise ValueError(f"MACD: fast_period ({fast}) must be less than slow_period ({slow})")


def _validate_multiplier(multiplier: float, indicator_name: str) -> None:
    """Validate that multiplier is positive."""
    if multiplier <= 0:
        raise ValueError(f"{indicator_name}: multiplier must be positive, got {multiplier}")


def _validate_input_data(df: pd.DataFrame) -> None:
    """Validate input DataFrame for common data quality issues."""
    ohlcv_cols = ["open", "high", "low", "close", "volume"]

    for col in ohlcv_cols:
        if col not in df.columns:
            continue

        # Check for inf values (critical - raise error)
        if np.isinf(df[col]).any():
            raise ValueError(f"Column '{col}' contains inf values - data is corrupted")

        # Check for NaN values (warning only - may be expected at edges)
        nan_count = df[col].isna().sum()
        if nan_count > 0:
            nan_pct = nan_count / len(df) * 100
            logger.warning(
                "Column '%s' has %d NaN values (%.1f%%) - may affect indicator accuracy",
                col, nan_count, nan_pct
            )

    # Check for negative prices (critical for OHLC)
    price_cols = ["open", "high", "low", "close"]
    for col in price_cols:
        if col in df.columns and (df[col] < 0).any():
            raise ValueError(f"Column '{col}' contains negative values - invalid price data")

    # Check for negative volume (warning - some data sources use -1 for missing)
    if "volume" in df.columns and (df["volume"] < 0).any():
        logger.warning("Column 'volume' contains negative values - may indicate missing data")


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

    # Validate input data quality
    _validate_input_data(df_out)

    # Track all indicator column names for warmup detection
    indicator_columns = []

    # Track seen aliases to prevent duplicates (Bug #8 fix)
    seen_aliases = set()

    for indicator in indicators:
        indicator_type = indicator.get("indicator_type") or indicator.get("type")
        alias = indicator.get("alias")
        params = indicator.get("params", {}) or {}

        if not indicator_type:
            raise ValueError("Indicator type is required")
        if not alias:
            raise ValueError("Indicator alias is required")

        # Check for duplicate alias
        if alias in seen_aliases:
            raise ValueError(f"Duplicate indicator alias: '{alias}'. Each indicator must have a unique alias.")
        seen_aliases.add(alias)

        kind = str(indicator_type).upper()
        source = params.get("source", "close")

        if kind == "RSI":
            period = int(_require_param(params, "period"))
            _validate_period(period, "RSI")
            series = _get_series(df_out, source)
            df_out[alias] = ta.rsi(series, length=period)
            indicator_columns.append(alias)
        elif kind == "EMA":
            period = int(_require_param(params, "period"))
            _validate_period(period, "EMA")
            series = _get_series(df_out, source)
            df_out[alias] = ta.ema(series, length=period)
            indicator_columns.append(alias)
        elif kind == "SMA":
            period = int(_require_param(params, "period"))
            _validate_period(period, "SMA")
            series = _get_series(df_out, source)
            df_out[alias] = ta.sma(series, length=period)
            indicator_columns.append(alias)
        elif kind == "MACD":
            fast = int(_require_param(params, "fast"))
            slow = int(_require_param(params, "slow"))
            signal = int(_require_param(params, "signal"))
            _validate_period(fast, "MACD fast")
            _validate_period(slow, "MACD slow")
            _validate_period(signal, "MACD signal")
            _validate_macd_periods(fast, slow)
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
            _validate_period(length, "Bollinger Bands")
            _validate_std_dev(std, "Bollinger Bands")
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
            _validate_period(period, "ATR")
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
            _validate_period(k_period, "Stochastic k")
            _validate_period(d_period, "Stochastic d")
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
            _validate_period(period, "ADX")
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
            _validate_period(tenkan, "Ichimoku tenkan")
            _validate_period(kijun, "Ichimoku kijun")
            _validate_period(senkou, "Ichimoku senkou")

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
        elif kind == "ROC":
            # Rate of Change: (price - price[n]) / price[n] * 100
            period = int(_require_param(params, "period"))
            series = _get_series(df_out, source)
            df_out[alias] = ta.roc(series, length=period)
            indicator_columns.append(alias)
        elif kind == "OBV":
            # On-Balance Volume: cumulative volume based on price direction
            # OBV doesn't use a period parameter
            df_out[alias] = ta.obv(df_out["close"], df_out["volume"])
            indicator_columns.append(alias)
        elif kind in {"DONCHIAN", "DC"}:
            # Donchian Channel: highest high and lowest low over period
            period = int(_require_param(params, "period"))
            dc_df = ta.donchian(
                df_out["high"],
                df_out["low"],
                lower_length=period,
                upper_length=period,
            )
            if dc_df is None or dc_df.empty:
                raise ValueError("Donchian Channel computation returned empty data")
            df_out[f"{alias}_upper"] = _pick_first_col(dc_df, f"DCU_{period}")
            df_out[f"{alias}_lower"] = _pick_first_col(dc_df, f"DCL_{period}")
            df_out[f"{alias}_mid"] = _pick_first_col(dc_df, f"DCM_{period}")
            indicator_columns.extend([f"{alias}_upper", f"{alias}_lower", f"{alias}_mid"])
        elif kind in {"HEIKINASHI", "HA"}:
            # Heikin Ashi candles: smoothed candlesticks
            ha_df = ta.ha(
                df_out["open"],
                df_out["high"],
                df_out["low"],
                df_out["close"],
            )
            if ha_df is None or ha_df.empty:
                raise ValueError("Heikin Ashi computation returned empty data")
            df_out[f"{alias}_open"] = ha_df["HA_open"]
            df_out[f"{alias}_high"] = ha_df["HA_high"]
            df_out[f"{alias}_low"] = ha_df["HA_low"]
            df_out[f"{alias}_close"] = ha_df["HA_close"]
            indicator_columns.extend([
                f"{alias}_open",
                f"{alias}_high",
                f"{alias}_low",
                f"{alias}_close",
            ])
        elif kind == "SUPERTREND":
            # Supertrend: trend-following indicator using ATR
            period = int(_require_param(params, "period"))
            multiplier = float(_require_param(params, "multiplier"))
            _validate_period(period, "Supertrend")
            _validate_multiplier(multiplier, "Supertrend")
            supertrend_df = ta.supertrend(
                df_out["high"],
                df_out["low"],
                df_out["close"],
                length=period,
                multiplier=multiplier,
            )
            if supertrend_df is None or supertrend_df.empty:
                raise ValueError("Supertrend computation returned empty data")
            # Supertrend returns: SUPERT_<period>_<multiplier>, SUPERTd_<period>_<multiplier>, SUPERTl_<period>_<multiplier>, SUPERTs_<period>_<multiplier>
            # SUPERT = trend line value
            # SUPERTd = direction (1 = bullish, -1 = bearish)
            # SUPERTl = long stop (NaN when bearish)
            # SUPERTs = short stop (NaN when bullish)
            df_out[f"{alias}_trend"] = _pick_first_col(supertrend_df, f"SUPERT_{period}_{multiplier}")
            df_out[alias] = _pick_first_col(supertrend_df, f"SUPERTd_{period}_{multiplier}")
            df_out[f"{alias}_long"] = _pick_first_col(supertrend_df, f"SUPERTl_{period}_{multiplier}")
            df_out[f"{alias}_short"] = _pick_first_col(supertrend_df, f"SUPERTs_{period}_{multiplier}")
            # Only check primary column for warmup (long/short are conditionally NaN by design)
            indicator_columns.append(alias)
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
    logger.debug("Warmup period: %d bars", warmup_bars)
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
