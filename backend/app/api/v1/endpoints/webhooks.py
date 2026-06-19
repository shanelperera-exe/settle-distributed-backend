from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from app.platform.infrastructure.db.session import get_db
from app.platform.integrations.stripe_service import stripe_service
from app.modules.payments.services import PaymentService
from app.platform.core.config import settings
from app.platform.observability.logging import logger
from app.platform.observability.metrics import webhook_processing_duration_seconds
from fastapi.responses import JSONResponse
import time
import httpx

router = APIRouter()

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Handles asynchronous webhook events from Stripe.
    """
    from app.platform.distributed.failover_service import FailoverService
    
    # 0. Raft Leadership Check & Proxy
    if not FailoverService.is_leader():
        leader_id = FailoverService.get_leader_id()
        if not leader_id:
            raise HTTPException(status_code=503, detail="Cluster is electing a new leader. Please retry.")
        
        from app.platform.distributed.raft.node import raft_node
        
        leader_ip = raft_node.peer_ips.get(leader_id)
        if not leader_ip:
            import socket
            try:
                leader_ip = socket.gethostbyname(leader_id)
            except Exception:
                leader_ip = leader_id

        logger.info(f"Proxying webhook to Raft Leader: {leader_id} ({leader_ip})")
        target_url = f"http://{leader_ip}:{settings.INTERNAL_PORT}/api/v1/webhooks/stripe"
        
        async with httpx.AsyncClient() as client:
            headers = dict(request.headers)
            headers.pop("content-length", None)
            headers.pop("Content-Length", None)
            headers.pop("host", None)
            headers.pop("Host", None)
            
            if headers.get("x-raft-proxied"):
                raise HTTPException(status_code=500, detail="Proxy loop detected")
            headers["x-raft-proxied"] = "true"
            
            body = await request.body()
            
            try:
                resp = await client.post(target_url, headers=headers, content=body)
                return JSONResponse(status_code=resp.status_code, content=resp.json() if resp.text else {})
            except Exception as e:
                logger.error(f"Failed to proxy webhook to leader: {e}")
                raise HTTPException(status_code=502, detail="Bad Gateway - Leader unresponsive")

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing signature")
        
    payload = await request.body()
    
    try:
        event = stripe_service.construct_webhook_event(payload, stripe_signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
    payment_service = PaymentService(db)
    
    # Stripe strongly recommends making webhooks asynchronous/fast, 
    # but since this requires distributed quorum, we process it inline here.
    # If the quorum fails or times out, we return 500 and Stripe will safely retry later.
    webhook_start = time.perf_counter()
    try:
        if event.type == 'payment_intent.succeeded':
            payment_intent = event.data.object
            await payment_service.finalize_payment(payment_intent.id, success=True)
            
        elif event.type == 'payment_intent.payment_failed':
            payment_intent = event.data.object
            await payment_service.finalize_payment(payment_intent.id, success=False)
            
        elif event.type == 'payment_intent.canceled':
            payment_intent = event.data.object
            await payment_service.finalize_payment(payment_intent.id, success=False)
            
        else:
            logger.info(f"Unhandled Stripe event type: {event.type}")
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Error processing webhook")
    finally:
        webhook_processing_duration_seconds.labels(
            node_id=settings.NODE_ID, event_type=event.type
        ).observe(time.perf_counter() - webhook_start)
        
    return {"status": "success"}

