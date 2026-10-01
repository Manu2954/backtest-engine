"""
Reproduction tests for financial-correctness bugs found in the 2026-09-28 review.

Each test asserts the CORRECT behavior and is expected to FAIL against the
current code. They are marked ``xfail(strict=True)`` so the suite stays green
today but will START FAILING (as XPASS -> error) the moment the underlying bug
is fixed, at which point the ``xfail`` marker should be removed and the test
becomes a permanent regression guard.

Each test documents: the file:line of the defect, a deterministic input, and
the wrong-vs-correct output verified by hand.

Scope note: the review also flagged non-causal regime labels
(regime_detection.py detect_regimes / analyze_trades_by_regime). That is a
whole-series lookahead that cannot be reproduced deterministically at the unit
level without the full signal pipeline, and is a methodology/contract issue
(labels are descriptive, must not feed entry logic) rather than a single wrong
number. It is intentionally documented here but not asserted. See the review
summary for the recommended fix (expanding-window detector or a loud
"non-causal" contract on the labels).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from app.engine.data_layer import get_cache_key, _filter_incomplete_bars
from app.engine.report_generator import (
    calculate_buy_and_hold_equity,
    generate_report,
)


# ---------------------------------------------------------------------------
# BUG 1 (CRITICAL) - Redis cache key collision across data variants.
# app/engine/data_layer.py:219  get_cache_key(ticker, resolution, start, end)
#
# The key omits asset_class / provider / market_type / timezone. Two fetches
# for the same symbol+resolution+date-range but a different market_type (SPOT
# vs FUTURES) or provider produce the SAME key, so the second fetch returns the
# first's cached DataFrame -> silently wrong prices, no error.
#
# NOTE: get_cache_key currently accepts only (ticker, resolution, start, end).
# The correct signature must include the disambiguating fields. This test calls
# the *intended* future signature; until the fix lands the extra kwargs raise
# TypeError, which is why the test xfails.
# ---------------------------------------------------------------------------
def test_cache_key_distinguishes_market_type() -> None:
    from datetime import date

    start, end = date(2026, 1, 1), date(2026, 2, 1)

    spot_key = get_cache_key(
        "BINANCE", "BTCUSDT", "1d", "CRYPTO", "SPOT", start, end
    )
    futures_key = get_cache_key(
         "BINANCE", "BTCUSDT", "1d", "CRYPTO", "FUTURES", start, end
    )

    assert spot_key != futures_key, (
        "SPOT and FUTURES for the same symbol/resolution/dates must not share a "
        "cache key; otherwise the second fetch returns the first's cached prices."
    )


# ---------------------------------------------------------------------------
# BUG 2 (HIGH) - Buy-and-hold benchmark equity does not start at initial capital.
# app/engine/report_generator.py:54,57
#     entry_price = df.iloc[0]["open"]
#     equity = initial_capital * (df["close"] / entry_price)
# => equity[0] = capital * close[0]/open[0] != capital.
#
# Verified numeric impact (open[0]=100, close[0]=110, close[-1]=120):
#   reported benchmark_return_pct = 9.09%   (base inflated to 11000)
#   correct   buy-at-open return  = 20.0%
# Benchmark daily returns / Sharpe are UNAFFECTED (pct_change cancels the
# constant factor); only the level and return/alpha metrics are wrong.
# ---------------------------------------------------------------------------

def test_benchmark_equity_anchors_at_initial_capital() -> None:
    capital = 10_000.0
    df = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 103.0],
            "close": [110.0, 102.0, 104.0, 120.0],
        },
        index=pd.date_range("2026-01-01", periods=4, freq="D"),
    )

    eq = calculate_buy_and_hold_equity(df, capital, asset_class="CRYPTO")

    # The benchmark must be worth exactly `capital` before any holding period.
    assert eq.iloc[0] == pytest.approx(capital), (
        f"benchmark equity[0] should equal initial capital {capital}, "
        f"got {eq.iloc[0]} (phantom bar-0 return of close0/open0)."
    )

def test_benchmark_return_pct_is_buy_at_close_to_close() -> None:
    capital = 10_000.0
    df = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 103.0],
            "close": [110.0, 102.0, 104.0, 120.0],
        },
        index=pd.date_range("2026-01-01", periods=4, freq="D"),
    )
    # Strategy equity is irrelevant here; give a flat curve so only the
    # benchmark math is under test.
    strategy_equity = pd.Series([capital] * len(df), index=df.index)
    benchmark_equity = calculate_buy_and_hold_equity(df, capital, asset_class="CRYPTO")

    report = generate_report(
        trade_log=[],
        equity_curve=strategy_equity,
        initial_capital=capital,
        benchmark_equity=benchmark_equity,
    )

    # Buy at close[0]=110, hold to close[-1]=120 => +20%.
    expected = (df.iloc[-1]["close"] / df.iloc[0]["close"] - 1) * 100
    got = report.get("benchmark_return_pct", 0.0)
    assert got == pytest.approx(expected, abs=0.5), (
        f"benchmark_return_pct should be ~{expected:.2f}% (buy at open[0], hold "
        f"to close[-1]); got {got:.2f}% because the base is inflated to "
        f"capital*close0/open0."
    )


# ---------------------------------------------------------------------------
# BUG 3 (HIGH) - Sortino uses std of the downside subset about ITS OWN mean,
# not the root-mean-square of shortfalls below the target.
# app/engine/report_generator.py:280  downside_std = downside_returns.std()
#
# With a single down day, .std(ddof=1) is NaN -> sortino=None (looks like N/A)
# for a strategy that clearly has downside. The correct downside deviation is
# RMS of min(excess, 0) over the full series (target = risk-free = 0).
# This test uses >=2 down days so the difference is a finite, checkable number.
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    reason="report_generator.py:280 downside_std = subset std about own mean, not RMS of shortfalls",
    strict=True,
    raises=AssertionError,
)
def test_sortino_uses_rms_downside_deviation() -> None:
    capital = 10_000.0
    # Construct an equity curve with known daily returns including two down days.
    # daily returns approx: +1%, -1%, +2%, -3%
    rets = [0.01, -0.01, 0.02, -0.03]
    equity_vals = [capital]
    for r in rets:
        equity_vals.append(equity_vals[-1] * (1 + r))
    equity = pd.Series(
        equity_vals, index=pd.date_range("2026-01-01", periods=len(equity_vals), freq="D")
    )

    report = generate_report(
        trade_log=[{"pnl": 100.0}],
        equity_curve=equity,
        initial_capital=capital,
        risk_free_rate=0.0,
    )

    daily = equity.pct_change().dropna()
    # Correct Sortino: mean(excess) / RMS(min(excess,0)) * sqrt(252), target=0.
    downside_rms = np.sqrt(np.mean(np.minimum(daily.values, 0.0) ** 2))
    expected_sortino = (daily.mean() / downside_rms) * (252 ** 0.5)

    got = report.get("sortino_ratio", report.get("sortino"))
    assert got is not None, "Sortino should be defined when there are down days."
    assert got == pytest.approx(expected_sortino, rel=0.05), (
        f"Sortino should use RMS downside deviation (expected ~{expected_sortino:.3f}); "
        f"got {got}. Current code uses downside_returns.std() about the subset mean, "
        f"which inflates the ratio."
    )


# ---------------------------------------------------------------------------
# BUG 4 (HIGH) - Incomplete DAILY bar is never dropped -> lookahead.
# app/engine/data_layer.py:305  _filter_incomplete_bars only filters intraday
# resolutions; "1d"/"1w"/"1mo" hit the early return, so a still-forming daily
# bar (fetched mid-day) is kept with a non-final high/low/close.
# ---------------------------------------------------------------------------

def test_incomplete_daily_bar_is_filtered() -> None:
    # Two daily bars: yesterday (complete) and today (still forming).
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)

    df = pd.DataFrame(
        {
            "open": [100.0, 105.0],
            "high": [106.0, 105.5],   # today's high not yet final
            "low": [99.0, 104.0],
            "close": [105.0, 105.2],  # today's close == current price
            "volume": [1_000_000, 10_000],
        },
        index=pd.DatetimeIndex([yesterday, today]),
    )

    filtered = _filter_incomplete_bars(df, "1d")

    print(filtered.all())

    assert today not in filtered.index, (
        "The still-forming daily bar (bar_end > now) must be dropped for '1d' "
        "just as it is for intraday resolutions; keeping it leaks a non-final "
        "close/high/low into the backtest (lookahead)."
    )
