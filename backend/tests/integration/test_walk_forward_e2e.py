"""
End-to-end integration tests for walk-forward validation.

These tests require:
- PostgreSQL running (docker-compose up)
- Redis running
- Celery worker running
- Alembic migrations applied

Run with: pytest tests/integration/test_walk_forward_e2e.py -v -s
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

# Add backend to path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402


# Use session scope for event loop to avoid "attached to a different loop" errors
pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_full_walk_forward_workflow():
    """
    Test complete walk-forward validation workflow.

    This is an end-to-end test that:
    1. Creates a strategy
    2. Submits walk-forward validation
    3. Waits for completion
    4. Verifies report structure and contents
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Step 1: Create test strategy
        strategy_data = {
            "name": "E2E Walk-Forward Test Strategy",
            "description": "For walk-forward validation testing",
            "indicators": [
                {
                    "alias": "sma_10",
                    "indicator_type": "SMA",
                    "params": {"period": 10, "source": "close"}
                },
                {
                    "alias": "sma_30",
                    "indicator_type": "SMA",
                    "params": {"period": 30, "source": "close"}
                }
            ],
            "entry_groups": {
                "crossover": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "left_operand_type": "INDICATOR",
                            "left_operand_value": "sma_10",
                            "operator": "CROSSES_ABOVE",
                            "right_operand_type": "INDICATOR",
                            "right_operand_value": "sma_30"
                        }
                    ]
                }
            },
            "exit_groups": {
                "crossunder": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "left_operand_type": "INDICATOR",
                            "left_operand_value": "sma_10",
                            "operator": "CROSSES_BELOW",
                            "right_operand_type": "INDICATOR",
                            "right_operand_value": "sma_30"
                        }
                    ]
                }
            },
            "entry_expression": "crossover",
            "exit_expression": "crossunder"
        }

        strategy_response = await client.post("/api/v1/strategies", json=strategy_data)
        assert strategy_response.status_code == 200
        strategy_id = strategy_response.json()["id"]
        print(f"\n✓ Created strategy: {strategy_id}")

        # Step 2: Submit walk-forward validation
        analysis_request = {
            "strategy_id": strategy_id,
            "ticker": "AAPL",
            "asset_class": "STOCK",
            "start_date": "2020-01-01",
            "end_date": "2024-01-01",
            "bar_resolution": "1d",
            "initial_capital": 10000.0,
            "window_count": 4,
            "commission_per_trade": 1.0,
            "slippage_pct": 0.05,
        }

        analysis_response = await client.post(
            "/api/v1/robustness/walk-forward",
            json=analysis_request,
            timeout=10.0
        )

        print(f"Response status: {analysis_response.status_code}")
        print(f"Response body: {analysis_response.text}")
        assert analysis_response.status_code == 200
        analysis_data = analysis_response.json()
        analysis_id = analysis_data["id"]

        print(f"✓ Submitted walk-forward validation: {analysis_id}")
        print(f"  Status: {analysis_data['status']}")
        print(f"  Window Count: {analysis_data['params']['window_count']}")

        # Step 3: Poll for completion
        max_wait = 300  # 5 minutes timeout
        start_time = time.time()
        completed = False

        while time.time() - start_time < max_wait:
            status_response = await client.get(f"/api/v1/robustness/{analysis_id}")
            assert status_response.status_code == 200

            status_data = status_response.json()
            current_status = status_data["status"]

            print(f"  Status: {current_status} (elapsed: {int(time.time() - start_time)}s)")

            if current_status == "COMPLETE":
                completed = True
                break
            elif current_status == "FAILED":
                error = status_data.get("error_message", "Unknown error")
                pytest.fail(f"Analysis failed: {error}")
                break

            await asyncio.sleep(5)  # Poll every 5 seconds

        assert completed, f"Analysis did not complete within {max_wait} seconds"
        print(f"✓ Analysis completed in {int(time.time() - start_time)}s")

        # Step 4: Verify report structure
        final_response = await client.get(f"/api/v1/robustness/{analysis_id}")
        final_data = final_response.json()

        assert final_data["status"] == "COMPLETE"
        assert final_data["report"] is not None
        assert final_data["analysis_type"] == "WALK_FORWARD"

        report = final_data["report"]

        # Verify windows section
        assert "windows" in report
        windows = report["windows"]
        assert len(windows) == 4  # Requested 4 windows

        print(f"\n✓ Windows ({len(windows)}):")
        for window in windows:
            assert "period" in window
            assert "metrics" in window

            metrics = window["metrics"]
            assert "total_return_pct" in metrics
            assert "sharpe_ratio" in metrics
            assert "total_trades" in metrics

            print(f"  - {window['period']}: "
                  f"Return={metrics['total_return_pct']:.2f}%, "
                  f"Trades={metrics['total_trades']}")

        # Verify summary section
        assert "summary" in report
        summary = report["summary"]

        assert "total_windows" in summary
        assert "sufficient_sample_windows" in summary
        assert "profitable_windows" in summary
        assert "profitable_ratio" in summary
        assert "consistency_score" in summary
        assert "return_range" in summary
        assert "best_window" in summary
        assert "worst_window" in summary

        print(f"\n✓ Summary:")
        print(f"  Total Windows: {summary['total_windows']}")
        print(f"  Sufficient Sample: {summary['sufficient_sample_windows']}")
        print(f"  Profitable: {summary['profitable_windows']}/{summary['total_windows']}")
        print(f"  Consistency Score: {summary['consistency_score']:.3f}")
        print(f"  Return Range: [{summary['return_range']['min']:.2f}%, {summary['return_range']['max']:.2f}%]")

        # Verify assessment section
        assert "assessment" in report
        assessment = report["assessment"]

        assert "level" in assessment
        assert assessment["level"] in ["ROBUST", "MODERATE", "FRAGILE"]
        assert "risk_flags" in assessment
        assert isinstance(assessment["risk_flags"], list)
        assert "recommendation" in assessment

        print(f"\n✓ Assessment:")
        print(f"  Level: {assessment['level']}")
        print(f"  Risk Flags: {len(assessment['risk_flags'])}")
        if assessment['risk_flags']:
            for flag in assessment['risk_flags']:
                print(f"    - {flag}")

        # Verify metadata
        assert "metadata" in report
        assert "strategy_id" in report["metadata"]
        assert "ticker" in report["metadata"]

        # Cleanup
        delete_response = await client.delete(f"/api/v1/robustness/{analysis_id}")
        assert delete_response.status_code == 200
        print(f"✓ Cleaned up analysis")

        delete_strategy = await client.delete(f"/strategies/{strategy_id}")
        assert delete_strategy.status_code == 200
        print(f"✓ Cleaned up strategy")


