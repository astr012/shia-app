# ============================================================
# Tests — Rate Limiter
# ============================================================

import pytest
import time
from app.services.rate_limiter import TokenBucket, RateLimiter


class TestTokenBucket:
    """Test the token bucket algorithm."""

    def test_allows_within_capacity(self):
        """Requests within capacity are allowed."""
        bucket = TokenBucket(rate=10, capacity=10)
        for _ in range(10):
            assert bucket.consume() is True

    def test_rejects_over_capacity(self):
        """Requests beyond capacity are rejected."""
        bucket = TokenBucket(rate=1, capacity=3)
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is False  # Over capacity

    def test_refills_over_time(self):
        """Tokens refill at the specified rate."""
        bucket = TokenBucket(rate=10, capacity=2)
        bucket.consume()
        bucket.consume()

        # Bucket is empty
        assert bucket.consume() is False

        # Wait for refill (10 tokens/s = 1 token every 0.1s)
        time.sleep(0.15)
        assert bucket.consume() is True

    def test_capacity_is_max(self):
        """Tokens never exceed capacity even after long waits."""
        bucket = TokenBucket(rate=100, capacity=5)
        time.sleep(0.1)  # Would generate 10 tokens at rate=100
        # But capacity is 5, so only 5 should be available
        count = 0
        while bucket.consume():
            count += 1
        assert count == 5


class TestRateLimiter:
    """Test per-client rate limiting."""

    def test_different_clients_independent(self):
        """Each client has their own bucket."""
        limiter = RateLimiter(rate=1, capacity=2)

        assert limiter.check("client_a") is True
        assert limiter.check("client_a") is True
        assert limiter.check("client_a") is False  # Over limit

        # Client B should still be allowed
        assert limiter.check("client_b") is True

    def test_stats_tracking(self):
        """Denied requests are counted."""
        limiter = RateLimiter(rate=1, capacity=1)
        limiter.check("client")
        limiter.check("client")  # denied

        stats = limiter.get_stats()
        assert stats["active_clients"] == 1
        assert stats["total_denied"] == 1

    def test_cleanup_stale(self):
        """Stale buckets are cleaned up."""
        limiter = RateLimiter(rate=1, capacity=5)
        limiter.check("old_client")

        # Force the last_refill to be old
        limiter._buckets["old_client"]._last_refill -= 600

        limiter.cleanup_stale(max_age_seconds=300)
        assert "old_client" not in limiter._buckets
