# ============================================================
# SignAI_OS — Translation Cache
#
# LRU cache for repeated translations.
# Avoids redundant LLM calls and speeds up common phrases.
# Both grammar corrections and sign translations are cached.
# ============================================================

import time
import logging
from typing import Optional, List
from collections import OrderedDict

logger = logging.getLogger("signai.cache")


class TranslationCache:
    """
    In-memory LRU cache for translation results.
    Separate caches for grammar corrections and sign translations.
    """

    def __init__(self, max_size: int = 256, ttl_seconds: int = 3600):
        self._max_size = max_size
        self._ttl = ttl_seconds

        # grammar: raw_text → corrected_text
        self._grammar_cache: OrderedDict[str, tuple[str, float]] = OrderedDict()
        # sign: text → sign_sequence
        self._sign_cache: OrderedDict[str, tuple[List[str], float]] = OrderedDict()

        self._hits = 0
        self._misses = 0

    # ── Grammar Cache ────────────────────────────────────────

    def get_grammar(self, raw_text: str) -> Optional[str]:
        """Look up a cached grammar correction."""
        key = raw_text.lower().strip()
        entry = self._grammar_cache.get(key)
        if entry:
            value, timestamp = entry
            if time.time() - timestamp < self._ttl:
                self._grammar_cache.move_to_end(key)
                self._hits += 1
                logger.debug(f"Cache HIT (grammar): '{key}'")
                return value
            else:
                # Expired
                del self._grammar_cache[key]
        self._misses += 1
        return None

    def set_grammar(self, raw_text: str, corrected: str):
        """Store a grammar correction in cache."""
        key = raw_text.lower().strip()
        self._grammar_cache[key] = (corrected, time.time())
        self._grammar_cache.move_to_end(key)
        self._evict(self._grammar_cache)

    # ── Sign Cache ───────────────────────────────────────────

    def get_sign(self, text: str) -> Optional[List[str]]:
        """Look up a cached sign translation."""
        key = text.lower().strip()
        entry = self._sign_cache.get(key)
        if entry:
            value, timestamp = entry
            if time.time() - timestamp < self._ttl:
                self._sign_cache.move_to_end(key)
                self._hits += 1
                logger.debug(f"Cache HIT (sign): '{key}'")
                return value
            else:
                del self._sign_cache[key]
        self._misses += 1
        return None

    def set_sign(self, text: str, signs: List[str]):
        """Store a sign translation in cache."""
        key = text.lower().strip()
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

    def get_stats(self) -> dict:
        """Return cache statistics."""
        return {
            "grammar_entries": len(self._grammar_cache),
            "sign_entries": len(self._sign_cache),
            "total_entries": len(self._grammar_cache) + len(self._sign_cache),
            "max_size_per_type": self._max_size,
            "ttl_seconds": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_pct": round(self.hit_rate, 1),
        }

    def clear(self):
        """Clear all caches."""
        self._grammar_cache.clear()
        self._sign_cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Translation cache cleared")
