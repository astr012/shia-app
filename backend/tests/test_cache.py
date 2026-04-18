# ============================================================
# Tests â€” Translation Cache
#
# Updated to use async methods after Redis migration made
# all cache operations async.
# ============================================================

import pytest
import time
from app.services.cache import TranslationCache


@pytest.fixture
def cache():
    return TranslationCache(max_size=5, ttl_seconds=2)


class TestGrammarCache:
    """Test grammar correction caching."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        await cache.set_grammar("hello how you", "Hello! How are you?")
        assert await cache.get_grammar("hello how you") == "Hello! How are you?"

    @pytest.mark.asyncio
    async def test_miss_returns_none(self, cache):
        assert await cache.get_grammar("nonexistent") is None

    @pytest.mark.asyncio
    async def test_case_insensitive(self, cache):
        await cache.set_grammar("HELLO", "Hello!")
        assert await cache.get_grammar("hello") == "Hello!"

    @pytest.mark.asyncio
    async def test_whitespace_normalized(self, cache):
        await cache.set_grammar("  hello  ", "Hello!")
        assert await cache.get_grammar("hello") == "Hello!"


class TestSignCache:
    """Test sign translation caching."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        await cache.set_sign("i want food", ["POINT_SELF", "WANT", "FOOD"])
        result = await cache.get_sign("i want food")
        assert result == ["POINT_SELF", "WANT", "FOOD"]

    @pytest.mark.asyncio
    async def test_miss_returns_none(self, cache):
        assert await cache.get_sign("nonexistent") is None


class TestCacheEviction:
    """Test LRU eviction behavior."""

    @pytest.mark.asyncio
    async def test_evicts_oldest(self, cache):
        """When cache exceeds max_size, oldest entry is evicted."""
        for i in range(6):
            await cache.set_grammar(f"entry{i}", f"result{i}")

        # Entry 0 should be evicted (max_size=5)
        assert await cache.get_grammar("entry0") is None
        # Entry 5 (newest) should exist
        assert await cache.get_grammar("entry5") == "result5"

    @pytest.mark.asyncio
    async def test_access_refreshes_position(self, cache):
        """Accessing an entry moves it to the end (LRU)."""
        await cache.set_grammar("old", "old_result")
        await cache.set_grammar("new1", "r1")
        await cache.set_grammar("new2", "r2")
        await cache.set_grammar("new3", "r3")

        # Access "old" to refresh it
        await cache.get_grammar("old")

        # Add more to trigger eviction
        await cache.set_grammar("new4", "r4")
        await cache.set_grammar("new5", "r5")

        # "old" was refreshed, so it should survive
        assert await cache.get_grammar("old") == "old_result"
        # "new1" was the least recently used, should be evicted
        assert await cache.get_grammar("new1") is None


class TestCacheTTL:
    """Test TTL expiry."""

    @pytest.mark.asyncio
    async def test_expired_entry_returns_none(self):
        """Entries older than TTL are treated as misses."""
        cache = TranslationCache(max_size=10, ttl_seconds=1)
        await cache.set_grammar("test", "result")

        # Should work immediately
        assert await cache.get_grammar("test") == "result"

        # Wait for expiry
        time.sleep(1.1)
        assert await cache.get_grammar("test") is None


class TestCacheStats:
    """Test statistics tracking."""

    @pytest.mark.asyncio
    async def test_initial_stats(self, cache):
        stats = await cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_hit_miss_tracking(self, cache):
        await cache.set_grammar("key", "value")

        await cache.get_grammar("key")       # hit
        await cache.get_grammar("missing")   # miss

        stats = await cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_pct"] == 50.0

    @pytest.mark.asyncio
    async def test_clear_resets_stats(self, cache):
        await cache.set_grammar("key", "value")
        await cache.get_grammar("key")
        await cache.clear()

        stats = await cache.get_stats()
        assert stats["hits"] == 0
        assert stats["total_local_entries"] == 0
