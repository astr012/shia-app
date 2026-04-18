# ============================================================
# SignAI_OS â€” Health & System Router
# ============================================================

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import settings
from app.dependencies import (
    manager, session_mgr, grammar_engine, translation_engine,
    analytics, cache, ws_limiter,
)
from app.routers.auth import get_current_user
from app.services.auth import require_role
from app.db import models

router = APIRouter(tags=["System"])


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    uptime: str
    services: dict
    config: dict


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="online",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime=analytics.uptime_formatted,
        services={
            "grammar_engine": grammar_engine.get_status(),
            "translation_engine": translation_engine.get_status(),
            "active_connections": manager.active_count(),
            "active_sessions": session_mgr.active_count,
            "cache": await cache.get_stats(),
        },
        config=settings.summary(),
    )


@router.get("/api/analytics", tags=["Analytics"], dependencies=[require_role("admin")])
async def get_analytics():
    return {
        **analytics.get_summary(),
        "sessions": session_mgr.get_summary(),
        "cache": await cache.get_stats(),
        "rate_limiter": ws_limiter.get_stats(),
    }


@router.get("/api/sessions")
async def get_sessions():
    return session_mgr.get_summary()


@router.get("/api/cache")
async def get_cache_stats():
    return await cache.get_stats()


@router.delete("/api/cache", dependencies=[require_role("admin")])
async def clear_cache():
    """Admin-only: purge all translation caches."""
    await cache.clear()
    return {"status": "cleared"}
