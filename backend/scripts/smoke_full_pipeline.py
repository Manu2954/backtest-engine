"""
Full Pipeline — End-to-End Backtest + Robustness Analysis

Strategy: Crash Bounce — Buy after 1.5% drop in 1h (Long Only, BTCUSDT 5m)
  - Long entry:  close < close:-12 * 0.985 AND RSI(5) < 25
  - Long exit:   RSI(5) > 60

Pipeline:
  1. Data fetch + indicators
  2. Backtest (long only)
  3. Regime detection (all 3 strategies)
  4. Parameter sensitivity analysis
  5. Walk-forward validation
  6. Feature conditioning
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

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
from app.engine.robustness.parameter_sensitivity import (
    generate_parameter_variants,
    calculate_stability_score,
    assess_robustness_level,
    generate_risk_flags,
    generate_recommendation,
)
from app.engine.robustness.walk_forward import (
    generate_windows,
    calculate_consistency_score,
    assess_walk_forward_results,
)
from app.engine.robustness.feature_conditioning import (
    extract_trade_features,
    analyze_feature_conditions,
    build_feature_conditioning_report,
)


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY CONFIGURATION — Edit this section to test your strategies
# ═══════════════════════════════════════════════════════════════════════════════

TICKER = "BTCUSDT"
START = "2025-01-01"
END = "2025-03-31"
INITIAL_CAPITAL = 10_000.0
ASSET_CLASS = "CRYPTO"
TF = "5m"

# Crash Bounce Strategy — Buy the dip after a sharp 1h drop
INDICATORS = [
    {"indicator_type": "RSI", "alias": "rsi_5", "params": {"period": 5, "source": "close"}},
    {"indicator_type": "ATR", "alias": "atr_14", "params": {"period": 14}},
]

# Long entry: price dropped >1.5% in 1h (12 bars) AND RSI confirms oversold
LONG_ENTRY_GROUP = {
    "logic": "AND",
    "conditions": [
        {
            "left_operand_type": "OHLCV",
            "left_operand_value": "close",
            "operator": "LT",
            "right_operand_type": "EXPRESSION",
            "right_operand_value": "close:-12 * 0.985",
        },
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "rsi_5",
            "operator": "LT",
            "right_operand_type": "SCALAR",
            "right_operand_value": "25",
        },
    ],
}

# Long exit: RSI recovers above 60 (bounce played out)
LONG_EXIT_GROUP = {
    "logic": "AND",
    "conditions": [
        {
            "left_operand_type": "INDICATOR",
            "left_operand_value": "rsi_5",
            "operator": "GT",
            "right_operand_type": "SCALAR",
            "right_operand_value": "60",
        },
    ],
}

# No short side
SHORT_ENTRY_GROUP = None
SHORT_EXIT_GROUP = None


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE — No need to edit below this line
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest_on_df(
    df,
    initial_capital: float = INITIAL_CAPITAL,
) -> tuple[list[dict], dict]:
    """Run backtest on a DataFrame with indicators already computed."""
    long_entry = evaluate_conditions(df, LONG_ENTRY_GROUP)
    long_exit = evaluate_conditions(df, LONG_EXIT_GROUP)

    short_entry = None
    short_exit = None
    if SHORT_ENTRY_GROUP and SHORT_EXIT_GROUP:
        short_entry = evaluate_conditions(df, SHORT_ENTRY_GROUP)
        short_exit = evaluate_conditions(df, SHORT_EXIT_GROUP)

    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=long_entry,
        exit_signal=long_exit,
        initial_capital=initial_capital,
        asset_class=ASSET_CLASS,
        position_size_type="percent_capital",
        position_size_value=50.0,
        stop_loss_pct=5.0,
        commission_per_trade=1.0,
        slippage_pct=0.05,
        enable_attribution=False,
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
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
    print("║           FULL PIPELINE — STRATEGY EVALUATION                       ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"  Ticker: {TICKER}  | Timeframe: {TF} | Period: {START} to {END}  |  Capital: ${INITIAL_CAPITAL:,.0f}")
    print(f"  Asset: {ASSET_CLASS}  |  Sizing: 50% capital  |  Stop: 5%")
    print()
    print("  Strategy:")
    print(f"    Indicators: {', '.join(i['alias'] for i in INDICATORS)}")
    for cond in LONG_ENTRY_GROUP["conditions"]:
        print(f"    Long entry:  {cond['left_operand_value']} {cond['operator']} {cond['right_operand_value']}")
    for cond in LONG_EXIT_GROUP["conditions"]:
        print(f"    Long exit:   {cond['left_operand_value']} {cond['operator']} {cond['right_operand_value']}")
    if SHORT_ENTRY_GROUP:
        for cond in SHORT_ENTRY_GROUP["conditions"]:
            print(f"    Short entry: {cond['left_operand_value']} {cond['operator']} {cond['right_operand_value']}")
    if SHORT_EXIT_GROUP:
        for cond in SHORT_EXIT_GROUP["conditions"]:
            print(f"    Short exit:  {cond['left_operand_value']} {cond['operator']} {cond['right_operand_value']}")

    # ─── Stage 1: Data ────────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  1. DATA")
    print(f"{'─' * 70}")

    df_raw = fetch_ohlcv(TICKER, START, END, TF, ASSET_CLASS)
    with contextlib.redirect_stdout(io.StringIO()):
        df = compute_indicators(df_raw.copy(), INDICATORS)
        df, warmup_bars = trim_warmup_period(df)

    print(f"  Bars fetched: {len(df_raw)}  |  After warmup trim: {len(df)}  |  Warmup: {warmup_bars} bars")

    # ─── Stage 2: Backtest ────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  2. BACKTEST RESULTS")
    print(f"{'─' * 70}")

    trades, report = run_backtest_on_df(df)
    long_trades = [t for t in trades if t.get("direction") == "LONG"]
    short_trades = [t for t in trades if t.get("direction") == "SHORT"]

    print(f"  {'Metric':<24} {'Value':>12}")
    print(f"  {'─' * 38}")
    print(f"  {'Total return':<24} {report['total_return_pct']:>+11.2f}%")
    print(f"  {'CAGR':<24} {report.get('cagr', 0):>+11.2f}%")
    print(f"  {'Sharpe ratio':<24} {report['sharpe_ratio']:>12.3f}")
    print(f"  {'Max drawdown':<24} {report['max_drawdown_pct']:>11.2f}%")
    print(f"  {'Longest drawdown':<24} {report.get('longest_drawdown_days', 0):>10} days")
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

    if long_trades and short_trades:
        ls = report.get("long_trades_summary", {})
        ss = report.get("short_trades_summary", {})
        print(f"\n  {'Direction':<8} {'Trades':>7} {'Win Rate':>10} {'Avg PnL':>10} {'Total PnL':>12}")
        print(f"  {'─' * 50}")
        if ls:
            print(f"  {'LONG':<8} {ls['total_trades']:>7} {ls['win_rate']:>9.1f}% "
                  f"${ls['avg_pnl']:>8,.2f} ${ls['total_pnl']:>10,.2f}")
        if ss:
            print(f"  {'SHORT':<8} {ss['total_trades']:>7} {ss['win_rate']:>9.1f}% "
                  f"${ss['avg_pnl']:>8,.2f} ${ss['total_pnl']:>10,.2f}")

    # ─── Stage 3: Regime Detection ────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  3. REGIME DETECTION")
    print(f"{'─' * 70}")

    MAX_BARS_REGIME = 30_000

    if len(df) > MAX_BARS_REGIME:
        print(f"\n  SKIPPED — {len(df):,} bars exceeds {MAX_BARS_REGIME:,} limit for PELT segmentation.")
        print(f"  Reduce date range or use higher timeframe to enable regime detection.")
    else:
        df_ohlcv = df[["open", "high", "low", "close", "volume"]].copy()
        strategies = ["pelt_directional", "pelt_volatility", "l1_trend"]

        for strat_name in strategies:
            segments, regime_labels = detect_regimes(df_ohlcv, strategy=strat_name)
            regime_metrics = analyze_trades_by_regime(trades, regime_labels)
            distribution = calculate_regime_distribution(regime_labels)
            dependency_level, dependency_score = assess_regime_dependency(regime_metrics)

            print(f"\n  [{strat_name}]  Segments: {len(segments)}  |  Dependency: {dependency_level} (CV={dependency_score:.2f})")

            # Print regime table
            print(f"    {'Regime':<12} {'Time%':>6} {'Trades':>7} {'Win Rate':>10} {'Return':>9}")
            print(f"    {'─' * 48}")
            for regime in sorted(distribution.keys()):
                pct = distribution[regime]
                m = regime_metrics.get(regime, {})
                t_count = m.get("total_trades", 0)
                wr = m.get("win_rate", 0)
                ret = m.get("total_return_pct", 0)
                print(f"    {regime:<12} {pct:>5.1f}% {t_count:>7} {wr:>9.1f}% {ret:>+8.2f}%")

    # ─── Stage 4: Parameter Sensitivity ───────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  4. PARAMETER SENSITIVITY")
    print(f"{'─' * 70}")

    base_strategy = {"indicators": INDICATORS}
    variants = generate_parameter_variants(base_strategy, variation_pct=0.2)

    baseline_metrics = extract_metrics(report)

    variant_metrics_list = []
    print(f"\n  {'Variant':<40} {'Return':>8} {'Sharpe':>8} {'Win%':>6}")
    print(f"  {'─' * 64}")
    print(f"  {'BASELINE':<40} {baseline_metrics['total_return_pct']:>+7.2f}% {baseline_metrics['sharpe_ratio']:>8.3f} {baseline_metrics['win_rate']:>5.1f}%")

    for v in variants:
        variant_indicators = v["strategy"]["indicators"]
        with contextlib.redirect_stdout(io.StringIO()):
            df_variant = compute_indicators(df_raw.copy(), variant_indicators)
            df_variant, _ = trim_warmup_period(df_variant)

        if len(df_variant) < 50:
            continue

        _, variant_report = run_backtest_on_df(df_variant)
        vm = extract_metrics(variant_report)
        variant_metrics_list.append(vm)

        label = v["variant_label"]
        if len(label) > 38:
            label = label[:38] + ".."
        print(f"  {label:<40} {vm['total_return_pct']:>+7.2f}% {vm['sharpe_ratio']:>8.3f} {vm['win_rate']:>5.1f}%")

    stability_score, metric_cvs = calculate_stability_score(baseline_metrics, variant_metrics_list)
    robustness_level = assess_robustness_level(stability_score)
    risk_flags = generate_risk_flags(baseline_metrics, variant_metrics_list, metric_cvs)

    print(f"\n  Stability: {stability_score:.3f}  →  {robustness_level}")
    if risk_flags:
        for flag in risk_flags:
            print(f"    ! {flag}")

    # ─── Stage 5: Walk-Forward Validation ─────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  5. WALK-FORWARD VALIDATION")
    print(f"{'─' * 70}")

    windows = generate_windows(df, window_count=5)

    window_results = []
    print(f"\n  {'Window':<8} {'Period':<27} {'Trades':>7} {'Return':>8} {'Sharpe':>8} {'Win%':>6}")
    print(f"  {'─' * 68}")

    for w in windows:
        df_window = df.iloc[w.start_idx:w.end_idx + 1]

        if len(df_window) < 30:
            window_results.append({"metrics": {"total_trades": 0}})
            print(f"  {w.index:<8} {str(w.start_date) + ' → ' + str(w.end_date):<27} {'(insufficient data)':>31}")
            continue

        _, report_w = run_backtest_on_df(df_window)
        metrics_w = extract_metrics(report_w)
        window_results.append({"metrics": metrics_w})

        period = f"{w.start_date} → {w.end_date}"
        print(f"  {w.index:<8} {period:<27} {metrics_w['total_trades']:>7} "
              f"{metrics_w['total_return_pct']:>+7.2f}% {metrics_w['sharpe_ratio']:>8.3f} {metrics_w['win_rate']:>5.1f}%")

    consistency_score, metric_cvs = calculate_consistency_score(window_results, min_trades=5)
    assessment = assess_walk_forward_results(window_results, consistency_score, min_trades=5)

    print(f"\n  Consistency: {consistency_score:.3f}  →  {assessment['level']}")
    if assessment.get("risk_flags"):
        for flag in assessment["risk_flags"]:
            print(f"    ! {flag}")

    # ─── Stage 6: Feature Conditioning ────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  6. FEATURE CONDITIONING")
    print(f"{'─' * 70}")

    trades_with_features = extract_trade_features(trades, df, lookback_window=50)

    if not trades_with_features:
        print("  No trades matched — skipping feature analysis")
    else:
        condition_analysis = analyze_feature_conditions(trades_with_features, min_trades_per_bin=5)
        overall_metrics = extract_metrics(report)
        fc_report = build_feature_conditioning_report(trades_with_features, condition_analysis, overall_metrics)

        # Feature importance
        importance = condition_analysis.get("feature_importance", {})
        if importance:
            sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
            print(f"\n  Feature Importance:")
            for feat, score in sorted_features:
                bar = "█" * int(score * 20)
                print(f"    {feat:<20} {bar} {score:.3f}")

        # Winning conditions
        winning = condition_analysis.get("winning_conditions", [])
        if winning:
            print(f"\n  Top Winning Conditions:")
            print(f"    {'Feature':<18} {'Range':<30} {'Win%':>6} {'Avg PnL':>9} {'Trades':>7}")
            print(f"    {'─' * 72}")
            for cond in winning[:5]:
                rng = f"[{cond['range'][0]:.4f}, {cond['range'][1]:.4f}]"
                print(f"    {cond['feature']:<18} {rng:<30} {cond['win_rate']:>5.1f}% "
                      f"{cond['avg_pnl_pct']:>+8.2f}% {cond['total_trades']:>7}")

        # Losing conditions
        losing = condition_analysis.get("losing_conditions", [])
        if losing:
            print(f"\n  Top Losing Conditions (AVOID):")
            print(f"    {'Feature':<18} {'Range':<30} {'Win%':>6} {'Avg PnL':>9} {'Trades':>7}")
            print(f"    {'─' * 72}")
            for cond in losing[:5]:
                rng = f"[{cond['range'][0]:.4f}, {cond['range'][1]:.4f}]"
                print(f"    {cond['feature']:<18} {rng:<30} {cond['win_rate']:>5.1f}% "
                      f"{cond['avg_pnl_pct']:>+8.2f}% {cond['total_trades']:>7}")

        # Recommendation
        assessment_fc = fc_report.get("assessment", {})
        if assessment_fc.get("recommendation"):
            print(f"\n  Recommendation: {assessment_fc['recommendation']}")

    # ─── Final Summary ────────────────────────────────────────────────────────
    print(f"\n{'═' * 70}")
    print("  SUMMARY")
    print(f"{'═' * 70}")
    print(f"  Return: {report['total_return_pct']:+.2f}%  |  Sharpe: {report['sharpe_ratio']:.3f}  |  "
          f"Drawdown: {report['max_drawdown_pct']:.2f}%  |  Trades: {report['total_trades']}")
    print(f"  Parameter Sensitivity:  {robustness_level} ({stability_score:.3f})")
    print(f"  Walk-Forward:           {assessment['level']} ({consistency_score:.3f})")
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
