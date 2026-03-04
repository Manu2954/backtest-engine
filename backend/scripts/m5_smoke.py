from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv  # noqa: E402
from app.engine.indicator_layer import compute_indicators  # noqa: E402
from app.engine.condition_engine import evaluate_conditions  # noqa: E402
from app.engine.state_machine import run_backtest  # noqa: E402
from app.engine.report_generator import generate_report  # noqa: E402


def main() -> None:
    ticker = "HDFCBANK.NS"
    start = "2003-01-01"
    end = "2025-01-01"
    initial_capital = 10000.0 # $10,000

    df = fetch_ohlcv(ticker, start, end, "1d", "STOCK")

    indicators = [
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
        {"indicator_type": "SMA", "alias": "sma_200", "params": {"period": 200, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)

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

    entry_signal = evaluate_conditions(df, entry_group)
    exit_signal = evaluate_conditions(df, exit_group)

    trades, equity_curve = run_backtest(
        df=df, 
        entry_signal=entry_signal, 
        exit_signal=exit_signal, 
        initial_capital=initial_capital,
        asset_class="STOCK",
        shares=0.0,
        periodic_contribution={"frequency":"monthly", "amount": 10000}
    )
    # print(df, trades, entry_signal.size, exit_signal.size)
    report = generate_report(trades, equity_curve, initial_capital)


    print("-------------------------------------------------------------")

    print("Total trades:", len(trades))
    for trade in trades:
        print(
            f"Entry {trade['entry_date'].date()} @ {trade['entry_price']:.2f} \n "
            f"Exit {trade['exit_date'].date()} @ {trade['exit_price']:.2f} \n "
            f"PnL {trade['pnl']:.2f} \n "
            f"Shares {trade['shares']:.2f} \n"
            f"Total capital = {equity_curve.at[trade['exit_date']]}\n"
            "-------------------------------------------------------------"
        )

    print("Report:")
    for key, value in report.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
