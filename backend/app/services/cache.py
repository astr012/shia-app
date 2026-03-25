# ============================================================
# SignAI_OS — Translation Cache
#
# LRU cache for repeated translations.
# Avoids redundant LLM calls and speeds up common phrases.
# Both grammar corrections and sign translations are cached.
# ============================================================

import time
import logging
import json
from typing import Optional, List
from collections import OrderedDict

logger = logging.getLogger("signai.cache")

try:
    import redis
    # Do not crash if redis module is missing, gracefully degrade.
    REDIS_INSTALLED = True
except ImportError:
    REDIS_INSTALLED = False

class TranslationCache:
    """
    In-memory LRU cache / Redis cluster cache for translation results.
    Self-healing architecture: If Redis socket fails or redis package is missing,
    it seamlessly falls back to local in-memory dictionaries.
    """

    def __init__(self, max_size: int = 256, ttl_seconds: int = 3600, redis_url: str = "redis://localhost:6379/0"):
        self._max_size = max_size
        self._ttl = ttl_seconds
        
        # Local fallback maps
        self._grammar_cache: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._sign_cache: OrderedDict[str, tuple[List[str], float]] = OrderedDict()

        self._hits = 0
        self._misses = 0
        
        # Redis setup
        self._redis_available = False
        self._redis_client = None
        if REDIS_INSTALLED:
            try:
                self._redis_client = redis.from_url(redis_url, socket_timeout=1.0)
                # Ping to check availability
                self._redis_client.ping()
                self._redis_available = True
                logger.info("[Cache] Connected to unified Redis cluster successfully.")
            except Exception as e:
                logger.warning(f"[Cache] Redis unavailable ({e}). Self-healing to localized in-memory maps.")
        else:
            logger.warning("[Cache] redis package not installed. Using localized in-memory maps.")

    def _fallback_get_grammar(self, key: str) -> Optional[str]:
        entry = self._grammar_cache.get(key)
        if entry:
            value, timestamp = entry
            if time.time() - timestamp < self._ttl:
                self._grammar_cache.move_to_end(key)
                self._hits += 1
                logger.debug(f"Cache HIT (local grammar): '{key}'")
                return value
            else:
                del self._grammar_cache[key]
        self._misses += 1
        return None

    def get_grammar(self, raw_text: str) -> Optional[str]:
        key = raw_text.lower().strip()
        
        # Try Redis first
        if self._redis_available and self._redis_client:
            try:
                val = self._redis_client.get(f"grammar:{key}")
                if val:
                    self._hits += 1
                    logger.debug(f"Cache HIT (redis grammar): '{key}'")
                    return val.decode("utf-8")
                else:
                    self._misses += 1
                    return None
            except Exception as e:
                logger.error(f"[Self-Healing] Redis socket failure: {e}. Rolling back to local maps.")
                self._redis_available = False
        
        # Use Local Cache
        return self._fallback_get_grammar(key)

    def _fallback_set_grammar(self, key: str, corrected: str):
        self._grammar_cache[key] = (corrected, time.time())
        self._grammar_cache.move_to_end(key)
        self._evict(self._grammar_cache)
        
    def set_grammar(self, raw_text: str, corrected: str):
        key = raw_text.lower().strip()
        
        if self._redis_available and self._redis_client:
            try:
                self._redis_client.setex(f"grammar:{key}", self._ttl, corrected)
            except Exception as e:
                logger.error(f"[Self-Healing] Redis socket failure during SET: {e}. Rolling back to local.")
                self._redis_available = False
                
        # Always store locally as fallback in case Redis crashes later
        self._fallback_set_grammar(key, corrected)

    def _fallback_get_sign(self, key: str) -> Optional[List[str]]:
        entry = self._sign_cache.get(key)
        if entry:
            value, timestamp = entry
            if time.time() - timestamp < self._ttl:
                self._sign_cache.move_to_end(key)
                self._hits += 1
                logger.debug(f"Cache HIT (local sign): '{key}'")
                return value
            else:
                del self._sign_cache[key]
        self._misses += 1
        return None

    def get_sign(self, text: str) -> Optional[List[str]]:
        key = text.lower().strip()
        if self._redis_available and self._redis_client:
            try:
                val = self._redis_client.get(f"sign:{key}")
                if val:
                    self._hits += 1
                    logger.debug(f"Cache HIT (redis sign): '{key}'")
                    return json.loads(val.decode("utf-8"))
                else:
                    self._misses += 1
                    return None
            except Exception as e:
                logger.error(f"[Self-Healing] Redis socket failure: {e}. Rolling back to local maps.")
                self._redis_available = False
                
        return self._fallback_get_sign(key)

    def _fallback_set_sign(self, key: str, signs: List[str]):
        self._sign_cache[key] = (signs, time.time())
        self._sign_cache.move_to_end(key)
        self._evict(self._sign_cache)

    def set_sign(self, text: str, signs: List[str]):
        key = text.lower().strip()
        if self._redis_available and self._redis_client:
            try:
                self._redis_client.setex(f"sign:{key}", self._ttl, json.dumps(signs))
            except Exception as e:
                logger.error(f"[Self-Healing] Redis socket failure during SET: {e}. Rolling back to local.")
                self._redis_available = False
                
        self._fallback_set_sign(key, signs)

    def _evict(self, cache: OrderedDict):
        while len(cache) > self._max_size:
            evicted_key, _ = cache.popitem(last=False)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return (self._hits / total * 100) if total > 0 else 0.0

    def get_stats(self) -> dict:
        return {
            "grammar_entries": len(self._grammar_cache) if not self._redis_available else "distributed",
            "sign_entries": len(self._sign_cache) if not self._redis_available else "distributed",
            "total_entries": len(self._grammar_cache) + len(self._sign_cache) if not self._redis_available else "distributed",
            "max_size_per_type": self._max_size,
            "ttl_seconds": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_pct": round(self.hit_rate, 1),
            "backend": "redis" if self._redis_available else "memory_fallback"
        }

    def clear(self):
        self._grammar_cache.clear()
        self._sign_cache.clear()
        if self._redis_available and self._redis_client:
            try:
                # Flush the current DB only
                self._redis_client.flushdb()
            except Exception:
                self._redis_available = False
        self._hits = 0
        self._misses = 0
        logger.info("Translation cache cleared")
