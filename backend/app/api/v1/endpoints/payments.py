import asyncio
import uuid
import socket
import httpx

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status, Query
from typing import Dict, Any, List, Optional
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from app.platform.infrastructure.db.session import get_db
from app.contracts.payment import PaymentCreate, PaymentResponse
from app.modules.payments.models import Payment, PaymentStatus
from app.financial.ledger.models import LedgerEntry, LedgerStatus
from app.modules.payments.repositories import PaymentRepository
from app.financial.ledger.repositories import LedgerRepository
from app.financial.idempotency.manager import IdempotencyManager, IdempotencyException
from app.platform.core.config import settings
from app.platform.observability.logging import logger

from app.platform.integrations.stripe_service import stripe_service
from app.modules.payments.services import PaymentService
from app.platform.infrastructure.cache.redis_client import redis_cache
import hashlib
import json

router = APIRouter()


def _resolve_leader_ip(leader_id: str) -> str:
    """Resolve leader hostname to IPv4 to avoid Docker DNS AAAA hang."""
    from app.platform.distributed.raft.node import raft_node
    cached = raft_node.peer_ips.get(leader_id)
    if cached:
        return cached
    try:
        return socket.gethostbyname(leader_id)
    except Exception:
        return leader_id

async def _enforce_linearizable_read(request: Request):
    """
    Ensures strict linearizability.
    1. Proxies to Leader if not Leader.
    2. Awaits ReadIndex protocol if Leader.
    Returns JSONResponse if proxied, None if local read is safe.
    """
    from app.platform.distributed.failover_service import FailoverService
    from app.platform.distributed.raft.node import raft_node

    if not FailoverService.is_leader():
        if request.headers.get("x-raft-proxied"):
            raise HTTPException(status_code=503, detail="Cluster is electing a new leader. Please retry.")

        leader_id = None
        for _ in range(50):
            leader_id = FailoverService.get_leader_id()
            if leader_id:
                break
            await asyncio.sleep(0.1)

        if not leader_id:
            raise HTTPException(status_code=503, detail="Cluster is electing a new leader. Please retry.")

        leader_ip = _resolve_leader_ip(leader_id)
        path = request.url.path
        query = request.url.query
        target_url = f"http://{leader_ip}:{settings.INTERNAL_PORT}{path}"
        if query:
            target_url += f"?{query}"

        logger.info(f"Proxying GET request to leader {leader_id} ({leader_ip})")

        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("Content-Length", None)
        headers["x-raft-proxied"] = "true"
        headers["host"] = f"{leader_ip}:{settings.INTERNAL_PORT}"

        last_error = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(target_url, headers=headers)
                return JSONResponse(status_code=resp.status_code, content=resp.json())
            except Exception as e:
                last_error = e
                await asyncio.sleep(0.3 * (attempt + 1))

        logger.error(f"All proxy attempts failed: {last_error}")
        raise HTTPException(status_code=502, detail="Bad Gateway — leader unreachable.")
    else:
        # We are the leader, execute ReadIndex protocol
        is_linearizable = await raft_node.wait_for_linearizable_read()
        if not is_linearizable:
            raise HTTPException(status_code=503, detail="Lost leadership during ReadIndex protocol. Please retry.")
        return None

