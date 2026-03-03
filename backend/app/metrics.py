"""
Prometheus metrics instrumentation — Phase 7

Exposes /metrics endpoint for Prometheus scraping.

Metrics registered:
  http_requests_total{method, endpoint, status_code}   Counter
  http_request_duration_seconds{method, endpoint}      Histogram
  http_active_requests                                 Gauge
  celery_task_total{task_name, status}                 Counter
  celery_task_duration_seconds{task_name}              Histogram
  proctor_active_sessions                              Gauge
  artifact_queue_depth                                 Gauge
  circuit_breaker_open{service}                        Gauge

Wire-up (backend/app/main.py):
  from .metrics import instrument_app, metrics_endpoint
  instrument_app(app)
  app.add_route("/metrics", metrics_endpoint)
"""
import re
import time
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

logger = logging.getLogger(__name__)

# ── Metric definitions ─────────────────────────────────────────────────────

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests handled",
    ["method", "endpoint", "status_code"],
)

HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency (seconds)",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

HTTP_ACTIVE_REQUESTS = Gauge(
    "http_active_requests",
    "Number of HTTP requests currently being processed",
)

CELERY_TASKS = Counter(
    "celery_task_total",
    "Celery tasks processed, labelled by outcome",
    ["task_name", "status"],
)

CELERY_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Celery task wall-clock duration (seconds)",
    ["task_name"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

PROCTOR_SESSIONS = Gauge(
    "proctor_active_sessions",
    "Number of in-progress proctored exam sessions",
)

ARTIFACT_QUEUE = Gauge(
    "artifact_queue_depth",
    "Number of artifact generation tasks queued or running",
)

CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_open",
    "1 = circuit open (service degraded), 0 = circuit closed (healthy)",
    ["service"],
)


# ── Path normalisation (prevent label cardinality explosion) ───────────────

_UUID_RE  = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_NUM_RE   = re.compile(r"/\d+")
_HASH_RE  = re.compile(r"/[0-9a-f]{24,}")  # mongo-style ObjectIDs

_SKIP_PATHS = frozenset({"/health", "/health/db", "/metrics", "/docs", "/redoc", "/openapi.json"})


def _normalize(path: str) -> str:
    path = _UUID_RE.sub("{id}", path)
    path = _NUM_RE.sub("/{id}", path)
    path = _HASH_RE.sub("/{id}", path)
    return path[:80]


# ── Prometheus scrape endpoint ─────────────────────────────────────────────

async def metrics_endpoint(request: Request) -> Response:
    """GET /metrics — scraped by Prometheus every 15 s."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


# ── Instrumentation middleware ─────────────────────────────────────────────

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Counts and times every request.
    Skips health/docs/metrics paths to avoid noise.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in _SKIP_PATHS:
            return await call_next(request)

        endpoint = _normalize(path)
        method   = request.method

        HTTP_ACTIVE_REQUESTS.inc()
        start = time.perf_counter()

        try:
            response = await call_next(request)
            status   = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            duration = time.perf_counter() - start
            HTTP_ACTIVE_REQUESTS.dec()
            HTTP_REQUESTS.labels(method=method, endpoint=endpoint, status_code=status).inc()
            HTTP_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

        return response


def instrument_app(app):
    """Attach Prometheus middleware and /metrics route to a FastAPI app."""
    app.add_middleware(PrometheusMiddleware)
    app.add_route("/metrics", metrics_endpoint, include_in_schema=False)
    logger.info("Prometheus instrumentation enabled — scrape at /metrics")


# ── Celery signal helpers (call from tasks.py) ─────────────────────────────

def record_celery_success(task_name: str, duration_s: float) -> None:
    CELERY_TASKS.labels(task_name=task_name, status="success").inc()
    CELERY_DURATION.labels(task_name=task_name).observe(duration_s)


def record_celery_failure(task_name: str, duration_s: float) -> None:
    CELERY_TASKS.labels(task_name=task_name, status="failure").inc()
    CELERY_DURATION.labels(task_name=task_name).observe(duration_s)
