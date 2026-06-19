from sqlalchemy.orm import Session
from fastapi import HTTPException
from decimal import Decimal
import uuid
import time
from app.modules.withdrawals.models import Withdrawal, WithdrawalStatus
from app.financial.ledger.models import LedgerEntry, TransactionType, LedgerStatus
from app.modules.wallets.services import WalletService
from app.platform.distributed.raft.node import raft_node
from app.platform.distributed.failover_service import FailoverService
from app.platform.core.config import settings
from app.platform.integrations.stripe_service import stripe_service
from app.platform.observability.logging import logger

class WithdrawalService:
    def __init__(self, db: Session):
        self.db = db
        self.wallet_service = WalletService(db)

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

    async def initiate_withdrawal(self, wallet_id: str, amount: Decimal, currency: str = "USD") -> Withdrawal:
        """
        Phase 1 of Saga: Create local pending withdrawal and lock funds via Raft.
        """
        FailoverService.ensure_leader()
        
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Withdrawal amount must be positive")

        # 1. Validate Balance
        balance_info = self.wallet_service.get_wallet_balance(wallet_id)
        if balance_info["available_balance"] < amount:
            raise HTTPException(status_code=400, detail="Insufficient funds for withdrawal")

        STRIPE_CLEARING_WALLET_ID = "sys_stripe_clearing"

        # 2. Prepare local model
        withdrawal = Withdrawal(
            wallet_id=wallet_id,
            amount=amount,
            currency=currency,
            status=WithdrawalStatus.PENDING
        )
        # We need an ID for idempotency before saving, since Raft applier does the save
        withdrawal.id = f"wdl_{uuid.uuid4().hex}"

        # 3. Prepare Double-Entry Ledger Command to lock the funds
        ledger_entry = LedgerEntry(
            id=f"led_{uuid.uuid4().hex}",
            transaction_id=withdrawal.id,
            leader_node=settings.NODE_ID,
            debit_account_id=wallet_id,
            credit_account_id=STRIPE_CLEARING_WALLET_ID,
            transaction_type=TransactionType.WITHDRAWAL,
            amount=amount,
            currency=currency,
            status=LedgerStatus.COMMITTED
        )

        command = {
            "type": "WITHDRAWAL",
            "withdrawal": self._to_dict(withdrawal),
            "ledger_entry": self._to_dict(ledger_entry)
        }

        # 4. Propose to Raft Log to deduct funds securely
        quorum_achieved = await raft_node.submit_command(command)
        
        if not quorum_achieved:
            raise Exception("Failed to achieve Raft quorum for withdrawal.")
            
        # 5. Call Stripe Payout API synchronously (Saga execution)
        try:
            payout = stripe_service.create_payout(
                amount=float(amount),
                currency=currency,
                idempotency_key=withdrawal.id,
                metadata={"withdrawal_id": withdrawal.id, "wallet_id": wallet_id}
            )
            
            # Since Stripe accepted it, we propose a status update to SUCCEEDED
            update_command = {
                "type": "WITHDRAWAL_UPDATE",
                "withdrawal_id": withdrawal.id,
                "status": WithdrawalStatus.SUCCEEDED.value,
                "stripe_payout_id": payout.id
            }
            await raft_node.submit_command(update_command)
            
            # Return updated object (approximated for response)
            withdrawal.status = WithdrawalStatus.SUCCEEDED
            withdrawal.stripe_payout_id = payout.id
            return withdrawal
            
        except Exception as e:
            logger.error(f"Stripe Payout failed for {withdrawal.id}: {e}")
            # Saga Compensation: Propose a reversal ledger entry to refund the user
            reversal_entry = LedgerEntry(
                id=f"led_{uuid.uuid4().hex}",
                transaction_id=withdrawal.id,
                leader_node=settings.NODE_ID,
                debit_account_id=STRIPE_CLEARING_WALLET_ID,
                credit_account_id=wallet_id,
                transaction_type=TransactionType.REFUND,
                amount=amount,
                currency=currency,
                status=LedgerStatus.COMMITTED
            )
            reversal_command = {
                "type": "WITHDRAWAL_UPDATE",
                "withdrawal_id": withdrawal.id,
                "status": WithdrawalStatus.FAILED.value,
                "ledger_entry": self._to_dict(reversal_entry) # Reversal
            }
            await raft_node.submit_command(reversal_command)
            raise HTTPException(status_code=500, detail=f"Payout failed: {str(e)}")

    def get_withdrawal(self, withdrawal_id: str) -> Withdrawal:
        return self.db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
