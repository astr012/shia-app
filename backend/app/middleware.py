# ============================================================
# SignAI_OS — Middleware
#
# Request logging, performance tracking, and security headers
# for all HTTP requests passing through the FastAPI server.
# ============================================================

import time
import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("signai.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every incoming HTTP request with method, path, status code,
    and response time in milliseconds.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        # Skip logging for health checks and docs (noisy)
        skip_log = request.url.path in ("/health", "/docs", "/openapi.json", "/favicon.ico")

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        if not skip_log:
            logger.info(
                f"{request.method} {request.url.path} → {response.status_code} "
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
