"""
Short Selling Smoke Test — Real Market Data

Strategy: SMA Crossover Long + Short on SPY
  - Long entry:  SMA(20) crosses above SMA(50) (golden cross)
  - Long exit:   SMA(20) crosses below SMA(50) (death cross)
  - Short entry: SMA(20) crosses below SMA(50) (death cross — go short)
  - Short exit:  SMA(20) crosses above SMA(50) (golden cross — cover short)

This tests the full pipeline with real data:
  fetch_ohlcv → compute_indicators → evaluate_conditions → run_backtest → generate_report
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv  # noqa: E402
from app.engine.indicator_layer import compute_indicators, trim_warmup_period  # noqa: E402
from app.engine.condition_engine import evaluate_conditions, evaluate_expression  # noqa: E402
from app.engine.state_machine import run_backtest  # noqa: E402
from app.engine.report_generator import generate_report  # noqa: E402


def main() -> None:
    print("=" * 65)
    print("SHORT SELLING SMOKE TEST — Real Market Data")
    print("=" * 65)

    ticker = "SPY"
    start = "2004-01-01"
    end = "2024-12-31"
    initial_capital = 10000.0
    asset_class = "STOCK"

    # ─── Fetch data ───
    print(f"\n[1] Fetching OHLCV: {ticker} ({start} to {end})...")
    df = fetch_ohlcv(ticker, start, end, "1d", asset_class)
    print(f"    Got {len(df)} bars")

    # ─── Compute indicators ───
    print("[2] Computing indicators (SMA-20, SMA-50)...")
    indicators = [
        {"indicator_type": "SMA", "alias": "sma_20", "params": {"period": 20, "source": "close"}},
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)
    df, warmup_bars = trim_warmup_period(df)
    print(f"    Trimmed {warmup_bars} warmup bars, {len(df)} bars remaining")

    # ─── Define conditions ───
    # LONG ENTRY: SMA(20) crosses above SMA(50) — golden cross
    long_entry_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_20",
                "operator": "CROSSES_ABOVE",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_50",
            }
        ],
    }

    # LONG EXIT: SMA(20) crosses below SMA(50) — death cross
    long_exit_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_20",
                "operator": "CROSSES_BELOW",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_50",
            }
        ],
    }

    # SHORT ENTRY: SMA(20) crosses below SMA(50) — death cross (go short)
    short_entry_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_20",
                "operator": "CROSSES_BELOW",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_50",
            }
        ],
    }

    # SHORT EXIT: SMA(20) crosses above SMA(50) — golden cross (cover)
    short_exit_group = {
        "logic": "AND",
        "conditions": [
            {
                "left_operand_type": "INDICATOR",
                "left_operand_value": "sma_20",
                "operator": "CROSSES_ABOVE",
                "right_operand_type": "INDICATOR",
                "right_operand_value": "sma_50",
            }
        ],
    }

    # ─── Evaluate signals ───
    print("[3] Evaluating entry/exit signals...")
    long_entry_signal = evaluate_conditions(df, long_entry_group)
    long_exit_signal = evaluate_conditions(df, long_exit_group)
    short_entry_signal = evaluate_conditions(df, short_entry_group)
    short_exit_signal = evaluate_conditions(df, short_exit_group)

    print(f"    Long entry signals:  {long_entry_signal.sum()}")
    print(f"    Long exit signals:   {long_exit_signal.sum()}")
    print(f"    Short entry signals: {short_entry_signal.sum()}")
    print(f"    Short exit signals:  {short_exit_signal.sum()}")

    # ─── Run backtest ───
    print("[4] Running backtest (simultaneous long + short, 50% sizing, 5% stop)...")
    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=long_entry_signal,
        exit_signal=long_exit_signal,
        initial_capital=initial_capital,
        asset_class=asset_class,
        position_size_type="percent_capital",
        position_size_value=50.0,
        stop_loss_pct=5.0,
        commission_per_trade=1.0,
        slippage_pct=0.05,
        enable_attribution=False,
        short_entry_signal=short_entry_signal,
        short_exit_signal=short_exit_signal,
    )

    # ─── Generate report ───
    print("[5] Generating report...")
    report = generate_report(trades, equity_curve, initial_capital)

    # ─── Print results ───
    print("\n" + "=" * 65)
    print("RESULTS")
    print("=" * 65)

    long_trades = [t for t in trades if t["direction"] == "LONG"]
    short_trades = [t for t in trades if t["direction"] == "SHORT"]

    print(f"\n  Total trades:     {report['total_trades']}")
    print(f"  Long trades:      {len(long_trades)}")
    print(f"  Short trades:     {len(short_trades)}")
    print(f"  Total return:     {report['total_return_pct']:.2f}%")
    print(f"  Final capital:    ${report['final_capital']:,.2f}")
    print(f"  Win rate:         {report['win_rate']:.1f}%")
    print(f"  Max drawdown:     {report['max_drawdown_pct']:.2f}%")
    print(f"  Sharpe ratio:     {report['sharpe_ratio']:.3f}")
    print(f"  Profit factor:    {report['profit_factor']:.2f}")

    if "long_trades_summary" in report:
        print(f"\n  --- Long Summary ---")
        ls = report["long_trades_summary"]
        print(f"  Trades: {ls['total_trades']}, Win rate: {ls['win_rate']:.1f}%, Total PnL: ${ls['total_pnl']:,.2f}")

    if "short_trades_summary" in report:
        print(f"\n  --- Short Summary ---")
        ss = report["short_trades_summary"]
        print(f"  Trades: {ss['total_trades']}, Win rate: {ss['win_rate']:.1f}%, Total PnL: ${ss['total_pnl']:,.2f}")

    # ─── Print sample trades ───
    print(f"\n{'─' * 65}")
    print("SAMPLE TRADES (first 5 long, first 5 short)")
    print(f"{'─' * 65}")

    print("\n  LONG:")
    for t in long_trades[:5]:
        print(
            f"    {t['entry_date'].strftime('%Y-%m-%d')} @ ${t['entry_price']:.2f} → "
            f"{t['exit_date'].strftime('%Y-%m-%d')} @ ${t['exit_price']:.2f} | "
            f"PnL ${t['pnl']:+,.2f} ({t['exit_reason']})"
        )

    print("\n  SHORT:")
    for t in short_trades[:5]:
        print(
            f"    {t['entry_date'].strftime('%Y-%m-%d')} @ ${t['entry_price']:.2f} → "
            f"{t['exit_date'].strftime('%Y-%m-%d')} @ ${t['exit_price']:.2f} | "
            f"PnL ${t['pnl']:+,.2f} ({t['exit_reason']})"
        )

    # ─── Assertions ───
    print(f"\n{'─' * 65}")
    print("ASSERTIONS")
    print(f"{'─' * 65}")

    checks = [
        ("Has trades", len(trades) > 0),
        ("Has long trades", len(long_trades) > 0),
        ("Has short trades", len(short_trades) > 0),
        ("All trades have direction field", all("direction" in t for t in trades)),
        ("Long directions correct", all(t["direction"] == "LONG" for t in long_trades)),
        ("Short directions correct", all(t["direction"] == "SHORT" for t in short_trades)),
        ("Report has direction breakdown", "long_trades_summary" in report and "short_trades_summary" in report),
        ("Equity curve not empty", not equity_curve.empty),
        ("Final equity > 0", equity_curve.iloc[-1] > 0),
        ("No negative equity", (equity_curve >= -0.01).all()),
        ("Short profitable when exit < entry (signal exits)",
         all(t["pnl"] > 0 for t in short_trades
             if t["exit_price"] < t["entry_price"] and t["exit_reason"] == "signal")),
        ("Short loses when exit > entry (signal exits)",
         all(t["pnl"] < 0 for t in short_trades
             if t["exit_price"] > t["entry_price"] and t["exit_reason"] == "signal")),
    ]

    all_passed = True
    for name, result in checks:
        status = "PASS" if result else "FAIL"
        if not result:
            all_passed = False
        print(f"  [{status}] {name}")

    print(f"\n{'=' * 65}")
    if all_passed:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")
        sys.exit(1)
    print(f"{'=' * 65}")


def test_composite_expressions() -> None:
    """
    Test short selling with composite expression groups.

    Strategy: Multi-condition short on SPY
      - Short entry: (overbought AND weakening_trend)
        - overbought: RSI(14) > 70
        - weakening_trend: SMA(20) < SMA(50) (price momentum fading)
      - Short exit: (oversold OR recovering_trend)
        - oversold: RSI(14) < 35
        - recovering_trend: SMA(20) > SMA(50) (momentum returning)
      - Long entry: (oversold AND strengthening_trend)
        - oversold: RSI(14) < 30
        - strengthening_trend: SMA(20) > SMA(50)
      - Long exit: overbought
        - overbought: RSI(14) > 70
    """

    print("\n\n" + "=" * 65)
    print("SHORT SELLING — COMPOSITE EXPRESSION GROUPS")
    print("=" * 65)

    ticker = "SPY"
    start = "2018-01-01"
    end = "2024-12-31"
    initial_capital = 10000.0
    asset_class = "STOCK"

    # ─── Fetch data ───
    print(f"\n[1] Fetching OHLCV: {ticker} ({start} to {end})...")
    df = fetch_ohlcv(ticker, start, end, "1d", asset_class)
    print(f"    Got {len(df)} bars")

    # ─── Compute indicators ───
    print("[2] Computing indicators (RSI-14, SMA-20, SMA-50)...")
    indicators = [
        {"indicator_type": "RSI", "alias": "rsi_14", "params": {"period": 14}},
        {"indicator_type": "SMA", "alias": "sma_20", "params": {"period": 20, "source": "close"}},
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)
    df, warmup_bars = trim_warmup_period(df)
    print(f"    Trimmed {warmup_bars} warmup bars, {len(df)} bars remaining")

    # ─── Define named condition groups ───
    # SHORT ENTRY groups
    short_entry_groups = {
        "overbought": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "70",
                }
            ],
        },
        "weakening_trend": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "sma_20",
                    "operator": "LT",
                    "right_operand_type": "INDICATOR",
                    "right_operand_value": "sma_50",
                }
            ],
        },
    }
    short_entry_expression = "overbought && weakening_trend"

    # SHORT EXIT groups
    short_exit_groups = {
        "oversold": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "35",
                }
            ],
        },
        "recovering_trend": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "sma_20",
                    "operator": "GT",
                    "right_operand_type": "INDICATOR",
                    "right_operand_value": "sma_50",
                }
            ],
        },
    }
    short_exit_expression = "oversold || recovering_trend"

    # LONG ENTRY groups
    long_entry_groups = {
        "oversold": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "30",
                }
            ],
        },
        "strengthening_trend": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "sma_20",
                    "operator": "GT",
                    "right_operand_type": "INDICATOR",
                    "right_operand_value": "sma_50",
                }
            ],
        },
    }
    long_entry_expression = "oversold && strengthening_trend"

    # LONG EXIT groups
    long_exit_groups = {
        "overbought": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "INDICATOR",
                    "left_operand_value": "rsi_14",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "70",
                }
            ],
        },
    }
    long_exit_expression = "overbought"

    # ─── Evaluate signals using expressions ───
    print("[3] Evaluating composite expression signals...")
    long_entry_signal = evaluate_expression(df, long_entry_groups, long_entry_expression)
    long_exit_signal = evaluate_expression(df, long_exit_groups, long_exit_expression)
    short_entry_signal = evaluate_expression(df, short_entry_groups, short_entry_expression)
    short_exit_signal = evaluate_expression(df, short_exit_groups, short_exit_expression)

    print(f"    Long entry (oversold && strengthening_trend):  {long_entry_signal.sum()} signals")
    print(f"    Long exit (overbought):                        {long_exit_signal.sum()} signals")
    print(f"    Short entry (overbought && weakening_trend):   {short_entry_signal.sum()} signals")
    print(f"    Short exit (oversold || recovering_trend):     {short_exit_signal.sum()} signals")

    # ─── Run backtest ───
    print("[4] Running backtest with composite expressions...")
    trades, equity_curve = run_backtest(
        df=df,
        entry_signal=long_entry_signal,
        exit_signal=long_exit_signal,
        initial_capital=initial_capital,
        asset_class=asset_class,
        position_size_type="percent_capital",
        position_size_value=50.0,
        stop_loss_pct=7.0,
        commission_per_trade=1.0,
        slippage_pct=0.05,
        enable_attribution=False,
        short_entry_signal=short_entry_signal,
        short_exit_signal=short_exit_signal,
    )

    # ─── Generate report ───
    print("[5] Generating report...")
    report = generate_report(trades, equity_curve, initial_capital)

    # ─── Print results ───
    print("\n" + "=" * 65)
    print("RESULTS (Composite Expression Strategy)")
    print("=" * 65)

    long_trades = [t for t in trades if t["direction"] == "LONG"]
    short_trades = [t for t in trades if t["direction"] == "SHORT"]

    print(f"\n  Total trades:     {report['total_trades']}")
    print(f"  Long trades:      {len(long_trades)}")
    print(f"  Short trades:     {len(short_trades)}")
    print(f"  Total return:     {report['total_return_pct']:.2f}%")
    print(f"  Final capital:    ${report['final_capital']:,.2f}")
    print(f"  Win rate:         {report['win_rate']:.1f}%")
    print(f"  Sharpe ratio:     {report['sharpe_ratio']:.3f}")

    if "long_trades_summary" in report:
        ls = report["long_trades_summary"]
        print(f"\n  --- Long Summary ---")
        print(f"  Trades: {ls['total_trades']}, Win rate: {ls['win_rate']:.1f}%, Total PnL: ${ls['total_pnl']:,.2f}")

    if "short_trades_summary" in report:
        ss = report["short_trades_summary"]
        print(f"\n  --- Short Summary ---")
        print(f"  Trades: {ss['total_trades']}, Win rate: {ss['win_rate']:.1f}%, Total PnL: ${ss['total_pnl']:,.2f}")

    # ─── Sample trades ───
    if short_trades:
        print(f"\n{'─' * 65}")
        print("SAMPLE SHORT TRADES (composite expression)")
        print(f"{'─' * 65}")
        for t in short_trades[:5]:
            print(
                f"    {t['entry_date'].strftime('%Y-%m-%d')} @ ${t['entry_price']:.2f} → "
                f"{t['exit_date'].strftime('%Y-%m-%d')} @ ${t['exit_price']:.2f} | "
                f"PnL ${t['pnl']:+,.2f} ({t['exit_reason']})"
            )

    # ─── Assertions ───
    print(f"\n{'─' * 65}")
    print("ASSERTIONS")
    print(f"{'─' * 65}")

    checks = [
        ("Expression evaluation produced signals", short_entry_signal.sum() > 0),
        ("Has trades", len(trades) > 0),
        ("Has short trades from composite expression", len(short_trades) > 0),
        ("All short trades have direction=SHORT", all(t["direction"] == "SHORT" for t in short_trades)),
        ("Equity curve valid", not equity_curve.empty and equity_curve.iloc[-1] > 0),
        ("No negative equity", (equity_curve >= -0.01).all()),
        ("Short entry requires BOTH conditions (overbought AND weak trend)",
         short_entry_signal.sum() < evaluate_conditions(df, short_entry_groups["overbought"]).sum()),
        ("Short exit uses OR (more signals than either alone)",
         short_exit_signal.sum() >= evaluate_conditions(df, short_exit_groups["oversold"]).sum()),
    ]

    all_passed = True
    for name, result in checks:
        status = "PASS" if result else "FAIL"
        if not result:
            all_passed = False
        print(f"  [{status}] {name}")

    print(f"\n{'=' * 65}")
    if all_passed:
        print("COMPOSITE EXPRESSION CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")
        sys.exit(1)
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
    test_composite_expressions()
