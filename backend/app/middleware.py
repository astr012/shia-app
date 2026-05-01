# ============================================================
# SignAI_OS â€” Middleware
#
# Request ID tracking, logging, performance tracking,
# security headers, CSRF protection, and REST API rate limiting.
# ============================================================

import time
import uuid
import logging
from typing import Callable
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.services.rate_limiter import RateLimiter
from app.config import settings

logger = logging.getLogger("signai.middleware")


# â”€â”€ Rate limiting for REST endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Shared REST rate limiter: 30 req/s per IP, burst of 60
_rest_limiter = RateLimiter(rate=30, capacity=60)

# Paths exempt from rate limiting
_EXEMPT_PATHS = frozenset({
    "/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico",
})

# HTTP methods that mutate state (subject to CSRF checks)
_STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique request ID to every HTTP request.
    Clients can pass their own via X-Request-ID header.
    The ID is injected into the response headers for tracing.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())[:12]
        request.state.request_id = request_id

        # Propagate to structured logger
        from app.services.logging import correlation_id
        token = correlation_id.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            correlation_id.reset(token)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Cross-Site Request Forgery protection.

    Validates Origin and Referer headers on state-changing requests
    (POST, PUT, DELETE, PATCH) against the configured trusted origins.
    API endpoints using Bearer token auth are exempt (token itself is CSRF-proof).
    WebSocket upgrade requests are also exempt.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip non-state-changing methods
        if request.method not in _STATE_CHANGING_METHODS:
            return await call_next(request)

        # Skip WebSocket upgrades
        if request.headers.get("upgrade") == "websocket":
            return await call_next(request)

        # Bearer token auth is inherently CSRF-safe (not sent by browser automatically)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        # Validate Origin or Referer
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        trusted = settings.CSRF_TRUSTED_ORIGINS

        if origin:
            if origin not in trusted:
                req_id = getattr(request.state, "request_id", "?")
                logger.warning(f"[{req_id}] CSRF rejected: origin={origin}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "csrf_validation_failed",
                        "message": "Cross-origin request blocked.",
                    },
                )
        elif referer:
            parsed = urlparse(referer)
            referer_origin = f"{parsed.scheme}://{parsed.netloc}"
            if referer_origin not in trusted:
                req_id = getattr(request.state, "request_id", "?")
                logger.warning(f"[{req_id}] CSRF rejected: referer={referer_origin}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "csrf_validation_failed",
                        "message": "Cross-origin request blocked.",
                    },
                )

        return await call_next(request)


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
        # Use the last IP in the chain to prevent client-side spoofing behind proxies
        x_forwarded_for = request.headers.get("x-forwarded-for", "")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[-1].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

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
        req_id = getattr(request.state, "request_id", "â€”")

        if not skip_log:
            logger.info(
                f"[{req_id}] {request.method} {request.url.path} â†’ {response.status_code} "
                f"({duration_ms:.1f}ms)"
            )

        # Inject performance header
        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds comprehensive security headers to all HTTP responses.
    Includes CSP, HSTS, Permissions-Policy, and standard XSS mitigations.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Standard XSS and clickjacking mitigations
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (config-driven)
        response.headers["Content-Security-Policy"] = settings.CSP_DIRECTIVES

        # HTTP Strict Transport Security (for production TLS enforcement)
        if settings.ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Permissions Policy â€” restrict sensitive browser APIs
        response.headers["Permissions-Policy"] = (
            "camera=(self), microphone=(self), geolocation=(), payment=()"
        )

        # Remove server identity leakage
        response.headers["X-Powered-By"] = "SignAI_OS"

        return response
