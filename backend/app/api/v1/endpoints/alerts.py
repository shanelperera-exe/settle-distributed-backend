import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.platform.observability.alerts import alert_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

async def alert_event_generator(request: Request):
    q = await alert_manager.subscribe()
    try:
        while True:
            if await request.is_disconnected():
                break
            
            try:
                # Wait for an alert with a small timeout so we can periodically check if client disconnected
                alert = await asyncio.wait_for(q.get(), timeout=1.0)
                yield f"data: {json.dumps(alert)}\n\n"
            except asyncio.TimeoutError:
                # Send a keep-alive comment to prevent connection from dropping
                yield ": keep-alive\n\n"
    except Exception as e:
        logger.error(f"SSE Error: {e}")
    finally:
        alert_manager.unsubscribe(q)

from pydantic import BaseModel

class AlertSyncPayload(BaseModel):
    category: str
    rule: str
    instance_id: str
    active: bool
    message: str = ""
    severity: str = "error"
    labels: dict = {}

@router.post("/internal/sync")
async def sync_alert(payload: AlertSyncPayload):
    alert_manager.set_alert_state(
        category=payload.category,
        rule=payload.rule,
        instance_id=payload.instance_id,
        active=payload.active,
        message=payload.message,
        severity=payload.severity,
        sync=False,
        labels=payload.labels
    )
    return {"status": "ok"}

@router.post("/webhook")
async def alertmanager_webhook(request: Request):
    """
    Receives alerts pushed from Prometheus Alertmanager.
    """
    try:
        payload = await request.json()
        from app.platform.observability.alerts import RULE_CATEGORIES
        
        # Build reverse map for category lookup
        rule_to_category = {}
        for cat, rules in RULE_CATEGORIES.items():
            for rule_name in rules:
                rule_to_category[rule_name] = cat
                
        alerts = payload.get("alerts", [])
        for alert in alerts:
            status = alert.get("status")
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            
            rule_name = labels.get("alertname")
            category = rule_to_category.get(rule_name, "unknown")
            
            # Use 'instance' label if available, otherwise cluster
            instance_id = labels.get("instance", "cluster")
            # Strip port from instance if present for cleaner UI
            if ":" in instance_id:
                instance_id = instance_id.split(":")[0]
                
            active = (status == "firing")
            message = annotations.get("description", "No description provided.")
            severity = labels.get("severity", "error")
            
            alert_manager.set_alert_state(
                category=category,
                rule=rule_name,
                instance_id=instance_id,
                active=active,
                message=message,
                severity=severity,
                sync=True, # Sync to other UI connected nodes
                labels=labels
            )
            
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to process Alertmanager webhook: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/stream")
async def stream_alerts(request: Request):
    """
    Server-Sent Events (SSE) endpoint to stream real-time system alerts.
    """
    return StreamingResponse(
        alert_event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/history")
async def get_alert_history():
    """
    Get the recent history of alerts.
    """
    return {"alerts": alert_manager.alerts}
