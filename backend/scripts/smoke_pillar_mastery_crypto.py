"""
Pillar-mastery smoke for CRYPTO — one script, all four pillars.

What this teaches (read the prints, not just the numbers):
  Pillar 2 DATA: Redis -> Postgres -> Binance, cache-key, gap check,
    incomplete-bar filter, resolution guard, timezone.
  Pillar 1 EXECUTION: indicators -> warmup -> conditions -> state machine
    (signal latch at i, fill at i+1 open, stops/TP/liquidation priority,
    commission/slippage, long+short, leverage, ExitRules, attribution).
  Pillar 3 MEASUREMENT: report honesty + robustness
    (walk-forward disjointness, param-sensitivity isolation,
    regime non-causality trap, feature conditioning).
  Pillar 4 OPERABILITY: sync vs async boundary, own_session/NullPool,
    timings, failure modes.

Usage:
  cd backend
  python scripts/smoke_pillar_mastery_crypto.py
"""
from __future__ import annotations

import sys
import time
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
from app.engine.robustness.walk_forward import (
    generate_windows,
    calculate_consistency_score,
)
from app.engine.robustness.parameter_sensitivity import generate_parameter_variants
from app.engine.robustness.regime_detection import detect_regimes, analyze_trades_by_regime
from app.engine.robustness.feature_conditioning import (
    extract_trade_features,
    analyze_feature_conditions,
)

TICKER = "BTCUSDT"
START = "2024-06-01"
END = "2025-01-01"
RESOLUTION = "4h"
ASSET_CLASS = "CRYPTO"
MARKET_TYPE = "SPOT"
PROVIDER = "binance"
INITIAL_CAPITAL = 1000.0