@router.post("/", response_model=Dict[str, Any])
async def process_payment(
    request: Request,
    payment_in: PaymentCreate,
    idempotency_key: str = Header(..., description="Unique key for deduplication"),
    db: Session = Depends(get_db),
):
    from app.platform.distributed.failover_service import FailoverService

    # --- Step 0: Leadership check + transparent proxy with retry ---
    if not FailoverService.is_leader():
        # If this request has already been proxied once, do not proxy again.
        if request.headers.get("x-raft-proxied"):
            raise HTTPException(status_code=503, detail="Cluster is electing a new leader. Please retry.")

        # Wait up to 5 seconds for a stable leader before giving up.
        leader_id = None
        for _ in range(50):
            leader_id = FailoverService.get_leader_id()
            if leader_id:
                break
            await asyncio.sleep(0.1)

        if not leader_id:
            raise HTTPException(status_code=503, detail="Cluster is electing a new leader. Please retry.")

        leader_ip = _resolve_leader_ip(leader_id)
        target_url = f"http://{leader_ip}:{settings.INTERNAL_PORT}/api/v1/payments/"
        logger.info(f"Proxying payment to leader {leader_id} ({leader_ip})")

        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("Content-Length", None)
        headers["x-raft-proxied"] = "true"
        headers["host"] = f"{leader_ip}:{settings.INTERNAL_PORT}"

        # Retry the proxy up to 3 times in case the leader steps down mid-flight.
        last_error = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        target_url,
                        headers=headers,
                        json=payment_in.model_dump(mode="json"),
                    )
                return JSONResponse(status_code=resp.status_code, content=resp.json())
            except Exception as e:
                last_error = e
                logger.warning(f"Proxy attempt {attempt + 1} failed: {e}. Retrying...")
                await asyncio.sleep(0.3 * (attempt + 1))

        logger.error(f"All proxy attempts failed: {last_error}")
        raise HTTPException(status_code=502, detail="Bad Gateway — leader unreachable after retries.")

    # --- Step 1: Idempotency / dedup check ---
    dedup_manager = IdempotencyManager(db)
    try:
        is_dup, cached_body, cached_code = await dedup_manager.check_or_create_lock(
            idempotency_key, payment_in.model_dump(mode="json")
        )
        if is_dup:
            return JSONResponse(status_code=cached_code, content=cached_body)
    except IdempotencyException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    try:
        # --- Step 2: Create Stripe PaymentIntent (offloaded so event loop stays free) ---
        intent = await asyncio.to_thread(
            stripe_service.create_payment_intent,
            amount=payment_in.amount,
            currency=payment_in.currency,
            idempotency_key=idempotency_key,
            payment_method=payment_in.payment_method
        )

        # --- Step 3: Propose PAYMENT_INIT to the Raft log ---
        payment_service = PaymentService(db)
        payment = await payment_service.initiate_payment(
            payment_in=payment_in,
            idempotency_key=idempotency_key,
            stripe_intent_id=intent.id,
        )

        # --- Step 3b: Auto-finalize if synchronous confirmation succeeded ---
        if intent.status == "succeeded":
            from app.platform.distributed.raft.node import raft_node
            # Wait for the state machine to apply the init command to the DB
            target = raft_node.state.commit_index
            while raft_node.state.last_applied < target:
                await asyncio.sleep(0.01)
            await payment_service.finalize_payment(intent.id, success=True)
            payment.status = PaymentStatus.COMPLETED

        response_data = {
            "payment_id": payment.id,
            "transaction_id": payment.transaction_id,
            "stripe_payment_intent_id": intent.id,
            "client_secret": intent.client_secret,
            "status": payment.status.value,
        }

        await dedup_manager.finalize(idempotency_key, payment.id, 200, response_data)
        return JSONResponse(status_code=200, content=response_data)

    except Exception as e:
        logger.error(f"Error processing payment: {e}", exc_info=True)
        await dedup_manager.release_lock_on_failure(idempotency_key)
        msg = str(e).lower()
        if "quorum" in msg or "leadership" in msg or "not the leader" in msg:
            raise HTTPException(status_code=503, detail="Leader changed mid-transaction. Please retry.")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=List[Dict[str, Any]])
async def list_payments(
    request: Request, 
    db: Session = Depends(get_db), 
    skip: int = 0, 
    limit: int = 100,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    amount: Optional[float] = Query(None, description="Exact amount"),
    customer_id: Optional[str] = Query(None, description="Sender or Receiver ID"),
    intent_id: Optional[str] = Query(None, description="Stripe Payment Intent ID")
):
    """
    List all payments with advanced filtering.
    Enforces Strict Linearizability via Raft ReadIndex Protocol.
    """
    proxy_resp = await _enforce_linearizable_read(request)
    if proxy_resp:
        return proxy_resp

    # Bypass cache if any advanced filters are applied
    has_filters = any([start_date, end_date, amount, customer_id, intent_id])
    
    if not has_filters:
        cache_key = f"payments_list:{skip}:{limit}"
        cached_data = await redis_cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache HIT for {cache_key}")
            return cached_data
            
        logger.info(f"Cache MISS for {cache_key}")

    query = db.query(Payment)

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Payment.created_at >= start_dt)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Payment.created_at < end_dt)
        except ValueError:
            pass
            
    if amount is not None:
        query = query.filter(Payment.amount == amount)
        
    if customer_id:
        from sqlalchemy import or_
        query = query.filter(or_(Payment.sender_id == customer_id, Payment.receiver_id == customer_id))
        
    # In Settle, intent ID is often stored in transaction_id for Stripe payments
    if intent_id:
        query = query.filter(Payment.transaction_id == intent_id)

    payments = query.order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()
    
    response_data = [
        {
            "payment_id": p.id,
            "transaction_id": p.transaction_id,
            "amount": float(p.amount) if p.amount else 0.0,
            "currency": p.currency,
            "sender_id": p.sender_id,
            "receiver_id": p.receiver_id,
            "payment_method": getattr(p, "payment_method", "pm_card_visa"),
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "created_at": p.created_at.isoformat() if p.created_at else None
        } for p in payments
    ]
    
    if not has_filters:
        await redis_cache.set(cache_key, response_data, expire=10)
        
    return response_data

