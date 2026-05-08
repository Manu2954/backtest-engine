"""
Volatile Bullish Bar — Short Mean-Reversion Strategy

Entry: Short after a bullish 1h candle with high-low range >= 2%
  - (high - low) >= low * 0.02   (2% range)
  - close > open                  (bullish candle)
  - volume is highest since last SMA50/SMA200 crossover
  - last crossover was bearish (SMA50 < SMA200)

Exit: TP -5% (price drops 5%), ATR signal exit

Usage:
  python scripts/smoke_volatile_short.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv
from app.engine.indicator_layer import compute_indicators, trim_warmup_period
from app.engine.condition_engine import evaluate_conditions
from app.engine.state_machine import run_backtest
from app.engine.report_generator import generate_report

from app.engine.robustness.regime_detection import (
    detect_regimes,
    analyze_trades_by_regime,
    calculate_regime_distribution,
    assess_regime_dependency,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TICKER = "BTCUSDT"
START = "2023-01-01"
END = "2026-05-06"
TF = "1h"
ASSET_CLASS = "CRYPTO"
INITIAL_CAPITAL = 10_000.0

RANGE_THRESHOLD = 0.02    # 2% high-low range
STOP_LOSS_PCT = None

INDICATORS = [
    {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    {"indicator_type": "SMA", "alias": "sma_200", "params": {"period": 200, "source": "close"}},
    {"indicator_type": "ATR", "alias": "atr_14", "params": {"period": 14}},
]

# Entry conditions: bullish candle with large range
SHORT_ENTRY_GROUP = {
    "logic": "AND",
    "conditions": [
        {
            "left_operand_type": "EXPRESSION",
            "left_operand_value": "high - low",
            "operator": "GTE",
            "right_operand_type": "EXPRESSION",
            "right_operand_value": f"low * {RANGE_THRESHOLD}",
        },
        {
            "left_operand_type": "OHLCV",
            "left_operand_value": "close",
            "operator": "GT",
            "right_operand_type": "OHLCV",
            "right_operand_value": "open",
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

import numpy as np


def compute_max_volume_since_cross(df: pd.DataFrame) -> pd.Series:
    cross = (
        ((df["sma_50"] > df["sma_200"]) & (df["sma_50"].shift(1) <= df["sma_200"].shift(1))) |
        ((df["sma_50"] < df["sma_200"]) & (df["sma_50"].shift(1) >= df["sma_200"].shift(1)))
    )
    segment_id = cross.cumsum()
    max_vol = df.groupby(segment_id)["volume"].cummax()
    return max_vol


def last_cross_was_bearish(df: pd.DataFrame) -> pd.Series:
    bull_cross = (df["sma_50"] > df["sma_200"]) & (df["sma_50"].shift(1) <= df["sma_200"].shift(1))
    bear_cross = (df["sma_50"] < df["sma_200"]) & (df["sma_50"].shift(1) >= df["sma_200"].shift(1))

    cross_type = pd.Series(0, index=df.index)
    cross_type[bull_cross] = 1
    cross_type[bear_cross] = -1

    cross_type = cross_type.replace(0, np.nan).ffill().fillna(0)

    return cross_type == -1


def run_backtest_on_df(df, initial_capital: float = INITIAL_CAPITAL) -> tuple[list[dict], dict]:
    base_signal = evaluate_conditions(df, SHORT_ENTRY_GROUP)

    max_vol_since_cross = compute_max_volume_since_cross(df)
    volume_is_highest = df["volume"] >= max_vol_since_cross

    bearish_cross_filter = last_cross_was_bearish(df)

    atr_mean_24 = df["atr_14"].shift(1).rolling(24).mean()
    df["atr_mean_24"] = atr_mean_24
    atr_above_mean = df["atr_14"] > atr_mean_24

    body = (df["open"] - df["close"]).abs()
    upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
    lower_wick = df[["open", "close"]].min(axis=1) - df["low"]
    total_wick = upper_wick + lower_wick
    body_gt_wick = body > total_wick

    short_entry_signal = base_signal & volume_is_highest & bearish_cross_filter & atr_above_mean & body_gt_wick

    # ATR exit gate: only fire when price crosses above SMA200 (bearish thesis invalidated)
    crossed_above_sma200 = (df["close"] > df["sma_200"]) & (df["close"].shift(1) <= df["sma_200"].shift(1))
    df["skip_atr_exit"] = ~crossed_above_sma200  # skip when NOT crossing above

    short_exit_signal = pd.Series(False, index=df.index)

    # Dummy long signals (no long trades)
    long_entry = pd.Series(False, index=df.index)
    long_exit = pd.Series(False, index=df.index)

    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=long_entry,
        exit_signal=long_exit,
        initial_capital=initial_capital,
        asset_class=ASSET_CLASS,
        position_size_type="percent_capital",
        position_size_value=50.0,
        stop_loss_pct=STOP_LOSS_PCT,
        take_profit_pct=5.0,
        dynamic_exit_monitor_column="atr_14",
        dynamic_exit_ref_column="atr_mean_24",
        dynamic_exit_min_loss_pct=1.0,
        dynamic_exit_skip_column="skip_atr_exit",
        commission_per_trade=1.0,
        slippage_pct=0.0,
        enable_attribution=False,
        short_entry_signal=short_entry_signal,
        short_exit_signal=short_exit_signal,
    )

    report = generate_report(trades, equity_curve, initial_capital)
    return trades, report


def extract_metrics(report: dict) -> dict:
    return {
        "total_return_pct": report.get("total_return_pct", 0.0),
        "sharpe_ratio": report.get("sharpe_ratio", 0.0),
        "win_rate": report.get("win_rate", 0.0),
        "total_trades": report.get("total_trades", 0),
    }


def main() -> None:
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║           VOLATILE BULLISH BAR — SHORT MEAN-REVERSION              ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"  Ticker: {TICKER}  | TF: {TF} | Period: {START} to {END} | Capital: ${INITIAL_CAPITAL:,.0f}")
    print(f"  Entry: bullish candle with (high-low)/low >= {RANGE_THRESHOLD*100:.1f}%")
    print(f"         + volume is highest since last SMA50/SMA200 crossover")
    print(f"         + last crossover was bearish (SMA50 < SMA200)")
    print(f"  Exit:  TP -5% (price drops 5%)  |  ATR signal exit")

    # ─── Stage 1: Data ────────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  1. DATA")
    print(f"{'─' * 70}")

    df_raw = fetch_ohlcv(TICKER, START, END, TF, ASSET_CLASS)
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        df = compute_indicators(df_raw.copy(), INDICATORS)
        df, warmup_bars = trim_warmup_period(df)

    print(f"  Bars fetched: {len(df_raw):,}  |  After warmup: {len(df):,}  |  Warmup: {warmup_bars} bars")
    print(f"  Effective start: {df.index[0].strftime('%Y-%m-%d %H:%M')}")

    # Show how many entry signals fire
    base_signal = evaluate_conditions(df, SHORT_ENTRY_GROUP)
    max_vol_since_cross = compute_max_volume_since_cross(df)
    volume_is_highest = df["volume"] >= max_vol_since_cross
    bearish_cross_filter = last_cross_was_bearish(df)
    entry_signal = base_signal & volume_is_highest & bearish_cross_filter
    print(f"  Entry signals: {entry_signal.sum()} (base: {base_signal.sum()}, +vol: {(base_signal & volume_is_highest).sum()}, +bear cross: {entry_signal.sum()})")

    # ─── Stage 2: Backtest ────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  2. BACKTEST RESULTS")
    print(f"{'─' * 70}")

    trades, report = run_backtest_on_df(df)

    print(f"  {'Metric':<24} {'Value':>12}")
    print(f"  {'─' * 38}")
    print(f"  {'Total return':<24} {report['total_return_pct']:>+11.2f}%")
    print(f"  {'CAGR':<24} {report.get('cagr', 0):>+11.2f}%")
    print(f"  {'Sharpe ratio':<24} {report['sharpe_ratio']:>12.3f}")
    print(f"  {'Max drawdown':<24} {report['max_drawdown_pct']:>11.2f}%")
    print(f"  {'Profit factor':<24} {report['profit_factor']:>12.2f}")
    print(f"  {'Win rate':<24} {report['win_rate']:>11.1f}%")
    print(f"  {'Total trades':<24} {report['total_trades']:>12}")
    print(f"  {'Avg win':<24} {'$'}{report.get('avg_win', 0):>11,.2f}")
    print(f"  {'Avg loss':<24} {'$'}{report.get('avg_loss', 0):>11,.2f}")
    print(f"  {'Avg win/loss ratio':<24} {report.get('avg_win_loss', 0):>12.2f}")
    print(f"  {'Largest win':<24} {'$'}{report.get('largest_win', 0):>11,.2f}")
    print(f"  {'Largest loss':<24} {'$'}{report.get('largest_loss', 0):>11,.2f}")
    print(f"  {'Avg trade duration':<24} {report.get('avg_trade_duration_days', 0):>10.1f} days")
    print(f"  {'Final capital':<24} {'$'}{report['final_capital']:>11,.2f}")

    # Exit reason breakdown
    tp_count = sum(1 for t in trades if t.get("exit_reason") == "take_profit")
    sl_count = sum(1 for t in trades if t.get("exit_reason") == "stop_loss")
    other_count = len(trades) - tp_count - sl_count

    print(f"\n  Exit reasons:")
    print(f"    Take profit: {tp_count}")
    print(f"    Stop loss:   {sl_count}")
    if other_count:
        print(f"    Other (signal/force close): {other_count}")

    # ─── Trade Log ────────────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  TRADE LOG")
    print(f"{'─' * 70}")
    atr_mean_24_col = df["atr_mean_24"]
    print(f"  {'#':<4} {'Entry':<18} {'Exit':<18} {'Entry$':>9} {'Exit$':>9} {'PnL':>9} {'PnL%':>7} {'MDD%':>7} {'eATR':>6} {'rATR':>6} {'Reason'}")
    print(f"  {'─' * 110}")
    for i, t in enumerate(trades, 1):
        entry_dt = t["entry_date"].strftime("%Y-%m-%d %H:%M")
        exit_dt = t["exit_date"].strftime("%Y-%m-%d %H:%M")
        exit_loc = df.index.get_loc(t["exit_date"])
        entry_loc = df.index.get_loc(t["entry_date"])
        signal_loc = max(entry_loc - 1, 0)
        exit_atr = df.iloc[exit_loc]["atr_14"]
        ref_atr = atr_mean_24_col.iloc[signal_loc]
        entry_price = t["entry_price"]
        # MDD for shorts: max adverse move is price going UP
        trade_highs = df.iloc[entry_loc:exit_loc + 1]["high"]
        max_dd_pct = (trade_highs.max() - entry_price) / entry_price * 100
        print(f"  {i:<4} {entry_dt:<18} {exit_dt:<18} ${t['entry_price']:>8,.0f} ${t['exit_price']:>8,.0f} "
              f"${t['pnl']:>+8,.2f} {t['pnl_pct']*100:>+6.2f}% {max_dd_pct:>+6.2f}% {exit_atr:>6.0f} {ref_atr:>6.0f} {t['exit_reason']}")

    # ─── Regime-Based Trade Log ───────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  TRADE LOG BY REGIME")
    print(f"{'─' * 70}")

    df_ohlcv = df[["open", "high", "low", "close", "volume"]].copy()
    strategies = ["pelt_directional", "pelt_volatility", "l1_trend"]

    for strat_name in strategies:
        segments, regime_labels = detect_regimes(df_ohlcv, strategy=strat_name)

        regime_trade_map: dict[str, list] = {}
        for t in trades:
            entry_date = t.get("entry_date")
            if entry_date is None:
                continue
            entry_ts = pd.Timestamp(entry_date)
            if entry_ts in regime_labels.index:
                regime = regime_labels.loc[entry_ts]
            else:
                idx = regime_labels.index.get_indexer([entry_ts], method="ffill")[0]
                regime = regime_labels.iloc[idx] if idx >= 0 else "UNKNOWN"
            regime_trade_map.setdefault(regime, []).append(t)

        print(f"\n  [{strat_name}]")
        for regime in sorted(regime_trade_map.keys()):
            rtrades = regime_trade_map[regime]
            wins = sum(1 for t in rtrades if t["pnl"] > 0)
            total_pnl = sum(t["pnl"] for t in rtrades)
            wr = wins / len(rtrades) * 100 if rtrades else 0
            print(f"\n    {regime} ({len(rtrades)} trades, WR: {wr:.0f}%, PnL: ${total_pnl:+,.2f})")
            print(f"    {'#':<4} {'Entry':<18} {'Exit':<18} {'PnL%':>7} {'Reason'}")
            print(f"    {'─' * 60}")
            for j, t in enumerate(rtrades, 1):
                entry_dt = t["entry_date"].strftime("%Y-%m-%d %H:%M")
                exit_dt = t["exit_date"].strftime("%Y-%m-%d %H:%M")
                print(f"    {j:<4} {entry_dt:<18} {exit_dt:<18} {t['pnl_pct']*100:>+6.2f}% {t['exit_reason']}")

    # ─── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'═' * 70}")
    print("  SUMMARY")
    print(f"{'═' * 70}")
    print(f"  Return: {report['total_return_pct']:+.2f}%  |  Sharpe: {report['sharpe_ratio']:.3f}  |  "
          f"Drawdown: {report['max_drawdown_pct']:.2f}%  |  Trades: {report['total_trades']}")
    print(f"  Win rate: {report['win_rate']:.1f}%  |  TP hits: {tp_count}  |  SL hits: {sl_count}")
    print(f"{'═' * 70}")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n  FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
