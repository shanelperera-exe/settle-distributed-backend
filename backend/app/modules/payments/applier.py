import asyncio
import logging
from decimal import Decimal

from app.platform.infrastructure.db.session import SessionLocal
from app.modules.payments.models import Payment, PaymentStatus
from app.financial.ledger.models import LedgerEntry, LedgerStatus

logger = logging.getLogger(__name__)

def _apply_sync(command: dict):
    """
    Synchronous DB write — runs in a thread pool via asyncio.to_thread().
    Keeping DB I/O off the event loop is critical: blocking the event loop
    starves the Raft heartbeat tasks, causing false election timeouts.
    """
    command_type = command.get("type")

    with SessionLocal() as db:
        try:
            if command_type == "PAYMENT_INIT":
                p_data = command["payment"]
                # Idempotent: skip if already exists (replayed log on restart).
                existing = db.query(Payment).filter(Payment.id == p_data["id"]).first()
                if existing:
                    logger.info(f"Raft Applier: PAYMENT_INIT {p_data['id']} already exists — skipping.")
                    return
                payment = Payment(
                    id=p_data["id"],
                    transaction_id=p_data["transaction_id"],
                    stripe_payment_intent_id=p_data["stripe_payment_intent_id"],
                    idempotency_key=p_data["idempotency_key"],
                    amount=Decimal(str(p_data["amount"])),
                    currency=p_data["currency"],
                    sender_id=p_data["sender_id"],
                    receiver_id=p_data["receiver_id"],
                    payment_method=p_data.get("payment_method"),
                    status=PaymentStatus(p_data["status"]),
                    originating_node_id=p_data["originating_node_id"],
                    processing_node_id=p_data["processing_node_id"],
                    committed=True,
                    replicated=True,
                )
                db.add(payment)
                db.commit()
                logger.info(f"Raft Applier: Committed PAYMENT_INIT for {payment.id}")

            elif command_type == "PAYMENT_FINALIZE":
                p_id = command["payment_id"]
                status = PaymentStatus(command["status"])
                entries = command["ledger_entries"]

                payment = db.query(Payment).filter(Payment.id == p_id).first()
                if payment:
                    payment.status = status

                for e_data in entries:
                    existing = db.query(LedgerEntry).filter(LedgerEntry.id == e_data["id"]).first()
                    if not existing:
                        entry = LedgerEntry(
                            id=e_data["id"],
                            transaction_id=e_data["transaction_id"],
                            leader_node=e_data.get("leader_node"),
                            debit_account_id=e_data["debit_account_id"],
                            credit_account_id=e_data["credit_account_id"],
                            transaction_type=e_data["transaction_type"],
                            amount=Decimal(str(e_data["amount"])),
                            currency=e_data["currency"],
                            status=LedgerStatus(e_data["status"]),
                            committed=True,
                            replicated=True,
                        )
                        db.add(entry)

                db.commit()
                logger.info(f"Raft Applier: Committed PAYMENT_FINALIZE {p_id}")

        except Exception as e:
            db.rollback()
            logger.error(f"Raft Applier Error: {e}", exc_info=True)
            raise


async def raft_apply_callback(command: dict):
    """
    Called by the Raft Node's applier_loop whenever a log entry is committed.
    Offloads synchronous DB work to a thread pool to keep the asyncio event loop free.
    This is essential: blocking the event loop starves the Raft heartbeat tasks.
    """
    await asyncio.to_thread(_apply_sync, command)
