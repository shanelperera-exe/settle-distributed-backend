"""
HTTP Metrics Middleware for the SETTLE Payment System.

This middleware intercepts every HTTP request/response cycle and records three
key signals into Prometheus:

  1. http_requests_total (Counter)
     Labeled by: method, endpoint, status_code, node_id
     → "How many requests of each type have we served?"

  2. http_request_duration_seconds (Histogram)
     Labeled by: method, endpoint, node_id
     → "How long did each request take?" — enables p50/p95/p99 latency queries.

  3. http_requests_in_progress (Gauge)
     Labeled by: node_id
     → "How many requests are we handling right now?" — detects overload.

Middleware Ordering:
────────────────────
  This middleware should be registered FIRST (outermost) so that it captures
  the full request lifecycle including time spent in other middleware layers.
  In Starlette/FastAPI, middleware is executed in LIFO order, so the LAST
  middleware added via app.add_middleware() is the FIRST to execute.
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.platform.core.config import settings
from app.platform.observability.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
)

# Paths to exclude from metrics collection to prevent recursive scraping
# and noisy health check metrics.
_EXCLUDED_PATHS = frozenset({"/metrics", "/api/v1/metrics", "/health", "/api/v1/health"})


def _normalize_path(path: str) -> str:
    """
    Normalize request paths to prevent label cardinality explosion.

    Dynamic path segments (UUIDs, IDs) are replaced with placeholders.
    Without this, every unique payment ID would create a new time series,
    eventually causing Prometheus OOM.

    Example: /api/v1/payments/pay_abc123 → /api/v1/payments/{id}
    """
    parts = path.rstrip("/").split("/")
    normalized = []
    for part in parts:
        # Replace segments that look like IDs (UUIDs, pay_xxx, txn_xxx, etc.)
        if part.startswith(("pay_", "txn_", "led_", "req_")):
            normalized.append("{id}")
        elif len(part) > 20 and any(c.isdigit() for c in part):
            # Long alphanumeric strings are likely IDs
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/".join(normalized) or "/"


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that collects HTTP request metrics for Prometheus.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip metrics collection for excluded paths
        if path in _EXCLUDED_PATHS:
            return await call_next(request)

        method = request.method
        endpoint = _normalize_path(path)
        node_id = settings.NODE_ID

        # Track in-progress requests
        http_requests_in_progress.labels(node_id=node_id).inc()
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            duration = time.perf_counter() - start_time

            # Record metrics
            http_requests_total.labels(
                node_id=node_id,
                method=method,
                endpoint=endpoint,
                status=status,
            ).inc()

            http_request_duration_seconds.labels(
                node_id=node_id,
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            http_requests_in_progress.labels(node_id=node_id).dec()

        return response
