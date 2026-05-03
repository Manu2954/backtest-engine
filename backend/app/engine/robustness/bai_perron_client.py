"""
Python client for Bai-Perron R service.

Usage:
    from app.engine.robustness.bai_perron_client import detect_structural_breaks

    breaks = detect_structural_breaks(
        prices=df['close'].tolist(),
        dates=[str(d) for d in df.index],
        min_segment=50,
    )
"""
from __future__ import annotations

import httpx
from typing import Any

DEFAULT_R_SERVICE_URL = "http://localhost:8787"


class BaiPerronClient:
    """Client for Bai-Perron R service."""

    def __init__(self, base_url: str = DEFAULT_R_SERVICE_URL, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health_check(self) -> bool:
        """Check if R service is running."""
        try:
            resp = httpx.get(f"{self.base_url}/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def detect_breaks(
        self,
        prices: list[float],
        dates: list[str],
        min_segment: int = 50,
        max_breaks: int = 10,
    ) -> dict[str, Any]:
        """
        Detect structural breaks using Bai-Perron test.

        Args:
            prices: List of prices (close prices)
            dates: List of date strings (ISO format)
            min_segment: Minimum segment length in bars
            max_breaks: Maximum number of breaks to detect

        Returns:
            Dict with:
                - success: bool
                - n_breaks: int
                - break_indices: list of break positions
                - break_dates: list of break dates
                - segments: list of segment info (start, end, slope, r_squared, pct_change)
                - bic: BIC score
        """
        payload = {
            "prices": prices,
            "dates": dates,
            "min_segment": min_segment,
            "max_breaks": max_breaks,
        }

        resp = httpx.post(
            f"{self.base_url}/detect-breaks",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()

        result = resp.json()

        if not result.get("success", False):
            raise RuntimeError(f"Bai-Perron detection failed: {result.get('error', 'Unknown error')}")

        return result


# Convenience function
def detect_structural_breaks(
    prices: list[float],
    dates: list[str],
    min_segment: int = 50,
    max_breaks: int = 10,
    service_url: str = DEFAULT_R_SERVICE_URL,
) -> dict[str, Any]:
    """
    Detect structural breaks using Bai-Perron test.

    Requires R service running at service_url.
    Start with: cd r_service && ./start.sh

    Args:
        prices: List of close prices
        dates: List of date strings
        min_segment: Minimum bars per segment
        max_breaks: Maximum breaks to detect
        service_url: URL of R service

    Returns:
        Detection result dict
    """
    client = BaiPerronClient(base_url=service_url)

    if not client.health_check():
        raise ConnectionError(
            f"Cannot connect to Bai-Perron R service at {service_url}. "
            "Start it with: cd r_service && ./start.sh"
        )

    return client.detect_breaks(
        prices=prices,
        dates=dates,
        min_segment=min_segment,
        max_breaks=max_breaks,
    )
