# ============================================================
# SignAI_OS — Translation Cache
#
# LRU cache for repeated translations.
# Avoids redundant LLM calls and speeds up common phrases.
# Both grammar corrections and sign translations are cached.
# ============================================================

import time
import json
import logging
import asyncio
from typing import Optional, List
from collections import OrderedDict
import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger("signai.cache")

class TranslationCache:
    """
    LRU cache for translation results backed by Redis with local dict fallback.
    Separate caches for grammar corrections and sign translations.
    """

    def __init__(self, max_size: int = 256, ttl_seconds: int = 3600):
        self._max_size = max_size
        self._ttl = ttl_seconds
        
        self._redis: Optional[Redis] = None
        if settings.REDIS_URL:
            try:
                self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
                logger.info("Redis cache initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")
                self._redis = None

        # Fallback local caches
        self._grammar_cache: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._sign_cache: OrderedDict[str, tuple[List[str], float]] = OrderedDict()

        self._hits = 0
        self._misses = 0

    # ── Grammar Cache ────────────────────────────────────────

    async def get_grammar(self, raw_text: str) -> Optional[str]:
        """Look up a cached grammar correction."""
        key = f"grammar:{raw_text.lower().strip()}"
        
        if self._redis:
            try:
                val = await self._redis.get(key)
                if val:
                    self._hits += 1
                    logger.debug(f"Cache HIT (grammar-redis): '{key}'")
                    return val
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
                
        # Fallback
        entry = self._grammar_cache.get(key)
        if entry:
            value, timestamp = entry
            if time.time() - timestamp < self._ttl:
                self._grammar_cache.move_to_end(key)
                self._hits += 1
                logger.debug(f"Cache HIT (grammar-local): '{key}'")
                return value
            else:
                del self._grammar_cache[key]
                
        self._misses += 1
        return None

    async def set_grammar(self, raw_text: str, corrected: str):
        """Store a grammar correction in cache."""
        key = f"grammar:{raw_text.lower().strip()}"
        
        if self._redis:
            try:
                await self._redis.setex(key, self._ttl, corrected)
                return
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
                
        # Fallback
        self._grammar_cache[key] = (corrected, time.time())
        self._grammar_cache.move_to_end(key)
        self._evict(self._grammar_cache)

    # ── Sign Cache ───────────────────────────────────────────

    async def get_sign(self, text: str) -> Optional[List[str]]:
        """Look up a cached sign translation."""
        key = f"sign:{text.lower().strip()}"
        
        if self._redis:
            try:
                val = await self._redis.get(key)
                if val:
                    self._hits += 1
                    logger.debug(f"Cache HIT (sign-redis): '{key}'")
                    return json.loads(val)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        # Fallback
        entry = self._sign_cache.get(key)
        if entry:
            value, timestamp = entry
            if time.time() - timestamp < self._ttl:
                self._sign_cache.move_to_end(key)
                self._hits += 1
                logger.debug(f"Cache HIT (sign-local): '{key}'")
                return value
            else:
                del self._sign_cache[key]
                
        self._misses += 1
        return None

    async def set_sign(self, text: str, signs: List[str]):
        """Store a sign translation in cache."""
        key = f"sign:{text.lower().strip()}"
        
        if self._redis:
            try:
                await self._redis.setex(key, self._ttl, json.dumps(signs))
                return
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        # Fallback
        self._sign_cache[key] = (signs, time.time())
        self._sign_cache.move_to_end(key)
        self._evict(self._sign_cache)

    # ── Eviction ─────────────────────────────────────────────

    def _evict(self, cache: OrderedDict):
        """Evict oldest entries if cache exceeds max size."""
        while len(cache) > self._max_size:
            evicted_key, _ = cache.popitem(last=False)
            logger.debug(f"Cache EVICT: '{evicted_key}'")

    # ── Stats ────────────────────────────────────────────────

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return (self._hits / total * 100) if total > 0 else 0.0

    async def get_stats(self) -> dict:
        """Return cache statistics."""
        redis_status = "connected" if self._redis else "disconnected"
        if self._redis:
            try:
                await self._redis.ping()
            except Exception:
                redis_status = "error"
                
        return {
            "grammar_entries": len(self._grammar_cache),
            "sign_entries": len(self._sign_cache),
            "total_local_entries": len(self._grammar_cache) + len(self._sign_cache),
            "max_size_per_type": self._max_size,
            "ttl_seconds": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_pct": round(self.hit_rate, 1),
            "redis_status": redis_status,
        }

    async def clear(self):
        """Clear all caches."""
        if self._redis:
            try:
                await self._redis.flushdb()
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")
                
        self._grammar_cache.clear()
        self._sign_cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Translation cache cleared")
