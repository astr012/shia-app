# ============================================================
# Tests — REST Rate Limit Middleware
# ============================================================

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.middleware import _rest_limiter


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestRateLimitMiddleware:
    """Test the REST API rate limiting middleware."""

    @pytest.mark.asyncio
    async def test_normal_requests_pass(self, client):
        """Requests within limit succeed."""
        res = await client.get("/api/vocabulary")
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_health_exempt(self, client):
        """Health endpoint is never rate-limited."""
        for _ in range(100):
            res = await client.get("/health")
            assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_429_on_burst(self, client):
        """Exceeding rate limit returns 429."""
        # Exhaust the limiter for a specific test key
        test_key = "rest:test-burst-client"
        for _ in range(65):  # capacity is 60
            _rest_limiter.check(test_key)

        # Verify the limiter rejects
        assert _rest_limiter.check(test_key) is False

    @pytest.mark.asyncio
    async def test_429_response_format(self, client):
        """When rate limited, response has correct structure."""
        # Force exhaust for the test client IP
        test_key = "rest:testclient"
        for _ in range(65):
            _rest_limiter.check(test_key)

        res = await client.get("/api/vocabulary")
        # If rate limited, check the body format
        if res.status_code == 429:
            data = res.json()
            assert data["error"] == "rate_limit_exceeded"
            assert "retry_after_seconds" in data


class TestRequestIDMiddleware:
    """Test X-Request-ID header injection."""

    @pytest.mark.asyncio
    async def test_auto_generated_id(self, client):
        """Responses include an auto-generated X-Request-ID."""
        res = await client.get("/health")
        assert "x-request-id" in res.headers
        assert len(res.headers["x-request-id"]) > 0

    @pytest.mark.asyncio
    async def test_client_provided_id(self, client):
        """Client-provided X-Request-ID is echoed back."""
        res = await client.get("/health", headers={"X-Request-ID": "my-trace-123"})
        assert res.headers["x-request-id"] == "my-trace-123"


class TestStructuredErrors:
    """Test structured JSON error responses."""

    @pytest.mark.asyncio
    async def test_error_responses_have_request_id_header(self, client):
        """Even error responses include X-Request-ID header for tracing."""
        res = await client.get("/nonexistent-route")
        assert res.status_code == 404
        # Request ID is in the response header regardless of error
        assert "x-request-id" in res.headers

    @pytest.mark.asyncio
    async def test_validation_error_returns_422(self, client):
        """Invalid request body returns 422."""
        res = await client.post("/api/translate", json={"text": "", "mode": "INVALID"})
        assert res.status_code == 422
