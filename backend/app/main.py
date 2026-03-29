# ============================================================
# SignAI_OS — FastAPI Backend
# Main Application Entry Point
#
# This file is deliberately lean. All endpoint logic lives
# in routers/, all services in services/, and all shared
# instances in dependencies.py.
#
# Pipeline: WebSocket ←→ Grammar AI ←→ Translation Engine
# ============================================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
)
from app.dependencies import analytics
from app.db.database import init_db

# ── Routers ──────────────────────────────────────────────────
from app.routers import health, auth, translation, tts, users, websocket

logger = logging.getLogger("signai")


# ── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("━" * 60)
    logger.info(f"🟢 {settings.APP_NAME} v{settings.APP_VERSION} starting")
    logger.info(f"   Environment : {settings.ENV}")
    logger.info(f"   Grammar AI  : {'OpenAI (' + settings.OPENAI_MODEL + ')' if settings.OPENAI_API_KEY else 'Rule-based (fallback)'}")
    logger.info(f"   Frontend URL: {settings.FRONTEND_URL}")
    logger.info("━" * 60)

    # Initialize Core Database Architecture (PostgreSQL/SQLite)
    try:
        await init_db()
        logger.info("   Database   : Connected & Schemas Verified")
    except Exception as e:
        logger.error(f"   Database   : Failed to initialize - {e}")

    yield
    logger.info(f"🔴 {settings.APP_NAME} shutting down | Uptime: {analytics.uptime_formatted}")
    logger.info("━" * 60)


# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="AI-powered sign language ↔ speech communication backend",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Middleware ───────────────────────────────────────────────

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Route Registration ──────────────────────────────────────

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(translation.router)
app.include_router(tts.router)
app.include_router(users.router)
app.include_router(websocket.router)


# ── Global Exception Handlers ───────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch any unhandled exception and return a structured JSON error."""
    import traceback
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{req_id}] Unhandled exception on {request.method} {request.url.path}: {exc}")
    logger.debug(traceback.format_exc())
    analytics.record_error("http")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
            "request_id": req_id,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Structured JSON responses for HTTP exceptions (400, 404, 422, etc.)."""
    req_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "http_error",
            "message": str(exc.detail),
            "status_code": exc.status_code,
            "request_id": req_id,
        },
    )
