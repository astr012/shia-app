# ============================================================
# SignAI_OS — Pluggable Cache Backend
#
# Redis adapter with automatic in-memory fallback.
# Zero-config: works without Redis installed.
# ============================================================

import json
import logging
from typing import Optional

logger = logging.getLogger("signai.cache")

_redis_client = None


async def get_redis():
    """Lazy-init Redis connection. Returns None if unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    from app.config import settings
    if not settings.REDIS_URL:
        return None

    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await _redis_client.ping()
        logger.info(f"✅ Redis connected: {settings.REDIS_URL}")
        return _redis_client
    except Exception as e:
        logger.warning(f"⚠️  Redis unavailable ({e}). Using in-memory cache.")
        _redis_client = None
        return None


class RedisCacheBackend:
    """Redis-backed cache with TTL. Falls back to None on errors."""

    def __init__(self, prefix: str = "signai", ttl: int = 3600):
        self.prefix = prefix
        self.ttl = ttl

    def _key(self, namespace: str, key: str) -> str:
        return f"{self.prefix}:{namespace}:{key}"

    async def get(self, namespace: str, key: str) -> Optional[str]:
        client = await get_redis()
        if not client:
            return None
        try:
            val = await client.get(self._key(namespace, key))
            return val
        except Exception:
            return None

    async def set(self, namespace: str, key: str, value: str) -> bool:
        client = await get_redis()
        if not client:
            return False
        try:
            await client.setex(self._key(namespace, key), self.ttl, value)
            return True
        except Exception:
            return False

    async def get_json(self, namespace: str, key: str):
        val = await self.get(namespace, key)
        if val:
            return json.loads(val)
        return None

    async def set_json(self, namespace: str, key: str, value) -> bool:
        return await self.set(namespace, key, json.dumps(value))

    async def flush(self, namespace: str = None):
        client = await get_redis()
        if not client:
            return
        try:
            pattern = f"{self.prefix}:{namespace}:*" if namespace else f"{self.prefix}:*"
            async for key in client.scan_iter(match=pattern):
                await client.delete(key)
        except Exception:
            pass


# Singleton
redis_cache = RedisCacheBackend()
