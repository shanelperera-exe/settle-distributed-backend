"""
Prometheus Metrics Scrape Endpoint.

This endpoint exposes all registered Prometheus metrics in the standard
text-based exposition format that Prometheus expects when scraping targets.

Prometheus scrapes this endpoint at a configured interval (default: 15s)
and stores the time-series data for querying via PromQL.

The endpoint is intentionally unauthenticated — this is the standard
Prometheus convention. In production, restrict access via network policies
(e.g., only allow traffic from the Prometheus container on the internal
Docker network).

TODO(security): In production, restrict /metrics to internal network only.
"""

from fastapi import APIRouter
from fastapi.responses import Response

from app.platform.observability.metrics import REGISTRY, generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Exposes application metrics in Prometheus text format for scraping.",
    tags=["Monitoring"],
    include_in_schema=False,  # Hide from OpenAPI docs — internal use only
)
async def metrics():
    """
    Returns all registered Prometheus metrics in text exposition format.
    
    Prometheus scrapes this endpoint periodically to collect time-series data
    for dashboards, alerting, and capacity planning.
    """
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
