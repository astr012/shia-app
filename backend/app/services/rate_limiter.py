# ============================================================
# SignAI_OS — Rate Limiter
#
# Token bucket rate limiter for both REST and WebSocket.
# Prevents abuse and protects the LLM API budget.
# ============================================================

import time
import logging
from typing import Dict

logger = logging.getLogger("signai.ratelimit")


class TokenBucket:
    """
    Token bucket rate limiter.
    Tokens refill at a steady rate. Each request consumes one token.
    If no tokens remain, the request is denied.
    """

    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in the bucket
        """
        self._rate = rate
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens. Returns True if allowed, False if rate-limited.
        """
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now

        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    @property
    def available_tokens(self) -> float:
        now = time.monotonic()
        elapsed = now - self._last_refill
        return min(self._capacity, self._tokens + elapsed * self._rate)


class RateLimiter:
    """
    Per-client rate limiter using token buckets.
    Tracks limits by client identifier (IP or session ID).
    """

    def __init__(self, rate: float, capacity: int):
        self._rate = rate
        self._capacity = capacity
        self._buckets: Dict[str, TokenBucket] = {}
        self._denied_count = 0

    def check(self, client_id: str) -> bool:
        """
        Check if a client is allowed to make a request.
        Returns True if allowed, False if rate-limited.
        """
        if client_id not in self._buckets:
            self._buckets[client_id] = TokenBucket(self._rate, self._capacity)

        allowed = self._buckets[client_id].consume()
        if not allowed:
            self._denied_count += 1
            logger.warning(f"Rate limit exceeded for: {client_id}")
        return allowed

    def cleanup_stale(self, max_age_seconds: float = 300):
        """Remove buckets that haven't been used in a while."""
        now = time.monotonic()
        stale = [
            cid for cid, bucket in self._buckets.items()
            if now - bucket._last_refill > max_age_seconds
        ]
        for cid in stale:
            del self._buckets[cid]

    def get_stats(self) -> dict:
        return {
            "active_clients": len(self._buckets),
            "total_denied": self._denied_count,
        }
