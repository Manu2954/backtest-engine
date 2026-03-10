from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.indicator_layer import compute_indicators  # noqa: E402


def make_df(rows: int = 200) -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=rows, freq="D")
    close = pd.Series(range(rows), index=index, dtype="float") + 100.0
    df = pd.DataFrame(
        {
            "open": close + 0.1,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
        },
        index=index,
    )
    return df


def assert_no_recent_nans(series: pd.Series, tail: int = 20) -> None:
    assert series.iloc[-tail:].isna().sum() == 0


def test_rsi() -> None:
    df = make_df()
    out = compute_indicators(
        df,
        [
            {
                "indicator_type": "RSI",
                "alias": "rsi_14",
                "params": {"period": 14, "source": "close"},
            }
        ],
    )
    assert "rsi_14" in out.columns
    assert_no_recent_nans(out["rsi_14"])


def test_ema() -> None:
    df = make_df()
    out = compute_indicators(
        df,
        [
            {
                "indicator_type": "EMA",
                "alias": "ema_20",
                "params": {"period": 20, "source": "close"},
            }
        ],
    )
    assert "ema_20" in out.columns
    assert_no_recent_nans(out["ema_20"])


def test_sma() -> None:
    df = make_df()
    out = compute_indicators(
        df,
        [
            {
                "indicator_type": "SMA",
                "alias": "sma_50",
                "params": {"period": 50, "source": "close"},
            }
        ],
    )
    assert "sma_50" in out.columns
    assert_no_recent_nans(out["sma_50"])


def test_macd() -> None:
    df = make_df()
    out = compute_indicators(
        df,
        [
            {
                "indicator_type": "MACD",
                "alias": "macd",
                "params": {"fast": 12, "slow": 26, "signal": 9, "source": "close"},
            }
        ],
    )
    assert "macd_macd" in out.columns
    assert "macd_signal" in out.columns
    assert "macd_hist" in out.columns
    assert_no_recent_nans(out["macd_macd"])
    assert_no_recent_nans(out["macd_signal"])
    assert_no_recent_nans(out["macd_hist"])


def test_bollinger_bands() -> None:
    df = make_df()
    out = compute_indicators(
        df,
        [
            {
                "indicator_type": "BB",
                "alias": "bb_20",
                "params": {"period": 20, "std_dev": 2, "source": "close"},
            }
        ],
    )
    assert "bb_20_upper" in out.columns
    assert "bb_20_mid" in out.columns
    assert "bb_20_lower" in out.columns
    assert_no_recent_nans(out["bb_20_upper"])
    assert_no_recent_nans(out["bb_20_mid"])
    assert_no_recent_nans(out["bb_20_lower"])


def test_atr() -> None:
    df = make_df()
    out = compute_indicators(
        df,
        [
            {
                "indicator_type": "ATR",
                "alias": "atr_14",
                "params": {"period": 14},
            }
        ],
    )
    assert "atr_14" in out.columns
    assert_no_recent_nans(out["atr_14"])


def test_stochastic() -> None:
    df = make_df()
    out = compute_indicators(
        df,
        [
            {
                "indicator_type": "STOCH",
                "alias": "stoch_14_3",
                "params": {"k_period": 14, "d_period": 3},
            }
        ],
    )
    assert "stoch_14_3_k" in out.columns
    assert "stoch_14_3_d" in out.columns
    assert_no_recent_nans(out["stoch_14_3_k"])
    assert_no_recent_nans(out["stoch_14_3_d"])


def test_duplicate_indicator_alias_rejected() -> None:
    """
    Bug Fix Test #8: Duplicate indicator aliases should be rejected.

    When two indicators have the same alias, the second would overwrite
    the first, causing silent data corruption. Should raise ValueError.
    """
    df = make_df()

    # Two indicators with same alias "rsi_14"
    indicators = [
        {
            "indicator_type": "RSI",
            "alias": "rsi_14",
            "params": {"period": 14, "source": "close"},
        },
        {
            "indicator_type": "RSI",
            "alias": "rsi_14",  # Duplicate!
            "params": {"period": 20, "source": "close"},
        },
    ]

    try:
        compute_indicators(df, indicators)
        assert False, "Should have raised ValueError for duplicate alias"
    except ValueError as e:
        assert "duplicate" in str(e).lower()
        assert "rsi_14" in str(e).lower()


def test_different_indicators_same_alias_rejected() -> None:
    """
    Bug Fix Test #8: Different indicator types with same alias should be rejected.
    """
    df = make_df()

    # RSI and EMA with same alias
    indicators = [
        {
            "indicator_type": "RSI",
            "alias": "my_indicator",
            "params": {"period": 14, "source": "close"},
        },
        {
            "indicator_type": "EMA",
            "alias": "my_indicator",  # Same alias as RSI!
            "params": {"period": 20, "source": "close"},
        },
    ]

    try:
        compute_indicators(df, indicators)
        assert False, "Should have raised ValueError for duplicate alias"
    except ValueError as e:
        assert "duplicate" in str(e).lower()
        assert "my_indicator" in str(e).lower()


def test_unique_aliases_allowed() -> None:
    """
    Bug Fix Test #8: Multiple indicators with unique aliases should work.
    """
    df = make_df()

    # Multiple indicators with unique aliases
    indicators = [
        {
            "indicator_type": "RSI",
            "alias": "rsi_14",
            "params": {"period": 14, "source": "close"},
        },
        {
            "indicator_type": "RSI",
            "alias": "rsi_20",  # Different alias
            "params": {"period": 20, "source": "close"},
        },
        {
            "indicator_type": "EMA",
            "alias": "ema_50",
            "params": {"period": 50, "source": "close"},
        },
    ]

    out = compute_indicators(df, indicators)

    # All indicators should be present
    assert "rsi_14" in out.columns
    assert "rsi_20" in out.columns
    assert "ema_50" in out.columns

    # Values should be different (different periods)
    assert not out["rsi_14"].equals(out["rsi_20"])


def test_roc() -> None:
    """Test ROC (Rate of Change) indicator."""
    df = make_df()
    out = compute_indicators(
        df,
        [
            {
                "indicator_type": "ROC",
                "alias": "roc_10",
                "params": {"period": 10, "source": "close"},
            }
        ],
    )
    assert "roc_10" in out.columns
    assert_no_recent_nans(out["roc_10"])


def test_obv() -> None:
    """Test OBV (On-Balance Volume) indicator."""
    df = make_df()
    out = compute_indicators(
        df,
        [
            {
                "indicator_type": "OBV",
                "alias": "obv",
                "params": {},  # OBV doesn't need parameters
            }
        ],
    )
    assert "obv" in out.columns
    # OBV is cumulative, so should not have NaNs
    assert out["obv"].isna().sum() == 0
