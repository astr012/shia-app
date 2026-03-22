# ============================================================
# SignAI_OS — Middleware
#
# Request ID tracking, logging, performance tracking,
# security headers, and REST API rate limiting.
# ============================================================

import time
import uuid
import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.services.rate_limiter import RateLimiter

logger = logging.getLogger("signai.middleware")


# ── Rate limiting for REST endpoints ─────────────────────────

# Shared REST rate limiter: 30 req/s per IP, burst of 60
_rest_limiter = RateLimiter(rate=30, capacity=60)

# Paths exempt from rate limiting
_EXEMPT_PATHS = frozenset({
    "/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico",
})


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique request ID to every HTTP request.
    Clients can pass their own via X-Request-ID header.
    The ID is injected into the response headers for tracing.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())[:12]
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-IP rate limiting for REST API endpoints.
    Returns 429 Too Many Requests when the client exceeds the limit.
    Exempt paths (health, docs) are never rate-limited.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for exempt paths and WebSocket upgrades
        if request.url.path in _EXEMPT_PATHS or request.headers.get("upgrade") == "websocket":
            return await call_next(request)

        # Identify client by IP (handles proxied requests via X-Forwarded-For)
        client_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or request.client.host
            if request.client
            else "unknown"
        )

        if not _rest_limiter.check(f"rest:{client_ip}"):
            req_id = getattr(request.state, "request_id", "?")
            logger.warning(f"[{req_id}] Rate limit exceeded for {client_ip} on {request.url.path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after_seconds": 1,
                },
                headers={"Retry-After": "1"},
            )

        response = await call_next(request)
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every incoming HTTP request with method, path, status code,
    response time, and request ID for full traceability.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        # Skip logging for health checks and docs (noisy)
        skip_log = request.url.path in ("/health", "/docs", "/openapi.json", "/favicon.ico")

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        req_id = getattr(request.state, "request_id", "—")

        if not skip_log:
            logger.info(
                f"[{req_id}] {request.method} {request.url.path} → {response.status_code} "
                f"({duration_ms:.1f}ms)"
            )

        # Inject performance header
        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds essential security headers to all HTTP responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Powered-By"] = "SignAI_OS"

        return response


