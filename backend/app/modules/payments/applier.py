import asyncio
import logging
from decimal import Decimal

from app.platform.infrastructure.db.session import SessionLocal
from app.modules.payments.models import Payment, PaymentStatus
from app.financial.ledger.models import LedgerEntry, LedgerStatus
from app.modules.transfers.models import Transfer, TransferStatus
from app.modules.deposits.models import Deposit, DepositStatus
from app.modules.withdrawals.models import Withdrawal, WithdrawalStatus
from app.modules.wallets.models import Wallet
from app.platform.core.websockets import manager

logger = logging.getLogger(__name__)


def _notify_ws(user_id: str, message: dict):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(manager.send_personal_message(message, user_id))
    except RuntimeError:
        # If no running loop, create a new one (unlikely but safe fallback)
        asyncio.run(manager.send_personal_message(message, user_id))


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
                
                # WS Notification
                if payment:
                    wallet = db.query(Wallet).filter(Wallet.id == payment.sender_id).first()
                    if wallet:
                        _notify_ws(wallet.user_id, {
                            "type": "PAYMENT_UPDATE",
                            "payment_id": p_id,
                            "status": status.value
                        })

            elif command_type == "TRANSFER":
                t_data = command["transfer"]
                e_data = command["ledger_entry"]

                # Idempotent: skip if transfer already exists
                existing_transfer = db.query(Transfer).filter(Transfer.id == t_data["id"]).first()
                if existing_transfer:
                    logger.info(f"Raft Applier: TRANSFER {t_data['id']} already exists — skipping.")
                    return

                transfer = Transfer(
                    id=t_data["id"],
                    sender_wallet_id=t_data["sender_wallet_id"],
                    receiver_wallet_id=t_data["receiver_wallet_id"],
                    amount=Decimal(str(t_data["amount"])),
                    currency=t_data["currency"],
                    status=TransferStatus(t_data["status"]),
                )
                db.add(transfer)

                existing_entry = db.query(LedgerEntry).filter(LedgerEntry.id == e_data["id"]).first()
                if not existing_entry:
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
                logger.info(f"Raft Applier: Committed TRANSFER {transfer.id}")
                
                # WS Notifications
                sender_wallet = db.query(Wallet).filter(Wallet.id == transfer.sender_wallet_id).first()
                receiver_wallet = db.query(Wallet).filter(Wallet.id == transfer.receiver_wallet_id).first()
                
                if sender_wallet:
                    _notify_ws(sender_wallet.user_id, {
                        "type": "TRANSFER_SENT",
                        "transfer_id": transfer.id,
                        "amount": float(transfer.amount),
                        "currency": transfer.currency
                    })
                if receiver_wallet:
                    _notify_ws(receiver_wallet.user_id, {
                        "type": "TRANSFER_RECEIVED",
                        "transfer_id": transfer.id,
                        "amount": float(transfer.amount),
                        "currency": transfer.currency
                    })

            elif command_type == "DEPOSIT":
                d_data = command["deposit"]
                e_data = command["ledger_entry"]

                deposit = db.query(Deposit).filter(Deposit.id == d_data["id"]).first()
                if deposit:
                    # Update status if it exists
                    deposit.status = DepositStatus(d_data["status"])
                else:
                    deposit = Deposit(
                        id=d_data["id"],
                        wallet_id=d_data["wallet_id"],
                        amount=Decimal(str(d_data["amount"])),
                        currency=d_data["currency"],
                        stripe_payment_intent_id=d_data.get("stripe_payment_intent_id"),
                        status=DepositStatus(d_data["status"])
                    )
                    db.add(deposit)

                existing_entry = db.query(LedgerEntry).filter(LedgerEntry.id == e_data["id"]).first()
                if not existing_entry:
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
                logger.info(f"Raft Applier: Committed DEPOSIT {deposit.id}")
                
                # WS Notification
                wallet = db.query(Wallet).filter(Wallet.id == deposit.wallet_id).first()
                if wallet:
                    _notify_ws(wallet.user_id, {
                        "type": "DEPOSIT_UPDATE",
                        "deposit_id": deposit.id,
                        "status": deposit.status.value,
                        "amount": float(deposit.amount)
                    })

            elif command_type == "WITHDRAWAL":
                w_data = command["withdrawal"]
                e_data = command["ledger_entry"]

                # Idempotent: skip if withdrawal already exists
                existing_w = db.query(Withdrawal).filter(Withdrawal.id == w_data["id"]).first()
                if existing_w:
                    logger.info(f"Raft Applier: WITHDRAWAL {w_data['id']} already exists — skipping.")
                    return

                withdrawal = Withdrawal(
                    id=w_data["id"],
                    wallet_id=w_data["wallet_id"],
                    amount=Decimal(str(w_data["amount"])),
                    currency=w_data["currency"],
                    status=WithdrawalStatus(w_data["status"]),
                )
                db.add(withdrawal)

                existing_entry = db.query(LedgerEntry).filter(LedgerEntry.id == e_data["id"]).first()
                if not existing_entry:
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
                logger.info(f"Raft Applier: Committed WITHDRAWAL {withdrawal.id}")


            elif command_type == "WITHDRAWAL_UPDATE":
                w_id = command["withdrawal_id"]
                status = WithdrawalStatus(command["status"])
                stripe_payout_id = command.get("stripe_payout_id")
                e_data = command.get("ledger_entry") # Reversal entry if failed

                withdrawal = db.query(Withdrawal).filter(Withdrawal.id == w_id).first()
                if withdrawal:
                    withdrawal.status = status
                    if stripe_payout_id:
                        withdrawal.stripe_payout_id = stripe_payout_id

                if e_data:
                    existing_entry = db.query(LedgerEntry).filter(LedgerEntry.id == e_data["id"]).first()
                    if not existing_entry:
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
                logger.info(f"Raft Applier: Committed WITHDRAWAL_UPDATE for {w_id}")
                
                # WS Notification
                if withdrawal:
                    wallet = db.query(Wallet).filter(Wallet.id == withdrawal.wallet_id).first()
                    if wallet:
                        _notify_ws(wallet.user_id, {
                            "type": "WITHDRAWAL_UPDATE",
                            "withdrawal_id": withdrawal.id,
                            "status": withdrawal.status.value,
                            "amount": float(withdrawal.amount)
                        })

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