@router.get("/stats/volume")
async def get_volume_stats(
    request: Request,
    db: Session = Depends(get_db),
    metric: str = Query("gross", description="gross, net, successful"),
    time_range: str = Query("7d", description="today, yesterday, 7d, 30d, custom"),
    custom_date: str = Query(None, description="YYYY-MM-DD format for custom time range")
):
    """
    Get aggregated volume statistics for the payment insights dashboard.
    """
    proxy_resp = await _enforce_linearizable_read(request)
    if proxy_resp:
        return proxy_resp

    cache_key = f"volume_stats:{metric}:{time_range}:{custom_date or 'none'}"
    cached_data = await redis_cache.get(cache_key)
    if cached_data:
        logger.info(f"Cache HIT for {cache_key}")
        return cached_data
        
    logger.info(f"Cache MISS for {cache_key}")
    now = datetime.utcnow()
    if time_range == "custom" and custom_date:
        try:
            start_date = datetime.strptime(custom_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
            now = start_date + timedelta(days=1)
            prev_start_date = start_date - timedelta(days=1)
            prev_end_date = start_date
        except ValueError:
            # Fallback to today if format is invalid
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            prev_start_date = start_date - timedelta(days=1)
            prev_end_date = start_date
    elif time_range == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        prev_start_date = start_date - timedelta(days=1)
        prev_end_date = start_date
    elif time_range == "yesterday":
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        now = start_date + timedelta(days=1)
        prev_start_date = start_date - timedelta(days=1)
        prev_end_date = start_date
    elif time_range == "30d":
        start_date = now - timedelta(days=30)
        prev_start_date = start_date - timedelta(days=30)
        prev_end_date = start_date
    else:
        # Default 7d
        start_date = now - timedelta(days=7)
        prev_start_date = start_date - timedelta(days=7)
        prev_end_date = start_date

    # Base query for successful payments
    query = db.query(Payment).filter(
        Payment.created_at >= start_date, 
        Payment.created_at <= now, 
        Payment.status == PaymentStatus.COMPLETED
    )
    
    payments = query.all()
    
    # Previous period query
    prev_query = db.query(Payment).filter(
        Payment.created_at >= prev_start_date,
        Payment.created_at < prev_end_date,
        Payment.status == PaymentStatus.COMPLETED
    )
    prev_payments = prev_query.all()
    
    total_gross = sum(float(p.amount) for p in payments)
    total_net = sum(float(p.amount) * 0.97 for p in payments) # Assume 3% fee
    total_count = len(payments)
    
    prev_gross = sum(float(p.amount) for p in prev_payments)
    prev_net = sum(float(p.amount) * 0.97 for p in prev_payments)
    prev_count = len(prev_payments)
    
    bins = defaultdict(lambda: {"gross": 0, "net": 0, "count": 0})
    
    for p in payments:
        if time_range in ["today", "yesterday"]:
            bin_key = p.created_at.strftime("%I %p") # e.g. "01 PM"
        else:
            bin_key = p.created_at.strftime("%b %d") # e.g. "Jun 23"
            
        bins[bin_key]["gross"] += float(p.amount)
        bins[bin_key]["net"] += float(p.amount) * 0.97
        bins[bin_key]["count"] += 1
        
    timeseries = [{"time": k, "value": round(v["count"] if metric == "successful" else v[metric], 2)} for k, v in bins.items()]
    
    current_value = total_count if metric == "successful" else (total_net if metric == "net" else total_gross)
    previous_value = prev_count if metric == "successful" else (prev_net if metric == "net" else prev_gross)
    
    # Calculate 24h gross for the massive KPI block
    last_24h_start = datetime.utcnow() - timedelta(days=1)
    last_24h_payments = db.query(Payment).filter(
        Payment.created_at >= last_24h_start,
        Payment.status == PaymentStatus.COMPLETED
    ).all()
    total_gross_24h = sum(float(p.amount) for p in last_24h_payments)
    
    response_data = {
        "metric": metric,
        "time_range": time_range,
        "current_value": round(current_value, 2),
        "previous_value": round(previous_value, 2),
        "total_gross_24h": round(total_gross_24h, 2),
        "timeseries": timeseries
    }
    
    await redis_cache.set(cache_key, response_data, expire=15)
    return response_data

@router.get("/{payment_id}", response_model=Dict[str, Any])
async def get_payment(payment_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Get a specific payment by ID.
    Enforces Strict Linearizability via Raft ReadIndex Protocol.
    """
    proxy_resp = await _enforce_linearizable_read(request)
    if proxy_resp:
        return proxy_resp

    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    return {
        "payment_id": payment.id,
        "transaction_id": payment.transaction_id,
        "amount": float(payment.amount) if payment.amount else 0.0,
        "currency": payment.currency,
        "sender_id": payment.sender_id,
        "receiver_id": payment.receiver_id,
        "status": payment.status.value if hasattr(payment.status, "value") else str(payment.status)
    }