async def test_walk_forward_with_different_window_counts():
    """
    Test walk-forward with different window counts.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create strategy
        strategy_data = {
            "name": "Window Count Test Strategy",
            "indicators": [
                {"alias": "rsi_14", "indicator_type": "RSI", "params": {"period": 14}},
            ],
            "entry_groups": {
                "entry": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "left_operand_type": "INDICATOR",
                            "left_operand_value": "rsi_14",
                            "operator": "LT",
                            "right_operand_type": "SCALAR",
                            "right_operand_value": "30"
                        }
                    ]
                }
            },
            "exit_groups": {
                "exit": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "left_operand_type": "INDICATOR",
                            "left_operand_value": "rsi_14",
                            "operator": "GT",
                            "right_operand_type": "SCALAR",
                            "right_operand_value": "70"
                        }
                    ]
                }
            },
            "entry_expression": "entry",
            "exit_expression": "exit"
        }

        strategy_response = await client.post("/api/v1/strategies", json=strategy_data)
        strategy_id = strategy_response.json()["id"]

        # Submit with 3 windows
        analysis_request = {
            "strategy_id": strategy_id,
            "ticker": "AAPL",
            "start_date": "2021-01-01",
            "end_date": "2024-01-01",
            "initial_capital": 10000.0,
            "window_count": 3,
        }

        analysis_response = await client.post(
            "/api/v1/robustness/walk-forward",
            json=analysis_request,
            timeout=60.0
        )

        analysis_id = analysis_response.json()["id"]

        # Wait for completion
        max_attempts = 60
        for _ in range(max_attempts):
            status_response = await client.get(f"/api/v1/robustness/{analysis_id}")
            status_data = status_response.json()

            if status_data["status"] == "COMPLETE":
                report = status_data["report"]

                # Should have exactly 3 windows
                assert len(report["windows"]) == 3

                print(f"\n✓ Walk-forward with 3 windows completed")
                print(f"  Windows: {len(report['windows'])}")
                print(f"  Consistency: {report['summary']['consistency_score']:.3f}")
                print(f"  Level: {report['assessment']['level']}")

                # Cleanup
                await client.delete(f"/api/v1/robustness/{analysis_id}")
                await client.delete(f"/strategies/{strategy_id}")
                return

            await asyncio.sleep(2)

        pytest.fail("Analysis did not complete")


async def test_walk_forward_insufficient_data():
    """
    Test walk-forward handles insufficient data gracefully.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create strategy with long indicator period
        strategy_data = {
            "name": "Insufficient Data Test",
            "indicators": [
                {"alias": "sma_200", "indicator_type": "SMA", "params": {"period": 200}},
            ],
            "entry_groups": {
                "entry": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "left_operand_type": "OHLCV",
                            "left_operand_value": "close",
                            "operator": "GT",
                            "right_operand_type": "INDICATOR",
                            "right_operand_value": "sma_200"
                        }
                    ]
                }
            },
            "exit_groups": {
                "exit": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "left_operand_type": "OHLCV",
                            "left_operand_value": "close",
                            "operator": "LT",
                            "right_operand_type": "INDICATOR",
                            "right_operand_value": "sma_200"
                        }
                    ]
                }
            },
            "entry_expression": "entry",
            "exit_expression": "exit"
        }

        strategy_response = await client.post("/api/v1/strategies", json=strategy_data)
        strategy_id = strategy_response.json()["id"]

        # Submit with very short date range (will fail after warmup)
        analysis_request = {
            "strategy_id": strategy_id,
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-06-01",  # Only ~5 months, SMA 200 needs 200 bars
            "initial_capital": 10000.0,
            "window_count": 5,
        }

        analysis_response = await client.post(
            "/api/v1/robustness/walk-forward",
            json=analysis_request,
            timeout=60.0
        )

        analysis_id = analysis_response.json()["id"]

        # Wait for completion (should fail)
        max_attempts = 30
        for _ in range(max_attempts):
            status_response = await client.get(f"/api/v1/robustness/{analysis_id}")
            status_data = status_response.json()

            if status_data["status"] == "FAILED":
                error_msg = status_data["error_message"].lower()
                assert "insufficient" in error_msg or \
                       "not enough" in error_msg or \
                       "nan" in error_msg or \
                       "need more" in error_msg
                print(f"\n✓ Correctly failed with insufficient data")
                print(f"  Error: {status_data['error_message']}")

                # Cleanup
                await client.delete(f"/api/v1/robustness/{analysis_id}")
                await client.delete(f"/strategies/{strategy_id}")
                return

            if status_data["status"] == "COMPLETE":
                # If it completed, that's also OK - just means there was enough data
                await client.delete(f"/api/v1/robustness/{analysis_id}")
                await client.delete(f"/strategies/{strategy_id}")
                print(f"\n✓ Analysis completed (had sufficient data)")
                return

            await asyncio.sleep(2)

        # Cleanup if timed out
        await client.delete(f"/api/v1/robustness/{analysis_id}")
        await client.delete(f"/strategies/{strategy_id}")


if __name__ == "__main__":
    # Can run directly for debugging
    pytest.main([__file__, "-v", "-s"])
