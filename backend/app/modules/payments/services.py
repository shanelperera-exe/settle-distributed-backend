import uuid
import time
from sqlalchemy.orm import Session
from app.modules.payments.models import Payment, PaymentStatus
from app.financial.ledger.models import LedgerEntry, TransactionType, LedgerStatus
from app.modules.payments.repositories import PaymentRepository
from app.financial.ledger.repositories import LedgerRepository
from app.platform.distributed.raft.node import raft_node
from app.platform.distributed.failover_service import FailoverService
from app.platform.core.config import settings
from app.platform.observability.logging import logger
from app.platform.observability.context import request_ctx
from app.platform.observability.metrics import (
    payments_processed_total,
    payments_failed_total,
    payments_pending,
    payment_processing_duration_seconds,
)
from app.platform.observability.tracing import get_tracer

_finalized_intents = set()

class PaymentService:
    """
    Orchestrates the distributed logic for handling payments and webhooks using RAFT.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.payment_repo = PaymentRepository(db)
        self.ledger_repo = LedgerRepository(db)

    def _to_dict(self, obj):
        from decimal import Decimal
        from datetime import datetime
        d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        for k, v in d.items():
            if isinstance(v, Decimal):
                d[k] = float(v)
            elif hasattr(v, 'value'): # Enum
                d[k] = v.value
            elif isinstance(v, datetime):
                d[k] = v.isoformat()
        return d

    async def initiate_payment(self, payment_in, idempotency_key: str, stripe_intent_id: str) -> dict:
        """
        Step 1: Client API initiates payment.
        Must be executed on the Leader. Proposes PAYMENT_INIT to the Raft log.
        """
        FailoverService.ensure_leader()
        start_time = time.perf_counter()
        
        transaction_id = f"txn_{uuid.uuid4().hex}"
        payment_id = f"pay_{uuid.uuid4().hex}"
        
        # Set context for distributed log correlation
        request_ctx.transaction_id.set(transaction_id)
        request_ctx.payment_id.set(payment_id)
        
        # Track pending payments
        payments_pending.labels(node_id=settings.NODE_ID).inc()
        
        tracer = get_tracer()
        init_success = False
        
        try:
            # 1. Prepare Local Model Representation
            new_payment = Payment(
                id=payment_id,
                transaction_id=transaction_id,
                stripe_payment_intent_id=stripe_intent_id,
                idempotency_key=idempotency_key,
                amount=payment_in.amount,
                currency=payment_in.currency,
                sender_id=payment_in.sender_id,
                receiver_id=payment_in.receiver_id,
                payment_method=payment_in.payment_method,
                status=PaymentStatus.PENDING,
                originating_node_id=settings.NODE_ID,
                processing_node_id=settings.NODE_ID,
                committed=True,
                replicated=True
            )
            
            # 2. Propose to Raft Log
            command = {
                "type": "PAYMENT_INIT",
                "payment": self._to_dict(new_payment)
            }
                
            # 3. Wait for Majority Quorum Commit
            if tracer:
                with tracer.start_as_current_span("raft.submit_command") as span:
                    span.set_attribute("settle.payment_id", payment_id)
                    span.set_attribute("settle.transaction_id", transaction_id)
                    span.set_attribute("settle.command_type", "PAYMENT_INIT")
                    quorum_achieved = await raft_node.submit_command(command)
            else:
                quorum_achieved = await raft_node.submit_command(command)
            
            if quorum_achieved:
                duration = time.perf_counter() - start_time
                payment_processing_duration_seconds.labels(
                    node_id=settings.NODE_ID, stage="initiate"
                ).observe(duration)
                init_success = True
                return new_payment
            else:
                payments_failed_total.labels(
                    node_id=settings.NODE_ID, reason="quorum_failure"
                ).inc()
                raise Exception("Failed to achieve quorum for payment initialization.")
        except Exception:
            raise
        finally:
            if not init_success:
                payments_pending.labels(node_id=settings.NODE_ID).dec()

    async def finalize_payment(self, stripe_intent_id: str, success: bool):
        """
        Step 2: Stripe Webhook arrival.
        Must be executed on the Leader. Proposes PAYMENT_FINALIZE to the Raft log.
        """
        FailoverService.ensure_leader()
        start_time = time.perf_counter()
        
        import asyncio
        payment = None
        for _ in range(10):
            payment = await asyncio.to_thread(self.payment_repo.get_by_stripe_intent_id, stripe_intent_id)
            if payment:
                break
            await asyncio.sleep(0.5)
            
        if not payment:
            logger.warning(f"Received webhook for unknown PaymentIntent: {stripe_intent_id}. Triggering retry.")
            raise Exception(f"PaymentIntent {stripe_intent_id} not found in DB yet.")
            
        if payment.status in [PaymentStatus.COMPLETED, PaymentStatus.FAILED, PaymentStatus.CANCELLED]:
            logger.info(f"Payment {payment.id} already finalized. Ignoring duplicate webhook.")
            return

        if stripe_intent_id in _finalized_intents:
            logger.info(f"Payment {payment.id} already finalizing in-memory. Ignoring duplicate webhook.")
            return

        _finalized_intents.add(stripe_intent_id)

        # Set context for log correlation
        request_ctx.payment_id.set(payment.id)
        request_ctx.transaction_id.set(payment.transaction_id)

        final_status = PaymentStatus.COMPLETED if success else PaymentStatus.FAILED
        
        # 1. Prepare Ledger Entry (Double-Entry Accounting)
        ledger_entry = LedgerEntry(
            id=f"led_{uuid.uuid4().hex}",
            transaction_id=payment.transaction_id,
            leader_node=settings.NODE_ID,
            debit_account_id=payment.sender_id, # Deduct from sender
            credit_account_id=payment.receiver_id, # Add to receiver
            transaction_type=TransactionType.DEPOSIT, # This is a deposit from Stripe
            amount=payment.amount,
            currency=payment.currency,
            status=LedgerStatus.COMMITTED if success else LedgerStatus.ROLLED_BACK
        )
        
        # 2. Propose to Raft Log
        command = {
            "type": "PAYMENT_FINALIZE",
            "payment_id": payment.id,
            "status": final_status.value,
            "ledger_entries": [self._to_dict(ledger_entry)]
        }
        
        # 3. Wait for Majority Quorum Commit
        try:
            quorum_achieved = await raft_node.submit_command(command)
            
            duration = time.perf_counter() - start_time
            payment_processing_duration_seconds.labels(
                node_id=settings.NODE_ID, stage="finalize"
            ).observe(duration)
            
            if quorum_achieved:
                payments_processed_total.labels(
                    node_id=settings.NODE_ID,
                    status="success" if success else "failure"
                ).inc()
                logger.info(f"Payment {payment.id} strictly finalized via webhook consensus. Status: {final_status}")
            else:
                payments_failed_total.labels(
                    node_id=settings.NODE_ID, reason="quorum_failure"
                ).inc()
                raise Exception("Failed to achieve Raft quorum for payment finalization.")
        finally:
            # Always decrement pending count when finalization attempt concludes
            payments_pending.labels(node_id=settings.NODE_ID).dec()