def header(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def main() -> None:
    header("PILLAR 2 — DATA: fetch path (Redis -> DB -> Binance)")
    print(f"{TICKER} {RESOLUTION} {START} -> {END} [{ASSET_CLASS}/{MARKET_TYPE}]")
    print("Learn: where cache hit saves you, where gap/incomplete-bar guards fire.")

    t0 = time.perf_counter()
    df1 = fetch_ohlcv(
        ticker=TICKER, start=START, end=END, resolution=RESOLUTION,
        asset_class=ASSET_CLASS, provider=PROVIDER, market_type=MARKET_TYPE,
    )
    t1 = time.perf_counter()
    print(f"  1st fetch (cold: DB/provider): {len(df1)} bars in {t1 - t0:.2f}s")
    print(f"  range: {df1.index.min()} -> {df1.index.max()}")

    t0 = time.perf_counter()
    df2 = fetch_ohlcv(
        ticker=TICKER, start=START, end=END, resolution=RESOLUTION,
        asset_class=ASSET_CLASS, provider=PROVIDER, market_type=MARKET_TYPE,
    )
    t1 = time.perf_counter()
    print(f"  2nd fetch (warm: Redis hit expected): {len(df2)} bars in {t1 - t0:.2f}s")
    print("  If 2nd fetch is ~ms, Redis yielded. If ~seconds, you missed cache —")
    print("  check get_cache_key inputs (ticker/resolution/start/end).")
    print("  Note: sync wrapper used here. Inside FastAPI use await fetch_ohlcv_async.")

    df = df1

    header("PILLAR 1a — INDICATORS + WARMUP (causal, no lookahead)")
    indicators = [
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50}},
        {"indicator_type": "EMA", "alias": "ema_21", "params": {"period": 21}},
        {"indicator_type": "RSI", "alias": "rsi_14", "params": {"period": 14}},
        {"indicator_type": "MACD", "alias": "macd", "params": {"fast": 12, "slow": 26, "signal": 9}},
        {"indicator_type": "ATR", "alias": "atr_14", "params": {"period": 14}},
        {"indicator_type": "BB", "alias": "bb_20", "params": {"period": 20, "std_dev": 2.0}},
        {"indicator_type": "ADX", "alias": "adx_14", "params": {"period": 14}},
        {"indicator_type": "DONCHIAN", "alias": "dc_20", "params": {"period": 20}},
        {"indicator_type": "STOCH", "alias": "stoch", "params": {"k_period": 14, "d_period": 3}},
    ]
    df = compute_indicators(df, indicators)
    print(f"  computed: {[i['alias'] for i in indicators]}")
    print(f"  columns sample: sma_50={df['sma_50'].notna().sum()}, rsi_14={df['rsi_14'].notna().sum()}")

    before = len(df)
    df, warmup = trim_warmup_period(df)
    print(f"  warmup trimmed: {warmup} bars ({before} -> {len(df)})")
    print("  Learn: warmup = first bar where ALL indicators non-NaN. No forward-fill.")

    # Helper columns for dynamic exits (must exist before run_backtest)
    df["tp_pct_col"] = 10.0  # per-trade TP% captured at entry (matches static TP below)

    header("PILLAR 1b — CONDITIONS (stateless, bar-level)")
    print("Learn: GT / CROSSES_ABOVE / IS_RISING / LOOKBACK. Right operand ignored for IS_RISING.")
    entry_group = {
        "logic": "AND",
        "conditions": [
            {"left_operand_type": "OHLCV", "left_operand_value": "close",
             "operator": "GT", "right_operand_type": "INDICATOR", "right_operand_value": "sma_50"},
            {"left_operand_type": "INDICATOR", "left_operand_value": "ema_21",
             "operator": "IS_RISING", "right_operand_type": "SCALAR", "right_operand_value": "0"},
            {"left_operand_type": "INDICATOR", "left_operand_value": "rsi_14",
             "operator": "GT", "right_operand_type": "LOOKBACK", "right_operand_value": "rsi_14:-3"},
            {"left_operand_type": "INDICATOR", "left_operand_value": "adx_14",
             "operator": "GT", "right_operand_type": "SCALAR", "right_operand_value": "20"},
            {"left_operand_type": "INDICATOR", "left_operand_value": "rsi_14",
             "operator": "LT", "right_operand_type": "SCALAR", "right_operand_value": "70"},
        ],
    }
    exit_group = {
        "logic": "OR",
        "conditions": [
            {"left_operand_type": "OHLCV", "left_operand_value": "close",
             "operator": "CROSSES_BELOW", "right_operand_type": "INDICATOR", "right_operand_value": "ema_21"},
            {"left_operand_type": "INDICATOR", "left_operand_value": "rsi_14",
             "operator": "GT", "right_operand_type": "SCALAR", "right_operand_value": "70"},
        ],
    }
    short_entry_group = {
        "logic": "AND",
        "conditions": [
            {"left_operand_type": "OHLCV", "left_operand_value": "close",
             "operator": "LT", "right_operand_type": "INDICATOR", "right_operand_value": "sma_50"},
            {"left_operand_type": "INDICATOR", "left_operand_value": "rsi_14",
             "operator": "LT", "right_operand_type": "SCALAR", "right_operand_value": "45"},
        ],
    }
    short_exit_group = {
        "logic": "OR",
        "conditions": [
            {"left_operand_type": "OHLCV", "left_operand_value": "close",
             "operator": "CROSSES_ABOVE", "right_operand_type": "INDICATOR", "right_operand_value": "ema_21"},
        ],
    }
    entry_signal = evaluate_conditions(df, entry_group)
    exit_signal = evaluate_conditions(df, exit_group)
    short_entry = evaluate_conditions(df, short_entry_group)
    short_exit = evaluate_conditions(df, short_exit_group)
    print(f"  long entry: {int(entry_signal.sum())}, long exit: {int(exit_signal.sum())}")
    print(f"  short entry: {int(short_entry.sum())}, short exit: {int(short_exit.sum())}")
    print("  Learn: signal latched at bar i, filled at bar i+1 open. Never same-bar fill.")

    header("PILLAR 1c — STATE MACHINE (full feature run: costs, leverage, shorts, ExitRules)")
    exit_rules = [
        ExitRule(name="rsi_hard_floor", monitor_col="rsi_14",
                 fixed_threshold=18.0, min_loss_pct=2.0),
    ]
    print("  ExitRule: fixed threshold (RSI < 18) gated on >=2% loss.")
    print("  Learn: ref-vs-monitor / activation / skip_col are extensions —")
    print("  master the fixed-threshold form first.")
    trades, equity = run_backtest(
        df=df,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        short_entry_signal=short_entry,
        short_exit_signal=short_exit,
        initial_capital=INITIAL_CAPITAL,
        asset_class=ASSET_CLASS,
        position_size_type="percent_capital",
        position_size_value=95.0,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        dynamic_tp_pct_column="tp_pct_col",
        commission_pct=0.1,
        slippage_pct=0.05,
        leverage=1.0,
        exit_rules=exit_rules,
        enable_attribution=True,
        entry_conditions=entry_group,
        exit_conditions=exit_group,
    )
    print(f"  trades: {len(trades)} (long+short, 1x, 5% SL / 10% TP + RSI-floor ExitRule)")
    if trades:
        reasons: dict[str, int] = {}
        for t in trades:
            reasons[t.get("exit_reason", "?")] = reasons.get(t.get("exit_reason", "?"), 0) + 1
        print(f"  exit reasons: {reasons}")
        first = trades[0]
        print(f"  sample: {first.get('direction')} "
              f"{first.get('entry_date')} -> {first.get('exit_date')} "
              f"pnl={float(first.get('pnl_pct', 0)):+.2f}% reason={first.get('exit_reason')}")
    print("  Learn: liquidation checked first, then stops, then SL/TP, then ExitRules.")
    print("  Slippage direction-aware. Commission once per side.")

    header("PILLAR 1d — POSITION SIZING COMPARISON (same signals, different risk)")
    for sizing, value, extra in [
        ("full_capital", 100.0, {}),
        ("fixed_amount", 500.0, {}),
        ("risk_based", 1.0, {"stop_loss_pct": 3.0}),
        ("kelly", 0.0, {"kelly_win_rate": 0.55, "kelly_payoff_ratio": 1.5, "kelly_fraction": 0.5}),
    ]:
        try:
            kw: dict = dict(initial_capital=INITIAL_CAPITAL, asset_class=ASSET_CLASS,
                            position_size_type=sizing, position_size_value=value,
                            commission_pct=0.1, slippage_pct=0.05, enable_attribution=False)
            kw.update(extra)
            if sizing == "kelly":
                kw.pop("position_size_value", None)
                kw["position_size_value"] = 100.0
            t, _ = run_backtest(df=df, entry_signal=entry_signal,
                                exit_signal=exit_signal, **kw)
            print(f"  {sizing:14s} -> {len(t)} trades")
        except Exception as e:  # keep learning loop unbroken
            print(f"  {sizing:14s} -> skipped: {e}")

    header("PILLAR 3a — REPORT (honest metrics)")
    if trades:
        report = generate_report(trades, equity, INITIAL_CAPITAL)
        for k in ["total_return_pct", "cagr", "sharpe_ratio", "max_drawdown_pct",
                  "win_rate", "profit_factor", "total_trades", "final_capital"]:
            print(f"  {k:20s} {report.get(k)}")
        print("  Learn: benchmark/Sortino had verified bugs — check your ENGINE_ASSESSMENT.")
    else:
        print("  no trades — widen dates or loosen entry group.")

    header("PILLAR 3b — WALK-FORWARD (disjoint, non-optimizing windows)")
    try:
        windows = generate_windows(df, window_count=3)
        wf_results = []
        for w in windows:
            wdf = df.iloc[w.start_idx:w.end_idx + 1]
            wentry = entry_signal.iloc[w.start_idx:w.end_idx + 1]
            wexit = exit_signal.iloc[w.start_idx:w.end_idx + 1]
            wt, weq = run_backtest(df=wdf, entry_signal=wentry, exit_signal=wexit,
                                   initial_capital=INITIAL_CAPITAL, asset_class=ASSET_CLASS,
                                   position_size_type="percent_capital",
                                   position_size_value=95.0,
                                   commission_pct=0.1, enable_attribution=False)
            wr = generate_report(wt, weq, INITIAL_CAPITAL) if wt else {"total_trades": 0}
            wf_results.append({"total_trades": len(wt), "total_return_pct": wr.get("total_return_pct", 0)})
            print(f"  window {w.index} [{w.start_date} -> {w.end_date}]: "
                  f"{len(wt)} trades, ret={wr.get('total_return_pct', 0):.2f}%")
        score, _ = calculate_consistency_score(wf_results, min_trades=1)
        print(f"  consistency score: {score:.3f} (ROBUST>=0.8, MODERATE>=0.6)")
        print("  Learn: windows must not overlap. <10 trades excluded by default.")
    except Exception as e:
        print(f"  walk-forward skipped: {e}")

    header("PILLAR 3c — PARAM SENSITIVITY (±20% isolation via deepcopy)")
    try:
        variants = generate_parameter_variants({"indicators": indicators}, variation_pct=0.2)
        print(f"  generated {len(variants)} variants (each varies ONE numeric param)")
        for v in variants[:4]:
            print(f"    - {v.get('variant_label')}")
        print("  Learn: run backtest per variant, CV of metrics -> stability score.")
    except Exception as e:
        print(f"  sensitivity skipped: {e}")

    header("PILLAR 3d — REGIME (DESCRIPTIVE ONLY — non-causal trap)")
    try:
        segments, labels = detect_regimes(df, strategy="pelt_volatility")
        print(f"  segments: {len(segments)}, label counts: {labels.value_counts().to_dict()}")
        by_regime = analyze_trades_by_regime(trades, labels) if trades else {}
        print(f"  trades by regime keys: {list(by_regime.keys())[:5] if isinstance(by_regime, dict) else by_regime}")
        print("  TRAP: label at bar t uses future data. Never feed into entry logic.")
    except Exception as e:
        print(f"  regime skipped: {e}")

    header("PILLAR 3e — FEATURE CONDITIONING (which conditions win)")
    try:
        if trades:
            enriched = extract_trade_features(trades, df)
            cond = analyze_feature_conditions(enriched, min_trades_per_bin=5)
            print(f"  feature importance: {cond.get('feature_importance', {})}")
            print(f"  winning conditions: {len(cond.get('winning_conditions', []))}")
        else:
            print("  skipped (no trades).")
    except Exception as e:
        print(f"  feature conditioning skipped: {e}")

    header("PILLAR 4 — OPERABILITY (what to watch in prod)")
    print("  - FastAPI: use await fetch_ohlcv_async; this script uses sync wrapper (no loop).")
    print("  - DB sessions: own_session + NullPool + dispose in finally (see data_layer).")
    print("  - Heavy CPU (indicators/state machine) belongs in Celery, not request loop.")
    print("  - Blocking-in-async smell: sync Redis/httpx inside async def stalls worker.")
    print()
    print("=" * 80)
    print("DONE. Next: change ONE thing (e.g. leverage 1.0, remove ExitRules,")
    print("widen RSI gate) and predict the trade-count/PnL direction BEFORE re-running.")
    print("=" * 80)


if __name__ == "__main__":
    main()
