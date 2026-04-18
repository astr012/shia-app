# ============================================================
# SignAI_OS â€” FastAPI Backend
# Main Application Entry Point
#
# This file is deliberately lean. All endpoint logic lives
# in routers/, all services in services/, and all shared
# instances in dependencies.py.
#
# Pipeline: WebSocket â†â†’ Grammar AI â†â†’ Translation Engine
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
    CSRFMiddleware,
)
from app.dependencies import analytics
from app.db.database import init_db

# â”€â”€ Routers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from app.routers import health, auth, translation, tts, users, websocket, ml

logger = logging.getLogger("signai")


# â”€â”€ Lifespan â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("â”" * 60)
    logger.info(f"ðŸŸ¢ {settings.APP_NAME} v{settings.APP_VERSION} starting")
    logger.info(f"   Environment : {settings.ENV}")
    logger.info(f"   Grammar AI  : {'OpenAI (' + settings.OPENAI_MODEL + ')' if settings.OPENAI_API_KEY else 'Rule-based (fallback)'}")
    logger.info(f"   Frontend URL: {settings.FRONTEND_URL}")
    logger.info("â”" * 60)

    # Initialize Core Database Architecture (PostgreSQL/SQLite)
    try:
        await init_db()
        logger.info("   Database   : Connected & Schemas Verified")
    except Exception as e:
        logger.error(f"   Database   : Failed to initialize - {e}")

    yield
    logger.info(f"ðŸ”´ {settings.APP_NAME} shutting down | Uptime: {analytics.uptime_formatted}")
    logger.info("â”" * 60)


# â”€â”€ App â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="AI-powered sign language â†” speech communication backend",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# â”€â”€ Middleware â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
    expose_headers=["X-Request-ID", "X-Response-Time"],
)


# â”€â”€ Route Registration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(translation.router)
app.include_router(tts.router)
app.include_router(users.router)
app.include_router(websocket.router)
app.include_router(ml.router)


# â”€â”€ Global Exception Handlers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
