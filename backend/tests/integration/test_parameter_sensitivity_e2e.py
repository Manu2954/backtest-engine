"""
End-to-end integration tests for parameter sensitivity analysis.

These tests require:
- PostgreSQL running (docker-compose up)
- Redis running
- Celery worker running
- Alembic migrations applied

Run with: pytest tests/integration/test_parameter_sensitivity_e2e.py -v -s
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


async def test_full_parameter_sensitivity_workflow():
    """
    Test complete parameter sensitivity workflow.

    This is an end-to-end test that:
    1. Creates a strategy
    2. Submits parameter sensitivity analysis
    3. Waits for completion
    4. Verifies report structure and contents
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Step 1: Create test strategy
        strategy_data = {
            "name": "E2E Test RSI Strategy",
            "description": "For parameter sensitivity testing",
            "indicators": [
                {
                    "alias": "rsi_14",
                    "indicator_type": "RSI",
                    "params": {"period": 14, "source": "close"}
                },
                {
                    "alias": "sma_50",
                    "indicator_type": "SMA",
                    "params": {"period": 50, "source": "close"}
                }
            ],
            "entry_groups": {
                "oversold": {
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
                "overbought": {
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
            "entry_expression": "oversold",
            "exit_expression": "overbought"
        }

        strategy_response = await client.post("/api/v1/strategies", json=strategy_data)
        assert strategy_response.status_code == 200
        strategy_id = strategy_response.json()["id"]
        print(f"\n✓ Created strategy: {strategy_id}")

        # Step 2: Submit parameter sensitivity analysis
        analysis_request = {
            "strategy_id": strategy_id,
            "ticker": "AAPL",
            "asset_class": "STOCK",
            "start_date": "2023-01-01",
            "end_date": "2024-06-30",  # 18 months to ensure enough data after warmup
            "bar_resolution": "1d",
            "initial_capital": 10000.0,
            "variation_pct": 0.2,
            "enable_attribution": False,  # Faster without attribution
            "commission_per_trade": 1.0,
            "slippage_pct": 0.05,
        }

        analysis_response = await client.post(
            "/api/v1/robustness/parameter-sensitivity",
            json=analysis_request,
            timeout=10.0
        )

        print(f"Response status: {analysis_response.status_code}")
        print(f"Response body: {analysis_response.text}")
        assert analysis_response.status_code == 200
        analysis_data = analysis_response.json()
        analysis_id = analysis_data["id"]

        print(f"✓ Submitted analysis: {analysis_id}")
        print(f"  Status: {analysis_data['status']}")
        print(f"  Variation: ±{analysis_data['params']['variation_pct']*100}%")

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

        report = final_data["report"]

        # Verify baseline section
        assert "baseline" in report
        assert "strategy_id" in report["baseline"]
        assert "params" in report["baseline"]
        assert "metrics" in report["baseline"]

        baseline_metrics = report["baseline"]["metrics"]
        assert "total_return_pct" in baseline_metrics
        assert "sharpe_ratio" in baseline_metrics
        assert "win_rate" in baseline_metrics

        print("\n✓ Baseline metrics:")
        print(f"  Return: {baseline_metrics['total_return_pct']:.2f}%")
        print(f"  Sharpe: {baseline_metrics['sharpe_ratio']:.2f}")
        print(f"  Win Rate: {baseline_metrics['win_rate']:.2f}%")

        # Verify variants section
        assert "variants" in report
        variants = report["variants"]

        # Should have 4 variants (2 indicators × 1 param each × 2 directions)
        # RSI period: 11, 17; SMA length: 40, 60
        assert len(variants) == 4, f"Expected 4 variants, got {len(variants)}"

        print(f"\n✓ Generated {len(variants)} variants:")
        for variant in variants:
            assert "variant_label" in variant
            assert "variant_params" in variant
            assert "metrics" in variant
            assert "delta_from_baseline" in variant

            print(f"  - {variant['variant_label']}")
            print(f"    Return: {variant['metrics']['total_return_pct']:.2f}% "
                  f"(Δ {variant['delta_from_baseline']['total_return_pct']:+.2f}%)")

        # Verify stability metrics
        assert "stability_metrics" in report
        stability = report["stability_metrics"]

        assert "overall_stability_score" in stability
        assert "per_metric_cv" in stability

        stability_score = stability["overall_stability_score"]
        assert 0.0 <= stability_score <= 1.0

        print(f"\n✓ Stability metrics:")
        print(f"  Overall score: {stability_score:.3f}")
        print(f"  Per-metric CV: {stability['per_metric_cv']}")

        # Verify assessment
        assert "assessment" in report
        assessment = report["assessment"]

        assert "robustness_level" in assessment
        assert assessment["robustness_level"] in ["ROBUST", "MODERATE", "FRAGILE"]

        assert "risk_flags" in assessment
        assert isinstance(assessment["risk_flags"], list)

        assert "recommendation" in assessment
        assert len(assessment["recommendation"]) > 0

        print(f"\n✓ Assessment:")
        print(f"  Robustness: {assessment['robustness_level']}")
        print(f"  Risk flags: {len(assessment['risk_flags'])}")
        if assessment['risk_flags']:
            for flag in assessment['risk_flags']:
                print(f"    - {flag}")
        print(f"  Recommendation: {assessment['recommendation'][:100]}...")

        # Step 5: Verify via API (skip direct DB access to avoid greenlet issues)
        # The GET endpoint already verified the data structure above
        print(f"\n✓ Report structure verified via API")

        # Cleanup: Delete analysis
        delete_response = await client.delete(f"/api/v1/robustness/{analysis_id}")
        assert delete_response.status_code == 200
        print(f"✓ Cleaned up analysis")


async def test_parameter_sensitivity_with_ema_crossover():
    """
    Test analysis with EMA crossover strategy.

    EMA(20) and EMA(50) will generate 4 variants (2 indicators × 2 directions each).
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create strategy with EMA crossover
        strategy_data = {
            "name": "EMA Crossover Strategy",
            "indicators": [
                {"alias": "ema_20", "indicator_type": "EMA", "params": {"period": 20, "source": "close"}},
                {"alias": "ema_50", "indicator_type": "EMA", "params": {"period": 50, "source": "close"}},
            ],
            "entry_groups": {
                "crossover": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "left_operand_type": "INDICATOR",
                            "left_operand_value": "ema_20",
                            "operator": "CROSSES_ABOVE",
                            "right_operand_type": "INDICATOR",
                            "right_operand_value": "ema_50"
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
                            "left_operand_value": "ema_20",
                            "operator": "CROSSES_BELOW",
                            "right_operand_type": "INDICATOR",
                            "right_operand_value": "ema_50"
                        }
                    ]
                }
            },
            "entry_expression": "crossover",
            "exit_expression": "crossunder"
        }

        strategy_response = await client.post("/api/v1/strategies", json=strategy_data)
        strategy_id = strategy_response.json()["id"]

        # Submit analysis
        analysis_request = {
            "strategy_id": strategy_id,
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2024-06-30",
            "initial_capital": 10000.0,
            "variation_pct": 0.2,
        }

        analysis_response = await client.post(
            "/api/v1/robustness/parameter-sensitivity",
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

                # Should have 4 variants (2 indicators × 2 directions)
                assert len(report["variants"]) == 4

                # Should have stability score between 0 and 1
                stability_score = report["stability_metrics"]["overall_stability_score"]
                assert 0.0 <= stability_score <= 1.0

                # Should have a robustness assessment
                assert report["assessment"]["robustness_level"] in ["ROBUST", "MODERATE", "FRAGILE"]

                print(f"\n✓ EMA crossover analysis completed with {len(report['variants'])} variants")
                print(f"  Stability score: {stability_score:.3f}")
                print(f"  Robustness: {report['assessment']['robustness_level']}")
                return

            await asyncio.sleep(2)

        pytest.fail("Analysis did not complete")


async def test_parameter_sensitivity_with_small_integer_params():
    """
    Test that small integer parameters (like period=2) are handled gracefully.

    Some params may not generate variants due to rounding.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        strategy_data = {
            "name": "Small Params Strategy",
            "indicators": [
                {"alias": "bb", "indicator_type": "BBANDS", "params": {"period": 20, "std_dev": 2}}
            ],
            "entry_groups": {
                "entry": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "left_operand_type": "OHLCV",
                            "left_operand_value": "close",
                            "operator": "LT",
                            "right_operand_type": "INDICATOR",
                            "right_operand_value": "bb_lower"
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
                            "operator": "GT",
                            "right_operand_type": "INDICATOR",
                            "right_operand_value": "bb_upper"
                        }
                    ]
                }
            },
            "entry_expression": "entry",
            "exit_expression": "exit"
        }

        strategy_response = await client.post("/api/v1/strategies", json=strategy_data)
        strategy_id = strategy_response.json()["id"]

        analysis_request = {
            "strategy_id": strategy_id,
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2024-06-30",
            "initial_capital": 10000.0,
            "variation_pct": 0.2,
        }

        analysis_response = await client.post(
            "/api/v1/robustness/parameter-sensitivity",
            json=analysis_request,
            timeout=60.0
        )

        analysis_id = analysis_response.json()["id"]

        # Wait and check that it completes without error
        max_attempts = 60
        for _ in range(max_attempts):
            status_response = await client.get(f"/api/v1/robustness/{analysis_id}")
            status_data = status_response.json()

            if status_data["status"] == "COMPLETE":
                # std_dev=2 won't generate variants (2*0.8=1.6→2, 2*1.2=2.4→2)
                # But period=20 will generate variants
                report = status_data["report"]
                assert len(report["variants"]) == 2  # Only period variants

                print("\n✓ Small integer params handled correctly")
                return
            elif status_data["status"] == "FAILED":
                error_msg = status_data.get("error_message", "Unknown error")
                pytest.fail(f"Analysis failed: {error_msg}")

            await asyncio.sleep(2)

        pytest.fail("Analysis did not complete")


if __name__ == "__main__":
    # Can run directly for debugging
    pytest.main([__file__, "-v", "-s"])
