from __future__ import annotations

import os
import time

import httpx
import pytest


def _get_base_url(for_pytest: bool) -> str | None:
    base_url = os.getenv("API_BASE_URL")
    if base_url:
        return base_url
    if for_pytest:
        return None
    return "http://localhost:8080"


def _run_flow(base_url: str) -> None:
    strategy_payload = {
        "name": "Integration Strategy",
        "description": "integration test",
        "indicators": [],
        "entry": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "OHLCV",
                    "left_operand_value": "close",
                    "operator": "GT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "0",
                    "display_order": 0,
                }
            ],
        },
        "exit": {
            "logic": "AND",
            "conditions": [
                {
                    "left_operand_type": "OHLCV",
                    "left_operand_value": "close",
                    "operator": "LT",
                    "right_operand_type": "SCALAR",
                    "right_operand_value": "0",
                    "display_order": 0,
                }
            ],
        },
    }

    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        response = client.post("/strategies", json=strategy_payload)
        assert response.status_code == 200, response.text
        strategy = response.json()
        strategy_id = strategy["id"]

        backtest_payload = {
            "strategy_id": strategy_id,
            "ticker": "AAPL",
            "asset_class": "STOCK",
            "start_date": "2020-01-01",
            "end_date": "2020-02-01",
            "bar_resolution": "1d",
            "initial_capital": 10000.0,
        }

        response = client.post("/backtests", json=backtest_payload)
        assert response.status_code == 200, response.text
        run = response.json()
        print(run)
        run_id = run["id"]

        # Poll once after a short delay; M7 will run the engine.
        time.sleep(0.2)
        response = client.get(f"/backtests/{run_id}")
        assert response.status_code == 200, response.text
        status = response.json().get("status")
        assert status == "PENDING"


def test_create_strategy_and_backtest() -> None:
    base_url = _get_base_url(for_pytest=True)
    if not base_url:
        pytest.skip("Set API_BASE_URL to run integration tests", allow_module_level=True)
    _run_flow(base_url)


if __name__ == "__main__":
    base_url = _get_base_url(for_pytest=False)
    try:
        _run_flow(base_url)
        print("Integration flow OK")
    except Exception as exc:
        print(f"Integration flow failed: {exc}")
        raise
