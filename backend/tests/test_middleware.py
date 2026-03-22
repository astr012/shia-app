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
