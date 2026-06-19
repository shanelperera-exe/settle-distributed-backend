"""
Request-scoped context using Python's contextvars.

In a distributed system, every request must carry identifiers that allow operators to
correlate logs, traces, and metrics across multiple nodes and services. Python's
`contextvars` module provides task-local storage that works correctly with asyncio —
each concurrent request gets its own isolated copy of these variables.

Usage:
    from app.platform.observability.context import request_ctx

    # In middleware (set once per request):
    request_ctx.request_id.set("req_abc123")

    # Anywhere downstream (read from any layer):
    rid = request_ctx.request_id.get()
"""

from contextvars import ContextVar
from typing import Optional


class RequestContext:
    """
    Centralized container for all request-scoped context variables.

    Each variable defaults to an empty string so that log formatters and metric
    labels never encounter None or raise LookupError when accessed outside a
    request lifecycle (e.g., during startup or background tasks).
    """

    # ── Core Request Identifiers ──────────────────────────────────────────────
    request_id: ContextVar[str] = ContextVar("request_id", default="")
    correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
    trace_id: ContextVar[str] = ContextVar("trace_id", default="")
    span_id: ContextVar[str] = ContextVar("span_id", default="")

    # ── Business Context ──────────────────────────────────────────────────────
    transaction_id: ContextVar[str] = ContextVar("transaction_id", default="")
    payment_id: ContextVar[str] = ContextVar("payment_id", default="")
    event_type: ContextVar[str] = ContextVar("event_type", default="")

    def clear(self) -> None:
        """Resets all context variables to their defaults. Called at request end."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, ContextVar):
                attr.set("")


# Singleton — import this everywhere
request_ctx = RequestContext()
