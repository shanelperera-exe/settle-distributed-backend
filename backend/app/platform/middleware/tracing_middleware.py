"""
Tracing Middleware for the SETTLE Payment System.

This middleware adds SETTLE-specific span attributes to the OpenTelemetry
auto-instrumented spans. The FastAPIInstrumentor already creates root spans
for every request, but we enrich them with distributed system context:

  - node_id: which cluster node handled this request
  - raft.role: LEADER / FOLLOWER / CANDIDATE at the time of the request
  - raft.term: current Raft consensus term

This enrichment makes Jaeger traces immediately useful for debugging
distributed payment failures — you can see which node was leader, what
term it was in, and correlate with Raft state changes.
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.platform.core.config import settings

logger = logging.getLogger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Enriches OpenTelemetry spans with SETTLE-specific distributed system attributes.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not settings.TRACING_ENABLED:
            return await call_next(request)

        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            if span and span.is_recording():
                # Add SETTLE-specific attributes
                span.set_attribute("settle.node_id", settings.NODE_ID)

                # Safely read Raft state (may not be initialized yet during startup)
                try:
                    from app.platform.distributed.raft.node import raft_node
                    span.set_attribute("settle.raft.role", raft_node.state.role.name)
                    span.set_attribute("settle.raft.term", raft_node.state.current_term)
                    if raft_node.state.leader_id:
                        span.set_attribute("settle.raft.leader_id", raft_node.state.leader_id)
                except Exception:
                    pass  # Raft not yet initialized
        except Exception as e:
            logger.debug(f"Failed to enrich span: {e}")

        return await call_next(request)
