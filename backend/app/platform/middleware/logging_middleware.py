"""
Logging Middleware for the SETTLE Payment System.

This middleware establishes the distributed context for every request by:

  1. Generating or extracting a request_id (UUID4)
  2. Propagating correlation_id from incoming X-Correlation-ID header
  3. Extracting trace_id from OpenTelemetry's active span
  4. Storing all IDs in contextvars so every log line downstream includes them

Why Correlation IDs?
────────────────────
  In a distributed system, a single user action (e.g., "make a payment") may
  trigger requests across 5+ nodes. Without a shared correlation_id, finding
  all logs related to that one payment across all nodes is nearly impossible.

  The correlation_id is set by the first entry point (API gateway or client)
  and propagated through every internal RPC. If no correlation_id is provided,
  we generate one and return it in the response headers so the client can
  use it for support tickets.

Context Flow:
─────────────
  Client → nginx → node-1 (sets correlation_id) → Raft RPC to node-2,3,4,5
                                                     (propagates correlation_id)
  All logs on all nodes for this request share the same correlation_id.
"""

import uuid
import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.platform.observability.context import request_ctx
from app.platform.observability.tracing import get_current_trace_id, get_current_span_id

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that establishes request-scoped context and logs structured
    request/response metadata.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # ── 1. Extract or generate identifiers ────────────────────────────────
        request_id = (
            request.headers.get("x-request-id")
            or str(uuid.uuid4())
        )
        correlation_id = (
            request.headers.get("x-correlation-id")
            or request_id  # Default to request_id if no correlation chain exists
        )

        # ── 2. Set context variables (available to all downstream code) ───────
        request_ctx.request_id.set(request_id)
        request_ctx.correlation_id.set(correlation_id)

        # Trace/span IDs are set by OpenTelemetry auto-instrumentation.
        # We read them here so the logging formatter can include them.
        trace_id = get_current_trace_id()
        span_id = get_current_span_id()
        if trace_id:
            request_ctx.trace_id.set(trace_id)
        if span_id:
            request_ctx.span_id.set(span_id)

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            duration = time.perf_counter() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"duration={duration:.3f}s error={exc!r}",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "trace_id": trace_id,
                },
            )
            raise
        finally:
            # Clear context at end of request to prevent leaking across requests
            request_ctx.clear()

        duration = time.perf_counter() - start_time

        # ── 3. Add correlation headers to response ────────────────────────────
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        if trace_id:
            response.headers["X-Trace-ID"] = trace_id

        # ── 4. Log the completed request ──────────────────────────────────────
        # Skip noisy internal endpoints
        path = request.url.path
        if path not in ("/metrics", "/api/v1/metrics", "/health", "/api/v1/health"):
            logger.info(
                f"{request.method} {path} → {response.status_code} "
                f"({duration:.3f}s)",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "trace_id": trace_id,
                    "event": "HTTP_REQUEST",
                },
            )

        return response
