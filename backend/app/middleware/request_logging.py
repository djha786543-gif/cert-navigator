"""
Structured JSON request logging middleware — Phase 7

Emits one line per request to the 'career.access' logger:
  {
    "request_id": "uuid4",
    "method":     "POST",
    "path":       "/api/resilience/forecast",
    "status":     200,
    "duration_ms": 142.3,
    "client_ip":  "1.2.3.4",
    "user_agent": "Mozilla/5.0..."
  }

Sets X-Request-ID response header so clients and downstream services
can correlate logs across the stack.

Usage (backend/app/main.py):
  from .middleware.request_logging import RequestLoggingMiddleware
  app.add_middleware(RequestLoggingMiddleware)
"""
import json
import time
import uuid
import logging
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Thread-local-equivalent request ID — readable from any coroutine in the
# same async context (useful for correlating log lines within one request).
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

logger = logging.getLogger("career.access")

_SKIP_PATHS = frozenset({
    "/health", "/health/db", "/metrics",
    "/docs", "/redoc", "/openapi.json",
    "/favicon.ico",
})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured access log + X-Request-ID header for every non-trivial request.

    Skips health-check / metrics paths to avoid log noise.
    """

    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid.uuid4())
        request_id_var.set(req_id)

        # Pass request ID to downstream services
        request.state.request_id = req_id

        start = time.perf_counter()

        try:
            response = await call_next(request)
            status   = response.status_code
        except Exception:
            status = 500
            raise
        finally:
            if request.url.path not in _SKIP_PATHS:
                duration_ms = round((time.perf_counter() - start) * 1000, 1)
                logger.info(
                    json.dumps(
                        {
                            "request_id": req_id,
                            "method":     request.method,
                            "path":       request.url.path,
                            "query":      str(request.url.query) or None,
                            "status":     status,
                            "duration_ms": duration_ms,
                            "client_ip":  (
                                request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                                or (request.client.host if request.client else "-")
                            ),
                            "user_agent": request.headers.get("user-agent", "")[:120],
                        },
                        separators=(",", ":"),
                    )
                )

        response.headers["X-Request-ID"] = req_id
        return response
