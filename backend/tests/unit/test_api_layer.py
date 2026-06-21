"""
Unit tests for API layer improvements:
- Rate limiting
- CORS configuration
- Global exception handler
- Health check with dependencies
- Request ID middleware
- API versioning
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app, raise_server_exceptions=False)


class TestAPIVersioning:
    """Test API versioning with /api/v1/ prefix."""

    def test_health_at_root(self, client):
        """Health check should be at root, not versioned."""
        response = client.get("/health")
        assert response.status_code in (200, 503)  # depends on DB/Redis availability
        assert "status" in response.json()

    def test_old_routes_not_found(self, client):
        """Old unversioned routes should 404."""
        response = client.get("/strategies")
        assert response.status_code == 404

    def test_versioned_path_in_openapi(self, client):
        """OpenAPI should have versioned paths."""
        response = client.get("/openapi.json")
        data = response.json()
        paths = list(data["paths"].keys())

        # Should have /api/v1/ prefixed routes
        assert any(p.startswith("/api/v1/strategies") for p in paths)


class TestRequestIDMiddleware:
    """Test request ID middleware for tracing."""

    def test_generates_request_id(self, client):
        """Should generate X-Request-ID if not provided."""
        response = client.get("/health")
        assert "X-Request-ID" in response.headers
        # Should be a valid UUID format
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

    def test_preserves_incoming_request_id(self, client):
        """Should preserve incoming X-Request-ID header."""
        custom_id = "my-custom-request-id-12345"
        response = client.get("/health", headers={"X-Request-ID": custom_id})
        assert response.headers["X-Request-ID"] == custom_id


class TestHealthCheck:
    """Test enhanced health check endpoint."""

    def test_health_response_structure(self, client):
        """Health check should return proper structure."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
        assert "timestamp" in data

    def test_health_check_status_field(self, client):
        """Each check should have status and latency."""
        response = client.get("/health")
        data = response.json()

        for check_name in ["database", "redis"]:
            check = data["checks"][check_name]
            assert "status" in check
            assert check["status"] in ("ok", "error")
            assert "latency_ms" in check

    def test_healthy_when_all_ok(self, client):
        """Status should be 'healthy' when all checks pass."""
        async def mock_db_check():
            return {"status": "ok", "latency_ms": 5.0}

        def mock_redis_check():
            return {"status": "ok", "latency_ms": 2.0}

        with patch("app.main._check_database", new=mock_db_check):
            with patch("app.main._check_redis", new=mock_redis_check):
                response = client.get("/health")
                assert response.status_code == 200
                assert response.json()["status"] == "healthy"

    def test_degraded_when_partial_failure(self, client):
        """Status should be 'degraded' when some checks fail."""
        async def mock_db_check():
            return {"status": "ok", "latency_ms": 5.0}

        def mock_redis_check():
            return {"status": "error", "latency_ms": 0, "error": "Connection refused"}

        with patch("app.main._check_database", new=mock_db_check):
            with patch("app.main._check_redis", new=mock_redis_check):
                response = client.get("/health")
                assert response.status_code == 503
                assert response.json()["status"] == "degraded"

    def test_unhealthy_when_all_fail(self, client):
        """Status should be 'unhealthy' when all checks fail."""
        async def mock_db_check():
            return {"status": "error", "latency_ms": 0, "error": "Connection refused"}

        def mock_redis_check():
            return {"status": "error", "latency_ms": 0, "error": "Connection refused"}

        with patch("app.main._check_database", new=mock_db_check):
            with patch("app.main._check_redis", new=mock_redis_check):
                response = client.get("/health")
                assert response.status_code == 503
                assert response.json()["status"] == "unhealthy"


class TestValidationErrorHandler:
    """Test validation error handling."""

    def test_validation_error_structure(self, client):
        """Validation errors should return structured response."""
        # Send invalid data to trigger validation error
        response = client.post(
            "/api/v1/strategies",
            json={"invalid_field": "value"}
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Validation error"
        assert "errors" in data
        assert isinstance(data["errors"], list)

    def test_validation_error_field_info(self, client):
        """Validation errors should include field information."""
        response = client.post(
            "/api/v1/strategies",
            json={}  # Missing required fields
        )
        assert response.status_code == 422
        data = response.json()

        # Each error should have field, message, type
        for error in data["errors"]:
            assert "field" in error
            assert "message" in error
            assert "type" in error


class TestCORSConfiguration:
    """Test CORS configuration."""

    def test_cors_headers_for_allowed_origin(self, client):
        """Should return CORS headers for allowed origins."""
        response = client.options(
            "/api/v1/strategies",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            }
        )
        # CORS preflight should succeed
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestRateLimiting:
    """Test rate limiting configuration."""

    def test_health_exempt_from_rate_limit(self, client):
        """Health check should be exempt from rate limiting."""
        # Make many requests to health - should never get 429
        for _ in range(20):
            response = client.get("/health")
            assert response.status_code != 429


class TestOpenAPIMetadata:
    """Test OpenAPI documentation metadata."""

    def test_openapi_title(self, client):
        """OpenAPI docs should have correct title."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "Backtest Engine API v1" in data["info"]["title"]

    def test_openapi_version(self, client):
        """OpenAPI docs should have version."""
        response = client.get("/openapi.json")
        data = response.json()
        assert data["info"]["version"] == "1.0.0"

    def test_openapi_has_versioned_paths(self, client):
        """OpenAPI should show versioned paths."""
        response = client.get("/openapi.json")
        data = response.json()
        paths = list(data["paths"].keys())

        # Should have /api/v1/ prefixed routes
        versioned_paths = [p for p in paths if p.startswith("/api/v1/")]
        assert len(versioned_paths) > 0

        # Health should be at root
        assert "/health" in paths


class TestGlobalExceptionHandler:
    """Test global exception handler doesn't leak stack traces."""

    def test_internal_error_hides_details(self, client):
        """Internal errors should not expose stack traces."""
        # Force an internal error by patching
        async def mock_db_check():
            raise RuntimeError("Simulated DB crash")

        with patch("app.main._check_database", new=mock_db_check):
            response = client.get("/health")
            # Should get an error response
            data = response.json()
            # Should NOT contain stack trace info
            response_text = str(data)
            assert "Traceback" not in response_text
            assert "RuntimeError" not in response_text
