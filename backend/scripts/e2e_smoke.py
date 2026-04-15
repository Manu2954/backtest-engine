"""
End-to-End Smoke Test - Full User Flow

Tests the complete user journey through the API:
1. Create a strategy with indicators and conditions
2. Run a backtest
3. Poll for completion
4. Verify report structure including warmup info
5. Run robustness analysis
6. Verify robustness report
7. Cleanup

Requirements:
- PostgreSQL running (docker-compose up)
- Redis running
- Celery worker running (celery -A app.celery_app.celery_app worker --loglevel=info)
- FastAPI server running (uvicorn app.main:app --reload)

Run: python scripts/e2e_smoke.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


BASE_URL = "http://localhost:8000"


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main() -> None:
    print_section("END-TO-END SMOKE TEST - FULL USER FLOW")

    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # Check server is running
    try:
        health = client.get("/health")
        if health.status_code != 200:
            print(f"Server health check failed: {health.status_code}")
            print("Make sure the FastAPI server is running: uvicorn app.main:app --reload")
            sys.exit(1)
    except httpx.ConnectError:
        print("Cannot connect to server at http://localhost:8000")
        print("Make sure the FastAPI server is running: uvicorn app.main:app --reload")
        sys.exit(1)

    print("Server is healthy")

    strategy_id = None
    backtest_id = None
    robustness_id = None

    try:
        # =====================================================================
        # STEP 1: Create Strategy
        # =====================================================================
        print_section("STEP 1: Create Strategy")

        strategy_data = {
            "name": "E2E Smoke Test Strategy - SMA Crossover",
            "description": "Tests full user flow through API",
            "indicators": [
                {
                    "alias": "sma_20",
                    "indicator_type": "SMA",
                    "params": {"period": 20, "source": "close"}
                },
                {
                    "alias": "sma_50",
                    "indicator_type": "SMA",
                    "params": {"period": 50, "source": "close"}
                },
                {
                    "alias": "rsi_14",
                    "indicator_type": "RSI",
                    "params": {"period": 14, "source": "close"}
                }
            ],
            "entry_groups": {
                "golden_cross": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "left_operand_type": "INDICATOR",
                            "left_operand_value": "sma_20",
                            "operator": "CROSSES_ABOVE",
                            "right_operand_type": "INDICATOR",
                            "right_operand_value": "sma_50"
                        }
                    ]
                }
            },
            "exit_groups": {
                "death_cross": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "left_operand_type": "INDICATOR",
                            "left_operand_value": "sma_20",
                            "operator": "CROSSES_BELOW",
                            "right_operand_type": "INDICATOR",
                            "right_operand_value": "sma_50"
                        }
                    ]
                }
            },
            "entry_expression": "golden_cross",
            "exit_expression": "death_cross"
        }

        response = client.post("/strategies", json=strategy_data)
        assert response.status_code == 200, f"Failed to create strategy: {response.text}"

        strategy = response.json()
        strategy_id = strategy["id"]

        print(f"Created strategy: {strategy['name']}")
        print(f"  ID: {strategy_id}")
        print(f"  Indicators: {len(strategy['indicators'])}")
        print(f"  Entry Groups: {list(strategy.get('entry_groups', {}).keys()) if strategy.get('entry_groups') else 'N/A'}")
        print(f"  Exit Groups: {list(strategy.get('exit_groups', {}).keys()) if strategy.get('exit_groups') else 'N/A'}")

        # =====================================================================
        # STEP 2: Run Backtest
        # =====================================================================
        print_section("STEP 2: Run Backtest")

        backtest_data = {
            "strategy_id": strategy_id,
            "ticker": "AAPL",
            "asset_class": "STOCK",
            "start_date": "2022-01-01",  # Start early to ensure warmup happens
            "end_date": "2024-01-01",
            "bar_resolution": "1d",
            "initial_capital": 10000.0,
            "position_size_type": "full_capital",
            "commission_per_trade": 1.0,
            "slippage_pct": 0.05,
            "enable_attribution": True,
        }

        response = client.post("/backtests", json=backtest_data)
        assert response.status_code == 200, f"Failed to submit backtest: {response.text}"

        backtest = response.json()
        backtest_id = backtest["id"]

        print(f"Submitted backtest: {backtest_id}")
        print(f"  Ticker: {backtest_data['ticker']}")
        print(f"  Period: {backtest_data['start_date']} to {backtest_data['end_date']}")
        print(f"  Initial Capital: ${backtest_data['initial_capital']:,.2f}")

        # =====================================================================
        # STEP 3: Poll for Backtest Completion
        # =====================================================================
        print_section("STEP 3: Wait for Backtest Completion")

        max_wait = 120  # 2 minutes
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = client.get(f"/backtests/{backtest_id}")
            assert response.status_code == 200

            status_data = response.json()
            status = status_data["status"]

            elapsed = int(time.time() - start_time)
            print(f"  Status: {status} (elapsed: {elapsed}s)")

            if status == "COMPLETE":
                break
            elif status == "FAILED":
                error = status_data.get("error_message", "Unknown error")
                raise AssertionError(f"Backtest failed: {error}")

            time.sleep(3)
        else:
            raise AssertionError(f"Backtest did not complete within {max_wait}s")

        print(f"Backtest completed in {int(time.time() - start_time)}s")

        # =====================================================================
        # STEP 4: Verify Backtest Report
        # =====================================================================
        print_section("STEP 4: Verify Backtest Report")

        response = client.get(f"/backtests/{backtest_id}")
        backtest_result = response.json()
        report = backtest_result["report"]

        # Verify core metrics
        assert "total_return_pct" in report, "Missing total_return_pct"
        assert "cagr" in report, "Missing cagr"
        assert "sharpe_ratio" in report, "Missing sharpe_ratio"
        assert "max_drawdown_pct" in report, "Missing max_drawdown_pct"
        assert "total_trades" in report, "Missing total_trades"
        assert "win_rate" in report, "Missing win_rate"
        assert "final_capital" in report, "Missing final_capital"

        print("Core Metrics:")
        print(f"  Total Return: {report['total_return_pct']:.2f}%")
        print(f"  CAGR: {report['cagr']:.2f}%")
        print(f"  Sharpe Ratio: {report['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {report['max_drawdown_pct']:.2f}%")
        print(f"  Total Trades: {report['total_trades']}")
        print(f"  Win Rate: {report['win_rate']:.2f}%")
        print(f"  Final Capital: ${report['final_capital']:,.2f}")

        # Verify warmup info
        assert "requested_start_date" in report, "Missing requested_start_date"
        assert "actual_start_date" in report, "Missing actual_start_date"
        assert "warmup_bars_trimmed" in report, "Missing warmup_bars_trimmed"

        print("\nWarmup Info:")
        print(f"  Requested Start: {report['requested_start_date']}")
        print(f"  Actual Start: {report['actual_start_date']}")
        print(f"  Warmup Bars Trimmed: {report['warmup_bars_trimmed']}")

        if "warmup_note" in report:
            print(f"  Note: {report['warmup_note']}")

        # Verify benchmark comparison
        if "benchmark_return_pct" in report:
            print("\nBenchmark Comparison:")
            print(f"  Benchmark Return: {report['benchmark_return_pct']:.2f}%")
            print(f"  Alpha: {report.get('alpha', 'N/A')}")
            print(f"  Beta: {report.get('beta', 'N/A')}")

        # Verify attribution (if enabled and trades occurred)
        if report["total_trades"] > 0 and "attribution" in report:
            print("\nAttribution:")
            attr = report["attribution"]
            print(f"  Total Alpha: {attr.get('total_alpha', 'N/A')}")
            print(f"  Signal Strength Analysis: {list(attr.get('signal_strength', {}).keys())}")

        print("\nBacktest report structure verified")

        # =====================================================================
        # STEP 5: Run Robustness Analysis
        # =====================================================================
        print_section("STEP 5: Run Robustness Analysis")

        robustness_data = {
            "strategy_id": strategy_id,
            "ticker": "AAPL",
            "asset_class": "STOCK",
            "start_date": "2022-01-01",
            "end_date": "2024-01-01",
            "bar_resolution": "1d",
            "initial_capital": 10000.0,
            "variation_pct": 0.2,
            "enable_attribution": False,  # Faster
        }

        response = client.post("/robustness/parameter-sensitivity", json=robustness_data)
        assert response.status_code == 200, f"Failed to submit robustness analysis: {response.text}"

        robustness = response.json()
        robustness_id = robustness["id"]

        print(f"Submitted robustness analysis: {robustness_id}")
        print(f"  Variation: +/-{robustness_data['variation_pct']*100:.0f}%")

        # =====================================================================
        # STEP 6: Poll for Robustness Completion
        # =====================================================================
        print_section("STEP 6: Wait for Robustness Completion")

        max_wait = 300  # 5 minutes (multiple backtests)
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = client.get(f"/robustness/{robustness_id}")
            assert response.status_code == 200

            status_data = response.json()
            status = status_data["status"]

            elapsed = int(time.time() - start_time)
            print(f"  Status: {status} (elapsed: {elapsed}s)")

            if status == "COMPLETE":
                break
            elif status == "FAILED":
                error = status_data.get("error_message", "Unknown error")
                raise AssertionError(f"Robustness analysis failed: {error}")

            time.sleep(5)
        else:
            raise AssertionError(f"Robustness analysis did not complete within {max_wait}s")

        print(f"Robustness analysis completed in {int(time.time() - start_time)}s")

        # =====================================================================
        # STEP 7: Verify Robustness Report
        # =====================================================================
        print_section("STEP 7: Verify Robustness Report")

        response = client.get(f"/robustness/{robustness_id}")
        robustness_result = response.json()
        rob_report = robustness_result["report"]

        # Verify baseline
        assert "baseline" in rob_report, "Missing baseline"
        baseline = rob_report["baseline"]
        assert "metrics" in baseline, "Missing baseline metrics"

        print("Baseline Metrics:")
        print(f"  Return: {baseline['metrics']['total_return_pct']:.2f}%")
        print(f"  Sharpe: {baseline['metrics']['sharpe_ratio']:.2f}")
        print(f"  Win Rate: {baseline['metrics']['win_rate']:.2f}%")

        # Verify variants
        assert "variants" in rob_report, "Missing variants"
        variants = rob_report["variants"]
        print(f"\nVariants: {len(variants)}")
        for v in variants:
            delta = v["delta_from_baseline"]["total_return_pct"]
            print(f"  - {v['variant_label']}: {v['metrics']['total_return_pct']:.2f}% ({delta:+.2f}%)")

        # Verify stability metrics
        assert "stability_metrics" in rob_report, "Missing stability_metrics"
        stability = rob_report["stability_metrics"]

        print(f"\nStability Score: {stability['overall_stability_score']:.3f}")
        print(f"Per-Metric CV: {stability['per_metric_cv']}")

        # Verify assessment
        assert "assessment" in rob_report, "Missing assessment"
        assessment = rob_report["assessment"]

        print(f"\nRobustness Level: {assessment['robustness_level']}")
        print(f"Risk Flags: {len(assessment['risk_flags'])}")
        if assessment['risk_flags']:
            for flag in assessment['risk_flags']:
                print(f"  - {flag}")
        print(f"Recommendation: {assessment['recommendation'][:80]}...")

        print("\nRobustness report structure verified")

        # =====================================================================
        # STEP 8: Cleanup
        # =====================================================================
        print_section("STEP 8: Cleanup")

        # Delete robustness analysis
        response = client.delete(f"/robustness/{robustness_id}")
        assert response.status_code == 200, f"Failed to delete robustness: {response.text}"
        print(f"Deleted robustness analysis: {robustness_id}")
        robustness_id = None

        # Delete backtest
        response = client.delete(f"/backtests/{backtest_id}")
        assert response.status_code == 200, f"Failed to delete backtest: {response.text}"
        print(f"Deleted backtest: {backtest_id}")
        backtest_id = None

        # Delete strategy
        response = client.delete(f"/strategies/{strategy_id}")
        assert response.status_code == 200, f"Failed to delete strategy: {response.text}"
        print(f"Deleted strategy: {strategy_id}")
        strategy_id = None

        # =====================================================================
        # FINAL SUMMARY
        # =====================================================================
        print_section("E2E SMOKE TEST RESULTS")

        print("\nAll steps completed successfully:")
        print("  1. Create Strategy")
        print("  2. Run Backtest")
        print("  3. Wait for Completion")
        print("  4. Verify Report (including warmup info)")
        print("  5. Run Robustness Analysis")
        print("  6. Wait for Completion")
        print("  7. Verify Robustness Report")
        print("  8. Cleanup")

        print("\n" + "=" * 80)
        print("  E2E SMOKE TEST: PASSED")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\nE2E SMOKE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

        # Cleanup on failure
        print("\nAttempting cleanup...")
        if robustness_id:
            try:
                client.delete(f"/robustness/{robustness_id}")
                print(f"  Deleted robustness: {robustness_id}")
            except Exception:
                pass
        if backtest_id:
            try:
                client.delete(f"/backtests/{backtest_id}")
                print(f"  Deleted backtest: {backtest_id}")
            except Exception:
                pass
        if strategy_id:
            try:
                client.delete(f"/strategies/{strategy_id}")
                print(f"  Deleted strategy: {strategy_id}")
            except Exception:
                pass

        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
