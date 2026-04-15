"""
Integration tests for parameter sensitivity analysis API.

Tests the full workflow:
1. Create analysis via API
2. Check status
3. Verify report structure
"""
from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

# Add backend to path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402
from app.models import RobustnessAnalysis  # noqa: E402
from app.core.database import get_session  # noqa: E402


@pytest.mark.asyncio
async def test_create_parameter_sensitivity_analysis():
    """Test creating parameter sensitivity analysis."""
    # Create test strategy first
    strategy_data = {
        "name": "Test RSI Strategy",
        "description": "For parameter sensitivity testing",
        "indicators": [
            {
                "alias": "rsi_14",
                "indicator_type": "RSI",
                "params": {"period": 14, "source": "close"}
            }
        ],
        "condition_groups": [
            {
                "group_name": "entry",
                "group_type": "ENTRY",
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
        ]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        strategy_response = await client.post("/strategies", json=strategy_data)
        assert strategy_response.status_code == 200
        strategy_id = strategy_response.json()["id"]

        # Create analysis
        request_data = {
            "strategy_id": strategy_id,
            "ticker": "AAPL",
            "asset_class": "STOCK",
            "start_date": "2023-01-01",
            "end_date": "2024-06-30",
            "initial_capital": 10000.0,
            "variation_pct": 0.2,
            "enable_attribution": False,
        }

        response = await client.post(
            "/robustness/parameter-sensitivity",
            json=request_data,
            timeout=10.0
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert data["strategy_id"] == strategy_id
        assert data["analysis_type"] == "PARAMETER_SENSITIVITY"
        assert data["status"] in ["PENDING", "RUNNING"]
        assert "params" in data
        assert data["params"]["variation_pct"] == 0.2


@pytest.mark.asyncio
async def test_get_analysis_status():
    """Test retrieving analysis status."""
    # Create strategy and analysis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        strategy_data = {
            "name": "Test Strategy",
            "indicators": [{"alias": "rsi_14", "indicator_type": "RSI", "params": {"period": 14}}],
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
        strategy_response = await client.post("/strategies", json=strategy_data)
        strategy_id = strategy_response.json()["id"]

        request_data = {
            "strategy_id": strategy_id,
            "ticker": "AAPL",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 10000.0,
            "variation_pct": 0.2,
        }

        create_response = await client.post(
            "/robustness/parameter-sensitivity",
            json=request_data,
            timeout=10.0
        )
        analysis_id = create_response.json()["id"]

        # Get analysis status
        get_response = await client.get(f"/robustness/{analysis_id}")

        assert get_response.status_code == 200
        data = get_response.json()

        assert data["id"] == analysis_id
        assert data["strategy_id"] == strategy_id
        assert data["analysis_type"] == "PARAMETER_SENSITIVITY"
        assert data["status"] in ["PENDING", "RUNNING", "COMPLETE", "FAILED"]


@pytest.mark.asyncio
async def test_get_nonexistent_analysis():
    """Test getting analysis that doesn't exist."""
    fake_id = str(uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/robustness/{fake_id}")

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_analysis():
    """Test deleting analysis."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create strategy and analysis
        strategy_data = {
            "name": "Test Strategy",
            "indicators": [{"alias": "rsi_14", "indicator_type": "RSI", "params": {"period": 14}}],
            "condition_groups": []
        }
        strategy_response = await client.post("/strategies", json=strategy_data)
        strategy_id = strategy_response.json()["id"]

        request_data = {
            "strategy_id": strategy_id,
            "ticker": "AAPL",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 10000.0,
            "variation_pct": 0.2,
        }

        create_response = await client.post(
            "/robustness/parameter-sensitivity",
            json=request_data,
            timeout=10.0
        )
        analysis_id = create_response.json()["id"]

        # Delete analysis
        delete_response = await client.delete(f"/robustness/{analysis_id}")
        assert delete_response.status_code == 200

        # Verify it's deleted
        get_response = await client.get(f"/robustness/{analysis_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_analysis_params_validation():
    """Test validation of analysis parameters."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test invalid variation_pct (too high)
        request_data = {
            "strategy_id": str(uuid4()),
            "ticker": "AAPL",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 10000.0,
            "variation_pct": 0.6,  # > 0.5 (50%)
        }

        response = await client.post(
            "/robustness/parameter-sensitivity",
            json=request_data
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_analysis_report_structure():
    """Test that completed analysis has correct report structure."""
    # Note: This test requires Celery worker running and completing tasks
    # For now, we'll just verify the database model can store report structure

    async with get_session() as session:
        analysis = RobustnessAnalysis(
            strategy_id=uuid4(),
            analysis_type="PARAMETER_SENSITIVITY",
            status="COMPLETE",
            params={"variation_pct": 0.2},
            report={
                "baseline": {
                    "strategy_id": str(uuid4()),
                    "metrics": {
                        "total_return_pct": 15.0,
                        "sharpe_ratio": 1.5,
                        "win_rate": 60.0,
                    }
                },
                "variants": [],
                "stability_metrics": {
                    "overall_stability_score": 0.85,
                },
                "assessment": {
                    "robustness_level": "ROBUST",
                    "risk_flags": [],
                    "recommendation": "Strategy is robust",
                }
            }
        )

        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)

        # Verify report stored correctly
        assert analysis.report is not None
        assert "baseline" in analysis.report
        assert "stability_metrics" in analysis.report
        assert analysis.report["assessment"]["robustness_level"] == "ROBUST"
