from sqlalchemy.orm import Session
from fastapi import HTTPException
from decimal import Decimal
import uuid
from app.modules.deposits.models import Deposit, DepositStatus
from app.financial.ledger.models import LedgerEntry, TransactionType, LedgerStatus
from app.platform.distributed.raft.node import raft_node
from app.platform.distributed.failover_service import FailoverService
from app.platform.core.config import settings
from app.platform.integrations.stripe_service import stripe_service

class DepositService:
    def __init__(self, db: Session):
        self.db = db

    def _to_dict(self, obj):
        from decimal import Decimal
        from datetime import datetime
        d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        for k, v in d.items():
            if isinstance(v, Decimal):
                d[k] = float(v)
            elif hasattr(v, 'value'):
                d[k] = v.value
            elif isinstance(v, datetime):
                d[k] = v.isoformat()
        return d

    def initiate_deposit(self, wallet_id: str, amount: Decimal, currency: str = "USD") -> Deposit:
        """
        Phase 1 of Saga: Create local pending deposit and call Stripe.
        """
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Deposit amount must be positive")

        # Create the local Pending Deposit record
        deposit = Deposit(
            wallet_id=wallet_id,
            amount=amount,
            currency=currency,
            status=DepositStatus.PENDING
        )
        self.db.add(deposit)
        self.db.commit()
        self.db.refresh(deposit)

        # Call Stripe API
        try:
            intent = stripe_service.create_payment_intent(
                amount=float(amount),
                currency=currency,
                idempotency_key=deposit.id,
                metadata={"deposit_id": deposit.id, "wallet_id": wallet_id}
            )
            deposit.stripe_payment_intent_id = intent.id
            self.db.commit()
            self.db.refresh(deposit)
            return deposit
        except Exception as e:
            deposit.status = DepositStatus.FAILED
            self.db.commit()
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    async def finalize_deposit(self, deposit_id: str):
        """
        Phase 2 of Saga: Triggered by Webhook. Propose the Raft double-entry Ledger command.
        DEBIT: STRIPE_CLEARING_ACCOUNT
        CREDIT: user_wallet
        """
        FailoverService.ensure_leader()
        
        deposit = self.db.query(Deposit).filter(Deposit.id == deposit_id).first()
        if not deposit:
            raise ValueError(f"Deposit {deposit_id} not found")
            
        if deposit.status == DepositStatus.SUCCEEDED:
            return # Idempotent: already succeeded

        STRIPE_CLEARING_WALLET_ID = "sys_stripe_clearing"

        ledger_entry = LedgerEntry(
            id=f"led_{uuid.uuid4().hex}",
            transaction_id=deposit.id,
            leader_node=settings.NODE_ID,
            debit_account_id=STRIPE_CLEARING_WALLET_ID,
            credit_account_id=deposit.wallet_id,
            transaction_type=TransactionType.DEPOSIT,
            amount=deposit.amount,
            currency=deposit.currency,
            status=LedgerStatus.COMMITTED
        )
        
        deposit_dict = self._to_dict(deposit)
        deposit_dict["status"] = DepositStatus.SUCCEEDED.value

        command = {
            "type": "DEPOSIT",
            "deposit": deposit_dict,
            "ledger_entry": self._to_dict(ledger_entry)
        }

        quorum_achieved = await raft_node.submit_command(command)
        
        if not quorum_achieved:
            raise Exception("Failed to achieve Raft quorum for deposit finalization.")
            
    def mark_failed(self, deposit_id: str):
        deposit = self.db.query(Deposit).filter(Deposit.id == deposit_id).first()
        if deposit:
            deposit.status = DepositStatus.FAILED
            self.db.commit()
