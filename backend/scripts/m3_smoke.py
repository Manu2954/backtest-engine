from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.data_layer import fetch_ohlcv  # noqa: E402
from app.engine.indicator_layer import compute_indicators  # noqa: E402
from app.engine.condition_engine import evaluate_conditions  # noqa: E402


def main() -> None:
    ticker = "BTC-USD"
    start = "2025-05-01"
    end = "2026-02-01"
    resolution = "1h"

    df = fetch_ohlcv(ticker, start, end, resolution)

    indicators = [
        {"indicator_type": "SMA", "alias": "sma_50", "params": {"period": 50, "source": "close"}},
        {"indicator_type": "SMA", "alias": "sma_200", "params": {"period": 200, "source": "close"}},
    ]
    df = compute_indicators(df, indicators)

    condition_group = {
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

    signals = evaluate_conditions(df, condition_group)
    hits = signals[signals].index

    print("Total signals:", len(hits))
    print("signal dates:")
    for ts in hits:
        print(ts.date())

    print("Signal sample with SMA values:")
    if len(hits) > 0:
        sample = df.loc[hits[:5], ["close", "sma_50", "sma_200"]]
        print(sample)
    else:
        print("No signals found in range")


if __name__ == "__main__":
    main()
