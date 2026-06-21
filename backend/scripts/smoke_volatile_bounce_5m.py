"""
Golden Cross Strategy — Trend-Following

Entry: SMA50 crosses above SMA200 (bullish crossover)
Exit: SMA50 crosses below SMA200 (bearish crossover)

Usage:
  python scripts/smoke_volatile_bounce_5m.py
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


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TICKER = "^NSEI"
START = "2001-01-01"
END = "2026-05-08"
TF = "1d"
ASSET_CLASS = "STOCK"
INITIAL_CAPITAL = 10_000.0

INDICATORS = [
    {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    {"indicator_type": "SMA", "alias": "sma_200", "params": {"period": 200, "source": "close"}},
    {"indicator_type": "ATR", "alias": "atr_14", "params": {"period": 14}},
]

# Entry conditions (volume filter applied separately as custom logic)
# LONG_ENTRY_GROUP = {
#     "logic": "AND",
#     "conditions": [
#         {
#             "left_operand_type": "EXPRESSION",
#             "left_operand_value": "high - low",
#             "operator": "GTE",
#             "right_operand_type": "EXPRESSION",
#             "right_operand_value": f"low * {RANGE_THRESHOLD}",
#         },
#         {
#             "left_operand_type": "OHLCV",
#             "left_operand_value": "close",
#             "operator": "LT",
#             "right_operand_type": "OHLCV",
#             "right_operand_value": "open",
#         },
#     ],
# }


entry_group = {
    "logic": "AND",
    "conditions": [
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "sma_50",
            "operator": "CROSSES_ABOVE",
            "right_operand_type": "INDICATOR",
            "right_operand_value": "sma_200",
        }
    ],
}

exit_group = {
    "logic": "AND",
    "conditions": [
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "sma_50",
            "operator": "CROSSES_BELOW",
            "right_operand_type": "INDICATOR",
            "right_operand_value": "sma_200",
        }
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


def run_backtest_on_df(df, initial_capital: float = INITIAL_CAPITAL) -> tuple[list[dict], dict]:
    # Entry: SMA50 crosses above SMA200 (golden cross)
    entry_signal = evaluate_conditions(df, entry_group)

    # Exit: SMA50 crosses below SMA200 (death cross)
    exit_signal = evaluate_conditions(df, exit_group)

    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        initial_capital=initial_capital,
        asset_class=ASSET_CLASS,
        # periodic_contribution={"amount": 10000, "frequency": "monthly"},
        enable_attribution=False,
        # stop_loss_pct=6
    )

    report = generate_report(trades, equity_curve, initial_capital)
    report['equity_curve'] = equity_curve  # Add equity curve to report
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
    print("║                  GOLDEN CROSS STRATEGY                               ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"  Ticker: {TICKER}  | TF: {TF} | Period: {START} to {END} | Capital: ${INITIAL_CAPITAL:,.0f}")
    print(f"  Entry: SMA50 crosses above SMA200 (golden cross)")
    print(f"  Exit:  SMA50 crosses below SMA200 (death cross)")

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
    # base_signal = evaluate_conditions(df, LONG_ENTRY_GROUP)
    # max_vol_since_cross = compute_max_volume_since_cross(df)
    # volume_is_highest = df["volume"] >= max_vol_since_cross
    # bullish_cross_filter = last_cross_was_bullish(df)
    # entry_signal = base_signal & volume_is_highest & bullish_cross_filter
    # print(f"  Entry signals: {entry_signal.sum()} (base: {base_signal.sum()}, +vol: {(base_signal & volume_is_highest).sum()}, +bull cross: {entry_signal.sum()})")

    # ─── Stage 2: Backtest ────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  2. BACKTEST RESULTS")
    print(f"{'─' * 70}")

    trades, report = run_backtest_on_df(df)
    equity_curve = report.get('equity_curve', pd.Series([INITIAL_CAPITAL]))

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

    # ─── Rolling Returns ──────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  3. ROLLING RETURNS")
    print(f"{'─' * 70}")

    # Calculate rolling returns for different windows
    windows = [252, 504, 756]  # 1Y, 2Y, 3Y in trading days
    window_labels = ["1-Year", "2-Year", "3-Year"]

    print(f"\n  {'Window':<12} {'Best':>10} {'Worst':>10} {'Avg':>10} {'Median':>10} {'StdDev':>10}")
    print(f"  {'─' * 65}")

    for window, label in zip(windows, window_labels):
        if len(equity_curve) > window:
            rolling_returns = []
            for i in range(window, len(equity_curve)):
                start_val = equity_curve.iloc[i - window]
                end_val = equity_curve.iloc[i]
                ret = (end_val - start_val) / start_val * 100
                rolling_returns.append(ret)

            if rolling_returns:
                best = max(rolling_returns)
                worst = min(rolling_returns)
                avg = sum(rolling_returns) / len(rolling_returns)
                median = sorted(rolling_returns)[len(rolling_returns) // 2]
                std = (sum((x - avg) ** 2 for x in rolling_returns) / len(rolling_returns)) ** 0.5

                print(f"  {label:<12} {best:>+9.2f}% {worst:>+9.2f}% {avg:>+9.2f}% {median:>+9.2f}% {std:>9.2f}%")
            else:
                print(f"  {label:<12} {'N/A':>10} {'N/A':>10} {'N/A':>10} {'N/A':>10} {'N/A':>10}")
        else:
            print(f"  {label:<12} {'(insufficient data)':>54}")

    # Exit reason breakdown
    tp_count = sum(1 for t in trades if t.get("exit_reason") == "take_profit")
    sl_count = sum(1 for t in trades if t.get("exit_reason") == "stop_loss")
    signal_count = sum(1 for t in trades if t.get("exit_reason") == "signal")
    other_count = len(trades) - tp_count - sl_count - signal_count

    print(f"\n  Exit reasons:")
    if signal_count:
        print(f"    Signal (death cross): {signal_count}")
    if tp_count:
        print(f"    Take profit:          {tp_count}")
    if sl_count:
        print(f"    Stop loss:            {sl_count}")
    if other_count:
        print(f"    Other (force close):  {other_count}")

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

    # ─── Trade Log ────────────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  TRADE LOG")
    print(f"{'─' * 70}")
    # atr_mean_24_col = df["atr_mean_24"]
    print(f"  {'#':<4} {'Entry':<18} {'Exit':<18} {'Entry$':>9} {'Exit$':>9} {'PnL':>9} {'PnL%':>7} {'MDD%':>7} {'Reason'}")
    print(f"  {'─' * 95}")
    for i, t in enumerate(trades, 1):
        entry_dt = t["entry_date"].strftime("%Y-%m-%d %H:%M")
        exit_dt = t["exit_date"].strftime("%Y-%m-%d %H:%M")
        exit_loc = df.index.get_loc(t["exit_date"])
        entry_loc = df.index.get_loc(t["entry_date"])
        entry_price = t["entry_price"]
        trade_lows = df.iloc[entry_loc:exit_loc + 1]["low"]
        max_dd_pct = (trade_lows.min() - entry_price) / entry_price * 100
        print(f"  {i:<4} {entry_dt:<18} {exit_dt:<18} ${t['entry_price']:>8,.0f} ${t['exit_price']:>8,.0f} "
              f"${t['pnl']:>+8,.2f} {t['pnl_pct']*100:>+6.2f}% {max_dd_pct:>+6.2f}% {t['exit_reason']}")

    # # ─── Stage 3: Regime Detection ────────────────────────────────────────────
    # print(f"\n{'─' * 70}")
    # print("  3. REGIME DETECTION")
    # print(f"{'─' * 70}")
    #
    # df_ohlcv = df[["open", "high", "low", "close", "volume"]].copy()
    # strategies = ["pelt_directional", "pelt_volatility", "l1_trend"]
    #
    # for strat_name in strategies:
    #     segments, regime_labels = detect_regimes(df_ohlcv, strategy=strat_name)
    #     regime_metrics = analyze_trades_by_regime(trades, regime_labels)
    #     distribution = calculate_regime_distribution(regime_labels)
    #     dependency_level, dependency_score = assess_regime_dependency(regime_metrics)
    #
    #     print(f"\n  [{strat_name}]  Segments: {len(segments)}  |  Dependency: {dependency_level} (CV={dependency_score:.2f})")
    #
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
    #
    # windows = generate_windows(df, window_count=5)
    #
    # window_results = []
    # print(f"\n  {'Window':<8} {'Period':<27} {'Trades':>7} {'Return':>8} {'Sharpe':>8} {'Win%':>6}")
    # print(f"  {'─' * 68}")
    #
    # for w in windows:
    #     df_window = df.iloc[w.start_idx:w.end_idx + 1]
    #
    #     if len(df_window) < 30:
    #         window_results.append({"metrics": {"total_trades": 0}})
    #         print(f"  {w.index:<8} {str(w.start_date) + ' → ' + str(w.end_date):<27} {'(insufficient data)':>31}")
    #         continue
    #
    #     _, report_w = run_backtest_on_df(df_window)
    #     metrics_w = extract_metrics(report_w)
    #     window_results.append({"metrics": metrics_w})
    #
    #     period = f"{w.start_date} → {w.end_date}"
    #     print(f"  {w.index:<8} {period:<27} {metrics_w['total_trades']:>7} "
    #           f"{metrics_w['total_return_pct']:>+7.2f}% {metrics_w['sharpe_ratio']:>8.3f} {metrics_w['win_rate']:>5.1f}%")
    #
    # consistency_score, metric_cvs = calculate_consistency_score(window_results, min_trades=3)
    # assessment = assess_walk_forward_results(window_results, consistency_score, min_trades=3)
    #
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
    print(f"  Win rate: {report['win_rate']:.1f}%")
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
