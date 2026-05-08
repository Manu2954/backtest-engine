"""
Volatile Bearish Bar — Mean-Reversion Strategy

Entry: Buy after a bearish 1h candle with high-low range >= 2%
  - (high - low) >= low * 0.02   (2% range)
  - close < open                  (bearish candle)
  - volume is highest since last SMA50/SMA200 crossover

Exit: Dynamic TP = bar's range %, Stop loss -1%

Usage:
  python scripts/smoke_volatile_bounce.py
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
from app.engine.exit_rules import ExitRule

from app.engine.robustness.regime_detection import (
    detect_regimes,
    analyze_trades_by_regime,
    calculate_regime_distribution,
    assess_regime_dependency,
)
from app.engine.robustness.walk_forward import (
    generate_windows,
    calculate_consistency_score,
    assess_walk_forward_results,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TICKER = "BTCUSDT"
START = "2023-01-01"
END = "2026-05-08"
TF = "5m"
ASSET_CLASS = "CRYPTO"
INITIAL_CAPITAL = 10_000.0

RANGE_THRESHOLD = 0.02    # 2% high-low range
STOP_LOSS_PCT = None   # Exit at -1%

INDICATORS = [
    {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    {"indicator_type": "SMA", "alias": "sma_200", "params": {"period": 200, "source": "close"}},
    {"indicator_type": "ATR", "alias": "atr_14", "params": {"period": 14}},
    {"indicator_type": "RSI", "alias": "rsi_14", "params": {"period": 14}},
]

# Entry conditions (volume filter applied separately as custom logic)
LONG_ENTRY_GROUP = {
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
            "operator": "LT",
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
    """
    For each bar, compute the max volume since the last SMA50/SMA200 crossover.
    Returns a Series of the running max volume within each cross-segment.
    """
    cross = (
        ((df["sma_50"] > df["sma_200"]) & (df["sma_50"].shift(1) <= df["sma_200"].shift(1))) |
        ((df["sma_50"] < df["sma_200"]) & (df["sma_50"].shift(1) >= df["sma_200"].shift(1)))
    )

    # Assign a segment ID that increments at each crossover
    segment_id = cross.cumsum()

    # Rolling max volume within each segment
    max_vol = df.groupby(segment_id)["volume"].cummax()
    return max_vol


def last_cross_was_bullish(df: pd.DataFrame) -> pd.Series:
    """
    For each bar, True if the most recent SMA50/SMA200 crossover was
    a bullish cross (50 crossed above 200).
    """
    bull_cross = (df["sma_50"] > df["sma_200"]) & (df["sma_50"].shift(1) <= df["sma_200"].shift(1))
    bear_cross = (df["sma_50"] < df["sma_200"]) & (df["sma_50"].shift(1) >= df["sma_200"].shift(1))

    # Track which type of cross happened last: 1 = bullish, -1 = bearish
    cross_type = pd.Series(0, index=df.index)
    cross_type[bull_cross] = 1
    cross_type[bear_cross] = -1

    # Forward-fill to carry last cross type
    cross_type = cross_type.replace(0, np.nan).ffill().fillna(0)

    return cross_type == 1


def run_backtest_on_df(df, initial_capital: float = INITIAL_CAPITAL) -> tuple[list[dict], dict]:
    # Base conditions from condition engine
    base_signal = evaluate_conditions(df, LONG_ENTRY_GROUP)

    # Volume filter: bar's volume must be the highest since last MA cross
    max_vol_since_cross = compute_max_volume_since_cross(df)
    volume_is_highest = df["volume"] >= max_vol_since_cross

    # Trend filter: last crossover must be bullish (50 above 200)
    bullish_cross_filter = last_cross_was_bullish(df)

    # ATR filter: ATR of signal candle > mean of 24 candles before it (excluding current)
    atr_mean_24 = df["atr_14"].shift(1).rolling(24).mean()
    df["atr_mean_24"] = atr_mean_24
    atr_above_mean = df["atr_14"] > atr_mean_24

    # Body > wick filter: candle body must be larger than total wicks
    body = (df["open"] - df["close"]).abs()
    upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
    lower_wick = df[["open", "close"]].min(axis=1) - df["low"]
    total_wick = upper_wick + lower_wick
    body_gt_wick = body > total_wick

    # Combined entry signal
    entry_signal = base_signal & volume_is_highest & bullish_cross_filter & atr_above_mean & body_gt_wick

    # Deferred entry: wait for close > SMA50 after signal fires
    above_sma50 = df["close"] > df["sma_50"]
    deferred_signal = pd.Series(False, index=df.index)
    armed = False
    # for i in range(len(df)):
    #     if entry_signal.iloc[i]:
    #         armed = True
    #     if armed and above_sma50.iloc[i]:
    #         deferred_signal.iloc[i] = True
    #         armed = False
    # entry_signal = deferred_signal

    # Exit: ATR < mean ATR (fixed at entry) AND losing >= 1% AND price crosses below SMA200
    crossed_below_sma200 = (df["close"] < df["sma_200"]) & (df["close"].shift(1) >= df["sma_200"].shift(1))
    df["skip_atr_exit"] = ~crossed_below_sma200  # skip when NOT crossing below

    exit_signal = pd.Series(False, index=df.index)

    # Exit rules (engine-level)
    atr_exit = ExitRule(name="atr_exit", ref_col="atr_mean_24", monitor_col="atr_14", min_loss_pct=1.0, skip_col="skip_atr_exit")
    rsi_exit = ExitRule(name="rsi_exit", ref_col="rsi_14", monitor_col="rsi_14", activation_threshold=30.0, min_loss_pct=1.0)
    rsi_20exit = ExitRule(name="rsi_20", monitor_col="rsi_14", fixed_threshold=30.0, min_loss_pct=1.0)
    
    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=initial_capital,
        asset_class=ASSET_CLASS,
        position_size_type="percent_capital",
        position_size_value=50.0,
        stop_loss_pct=STOP_LOSS_PCT,
        take_profit_pct=5.0,
        commission_per_trade=1.0,
        slippage_pct=0.0,
        enable_attribution=False,
        # exit_rules=[atr_exit, rsi_exit, rsi_20exit],
        exit_rules=[atr_exit],
        leverage=5
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
    print("║           VOLATILE BEARISH BAR — MEAN-REVERSION                     ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"  Ticker: {TICKER}  | TF: {TF} | Period: {START} to {END} | Capital: ${INITIAL_CAPITAL:,.0f}")
    print(f"  Entry: bearish candle with (high-low)/low >= {RANGE_THRESHOLD*100:.1f}%")
    print(f"         + volume is highest since last SMA50/SMA200 crossover")
    print(f"         + last crossover was bullish (SMA50 > SMA200)")
    print(f"  Exit:  TP = bar's range %  |  SL -{STOP_LOSS_PCT}%")

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
    base_signal = evaluate_conditions(df, LONG_ENTRY_GROUP)
    max_vol_since_cross = compute_max_volume_since_cross(df)
    volume_is_highest = df["volume"] >= max_vol_since_cross
    bullish_cross_filter = last_cross_was_bullish(df)
    entry_signal = base_signal & volume_is_highest & bullish_cross_filter
    print(f"  Entry signals: {entry_signal.sum()} (base: {base_signal.sum()}, +vol: {(base_signal & volume_is_highest).sum()}, +bull cross: {entry_signal.sum()})")

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
    print(f"    Take profit (dynamic): {tp_count}")
    print(f"    Stop loss (-{STOP_LOSS_PCT}%):   {sl_count}")
    if other_count:
        print(f"    Other (force close):   {other_count}")

    # ─── Signal Log ────────────────────────────────────────────────────────────
    # print(f"\n{'─' * 70}")
    # print("  SIGNAL LOG (entry signals fired)")
    # print(f"{'─' * 70}")
    # print(f"  {'#':<4} {'Timestamp':<18} {'Close':>9} {'Range%':>8} {'Volume':>12} {'MaxVol':>12}")
    # print(f"  {'─' * 68}")
    # signal_bars = df[entry_signal]
    # for i, (idx, row) in enumerate(signal_bars.iterrows(), 1):
    #     ts_str = idx.strftime("%Y-%m-%d %H:%M")
    #     hl_pct = (row["high"] - row["low"]) / row["low"] * 100
    #     max_v = max_vol_since_cross.loc[idx]
    #     print(f"  {i:<4} {ts_str:<18} ${row['close']:>8,.0f} {hl_pct:>+7.2f}% {row['volume']:>11,.0f} {max_v:>11,.0f}")

    # ─── Trade Log (grouped by exit reason) ─────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  TRADE LOG (grouped by exit reason)")
    print(f"{'─' * 70}")
    atr_mean_24_col = df["atr_mean_24"]

    # Group trades by exit reason
    from collections import defaultdict
    grouped: dict[str, list] = defaultdict(list)
    for t in trades:
        grouped[t["exit_reason"]].append(t)

    # Compute running capital per trade (chronological order)
    capital_after_trade = {}
    running_capital = INITIAL_CAPITAL
    for t in sorted(trades, key=lambda x: x["exit_date"]):
        running_capital += t["pnl"]
        capital_after_trade[id(t)] = running_capital

    header = f"  {'#':<4} {'Entry':<16} {'Exit':<16} {'PnL':>10} {'PnL%':>8} {'MDD%':>7} {'eATR':>6} {'rATR':>6} {'eRSI':>5} {'Capital':>11}"
    separator = f"  {'─' * 100}"

    for reason in sorted(grouped.keys()):
        group = grouped[reason]
        group_pnl = sum(t["pnl"] for t in group)
        group_wins = sum(1 for t in group if t["pnl"] > 0)
        group_wr = group_wins / len(group) * 100 if group else 0
        print(f"\n  [{reason}] — {len(group)} trades | WR: {group_wr:.0f}% | PnL: ${group_pnl:+,.2f}")
        print(header)
        print(separator)
        for i, t in enumerate(group, 1):
            entry_dt = t["entry_date"].strftime("%Y-%m-%d %H:%M")
            exit_dt = t["exit_date"].strftime("%Y-%m-%d %H:%M")
            exit_loc = df.index.get_loc(t["exit_date"])
            entry_loc = df.index.get_loc(t["entry_date"])
            signal_loc = max(entry_loc - 1, 0)
            exit_atr = df.iloc[exit_loc]["atr_14"]
            ref_atr = atr_mean_24_col.iloc[signal_loc]
            entry_rsi = df.iloc[signal_loc]["rsi_14"]
            entry_price = t["entry_price"]
            trade_lows = df.iloc[entry_loc:exit_loc + 1]["low"]
            max_dd_pct = (trade_lows.min() - entry_price) / entry_price * 100
            cap = capital_after_trade[id(t)]
            print(f"  {i:<4} {entry_dt:<16} {exit_dt:<16} "
                  f"${t['pnl']:>+9,.2f} {t['pnl_pct']*100:>+7.2f}% {max_dd_pct:>+6.2f}% {exit_atr:>6.0f} {ref_atr:>6.0f} {entry_rsi:>5.1f} ${cap:>10,.2f}")

    # ─── Complete Trade Log (chronological) ───────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  COMPLETE TRADE LOG (chronological)")
    print(f"{'─' * 70}")
    chr_header = f"  {'#':<4} {'Entry':<16} {'Exit':<16} {'PnL':>10} {'PnL%':>8} {'MDD%':>7} {'eATR':>6} {'rATR':>6} {'eRSI':>5} {'Capital':>11} {'Reason':<12}"
    print(chr_header)
    print(f"  {'─' * 112}")
    for i, t in enumerate(sorted(trades, key=lambda x: x["exit_date"]), 1):
        entry_dt = t["entry_date"].strftime("%Y-%m-%d %H:%M")
        exit_dt = t["exit_date"].strftime("%Y-%m-%d %H:%M")
        exit_loc = df.index.get_loc(t["exit_date"])
        entry_loc = df.index.get_loc(t["entry_date"])
        signal_loc = max(entry_loc - 1, 0)
        exit_atr = df.iloc[exit_loc]["atr_14"]
        ref_atr = atr_mean_24_col.iloc[signal_loc]
        entry_rsi = df.iloc[signal_loc]["rsi_14"]
        entry_price = t["entry_price"]
        trade_lows = df.iloc[entry_loc:exit_loc + 1]["low"]
        max_dd_pct = (trade_lows.min() - entry_price) / entry_price * 100
        cap = capital_after_trade[id(t)]
        print(f"  {i:<4} {entry_dt:<16} {exit_dt:<16} "
              f"${t['pnl']:>+9,.2f} {t['pnl_pct']*100:>+7.2f}% {max_dd_pct:>+6.2f}% {exit_atr:>6.0f} {ref_atr:>6.0f} {entry_rsi:>5.1f} ${cap:>10,.2f} {t['exit_reason']:<12}")

    # ─── Regime-Based Trade Log ───────────────────────────────────────────────
    # print(f"\n{'─' * 70}")
    # print("  TRADE LOG BY REGIME")
    # print(f"{'─' * 70}")

    # df_ohlcv = df[["open", "high", "low", "close", "volume"]].copy()
    # strategies = ["pelt_directional", "pelt_volatility", "l1_trend"]

    # for strat_name in strategies:
    #     segments, regime_labels = detect_regimes(df_ohlcv, strategy=strat_name)

    #     # Group trades by regime at entry
    #     regime_trade_map: dict[str, list] = {}
    #     for t in trades:
    #         entry_date = t.get("entry_date")
    #         if entry_date is None:
    #             continue
    #         # Find regime at entry
    #         entry_ts = pd.Timestamp(entry_date)
    #         if entry_ts in regime_labels.index:
    #             regime = regime_labels.loc[entry_ts]
    #         else:
    #             idx = regime_labels.index.get_indexer([entry_ts], method="ffill")[0]
    #             regime = regime_labels.iloc[idx] if idx >= 0 else "UNKNOWN"
    #         regime_trade_map.setdefault(regime, []).append(t)

    #     print(f"\n  [{strat_name}]")
    #     for regime in sorted(regime_trade_map.keys()):
    #         rtrades = regime_trade_map[regime]
    #         wins = sum(1 for t in rtrades if t["pnl"] > 0)
    #         total_pnl = sum(t["pnl"] for t in rtrades)
    #         wr = wins / len(rtrades) * 100 if rtrades else 0
    #         print(f"\n    {regime} ({len(rtrades)} trades, WR: {wr:.0f}%, PnL: ${total_pnl:+,.2f})")
    #         print(f"    {'#':<4} {'Entry':<18} {'Exit':<18} {'PnL%':>7} {'Reason'}")
    #         print(f"    {'─' * 60}")
    #         for j, t in enumerate(rtrades, 1):
    #             entry_dt = t["entry_date"].strftime("%Y-%m-%d %H:%M")
    #             exit_dt = t["exit_date"].strftime("%Y-%m-%d %H:%M")
    #             print(f"    {j:<4} {entry_dt:<18} {exit_dt:<18} {t['pnl_pct']*100:>+6.2f}% {t['exit_reason']}")
    # print(f"\n{'─' * 70}")
    # print("  3. REGIME DETECTION")
    # print(f"{'─' * 70}")
    
    # df_ohlcv = df[["open", "high", "low", "close", "volume"]].copy()
    # strategies = ["pelt_directional", "pelt_volatility", "l1_trend"]
    
    # for strat_name in strategies:
    #     segments, regime_labels = detect_regimes(df_ohlcv, strategy=strat_name)
    #     regime_metrics = analyze_trades_by_regime(trades, regime_labels)
    #     distribution = calculate_regime_distribution(regime_labels)
    #     dependency_level, dependency_score = assess_regime_dependency(regime_metrics)
    
    #     print(f"\n  [{strat_name}]  Segments: {len(segments)}  |  Dependency: {dependency_level} (CV={dependency_score:.2f})")
    
    #     print(f"    {'Regime':<12} {'Time%':>6} {'Trades':>7} {'Win Rate':>10} {'Return':>9}")
    #     print(f"    {'─' * 48}")
    #     for regime in sorted(distribution.keys()):
    #         pct = distribution[regime]
    #         m = regime_metrics.get(regime, {})
    #         t_count = m.get("total_trades", 0)
    #         wr = m.get("win_rate", 0)
    #         ret = m.get("total_return_pct", 0)
    #         print(f"    {regime:<12} {pct:>5.1f}% {t_count:>7} {wr:>9.1f}% {ret:>+8.2f}%")

    # # ─── Stage 4: Walk-Forward Validation ─────────────────────────────────────
    # print(f"\n{'─' * 70}")
    # print("  4. WALK-FORWARD VALIDATION")
    # print(f"{'─' * 70}")
    
    # windows = generate_windows(df, window_count=5)
    
    # window_results = []
    # print(f"\n  {'Window':<8} {'Period':<27} {'Trades':>7} {'Return':>8} {'Sharpe':>8} {'Win%':>6}")
    # print(f"  {'─' * 68}")
    
    # for w in windows:
    #     df_window = df.iloc[w.start_idx:w.end_idx + 1]
    
    #     if len(df_window) < 30:
    #         window_results.append({"metrics": {"total_trades": 0}})
    #         print(f"  {w.index:<8} {str(w.start_date) + ' → ' + str(w.end_date):<27} {'(insufficient data)':>31}")
    #         continue
    
    #     _, report_w = run_backtest_on_df(df_window)
    #     metrics_w = extract_metrics(report_w)
    #     window_results.append({"metrics": metrics_w})
    
    #     period = f"{w.start_date} → {w.end_date}"
    #     print(f"  {w.index:<8} {period:<27} {metrics_w['total_trades']:>7} "
    #           f"{metrics_w['total_return_pct']:>+7.2f}% {metrics_w['sharpe_ratio']:>8.3f} {metrics_w['win_rate']:>5.1f}%")
    
    # consistency_score, metric_cvs = calculate_consistency_score(window_results, min_trades=3)
    # assessment = assess_walk_forward_results(window_results, consistency_score, min_trades=3)
    
    # print(f"\n  Consistency: {consistency_score:.3f}  →  {assessment['level']}")
    # if assessment.get("risk_flags"):
    #     for flag in assessment["risk_flags"]:
    #         print(f"    ! {flag}")

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
