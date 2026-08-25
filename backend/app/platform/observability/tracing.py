"""
OpenTelemetry Distributed Tracing for the SETTLE Payment System.

Distributed Tracing Concepts:
─────────────────────────────
  Trace   – A complete end-to-end journey of a single request across all services/nodes.
            Composed of multiple spans. Identified by a globally unique trace_id.

  Span    – A single unit of work within a trace (e.g., "stripe.create_intent", 
            "raft.submit_command"). Each span has a start time, end time, attributes,
            and a parent span (forming a tree).

  Context Propagation – Mechanism for passing trace_id and span_id across process
            boundaries (e.g., between SETTLE nodes via HTTP headers). We use the
            W3C TraceContext standard (traceparent/tracestate headers).

  Exporter – Ships completed spans to a tracing backend. We use the OTLP exporter
            which sends spans to Jaeger's OTLP endpoint.

Architecture:
─────────────
  FastAPI Request → OpenTelemetry auto-instrumentation creates root span
    → Payment Service creates child span "payment.initiate"
      → Stripe Service creates child span "stripe.create_intent"
      → Raft Node creates child span "raft.submit_command"
        → Per-peer child spans "raft.replicate.{peer_id}"
    → Webhook handler creates child span "webhook.process"

  All spans are batched and exported to Jaeger via OTLP gRPC.
"""

import logging
from typing import Optional

from app.platform.core.config import settings

logger = logging.getLogger(__name__)

# ── Module-level state ────────────────────────────────────────────────────────
_tracer_provider = None
_tracer = None
_initialized = False


def init_tracing() -> None:
    """
    Initialize OpenTelemetry tracing with Jaeger exporter.
    
    Must be called once during application startup (in FastAPI lifespan).
    Subsequent calls are no-ops.
    """
    global _tracer_provider, _tracer, _initialized

    if _initialized:
        return

    if not settings.TRACING_ENABLED:
        logger.info("Distributed tracing is disabled (TRACING_ENABLED=false).")
        _initialized = True
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        # Resource describes this service to the tracing backend
        resource = Resource.create({
            SERVICE_NAME: "settle",
            "service.namespace": "settle-cluster",
            "service.instance.id": settings.NODE_ID,
            "deployment.environment": "development",
        })

        # Sampler controls what percentage of traces are recorded
        sampler = TraceIdRatioBased(settings.TRACING_SAMPLE_RATE)

        _tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler,
        )

        # OTLP exporter sends spans to Jaeger's OTLP gRPC endpoint
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.JAEGER_OTLP_ENDPOINT,
            insecure=True,  # No TLS in dev; TODO(security): enable TLS in production
        )

        # BatchSpanProcessor batches spans before export for efficiency
        span_processor = BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=5000,
        )
        _tracer_provider.add_span_processor(span_processor)

        # Set as the global tracer provider
        trace.set_tracer_provider(_tracer_provider)

        # Auto-instrument httpx (used for inter-node Raft RPCs)
        # This propagates trace context in outgoing HTTP requests automatically
        HTTPXClientInstrumentor().instrument()

        _tracer = trace.get_tracer("settle", "1.0.0")
        _initialized = True

        logger.info(
            f"OpenTelemetry tracing initialized. "
            f"Exporting to {settings.JAEGER_OTLP_ENDPOINT} "
            f"(sample_rate={settings.TRACING_SAMPLE_RATE})"
        )

    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry tracing: {e}", exc_info=True)
        _initialized = True  # Don't retry on every call


def instrument_app(app) -> None:
    """
    Apply FastAPI auto-instrumentation to the given app instance.
    
    This creates a root span for every incoming HTTP request with attributes
    like http.method, http.url, http.status_code, etc.
    
    Must be called AFTER init_tracing() and AFTER the FastAPI app is created.
    """
    if not settings.TRACING_ENABLED:
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="metrics,health",  # Don't trace health checks and metrics scraping
        )
        logger.info("FastAPI OpenTelemetry instrumentation applied.")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}", exc_info=True)


def shutdown_tracing() -> None:
    """Flush pending spans and shut down the tracer provider. Call on app shutdown."""
    global _initialized

    if _tracer_provider is not None:
        try:
            _tracer_provider.shutdown()
            logger.info("OpenTelemetry tracer provider shut down.")
        except Exception as e:
            logger.error(f"Error shutting down tracer provider: {e}")
    _initialized = False


def get_tracer():
    """
    Returns the application tracer for creating custom spans.
    
    Usage:
        tracer = get_tracer()
        if tracer:
            with tracer.start_as_current_span("my_operation") as span:
                span.set_attribute("key", "value")
                # ... do work ...
    """
    return _tracer


def get_current_trace_id() -> str:
    """Returns the current trace ID as a hex string, or empty string if no active span."""
    if not settings.TRACING_ENABLED:
        return ""
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id:
            return format(ctx.trace_id, "032x")
    except Exception:
        pass
    return ""


def get_current_span_id() -> str:
    """Returns the current span ID as a hex string, or empty string if no active span."""
    if not settings.TRACING_ENABLED:
        return ""
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.span_id:
            return format(ctx.span_id, "016x")
    except Exception:
        pass
    return ""
