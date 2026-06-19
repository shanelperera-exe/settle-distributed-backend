from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from decimal import Decimal
import uuid
import time
from app.modules.transfers.models import Transfer, TransferStatus
from app.financial.ledger.models import LedgerEntry, TransactionType, LedgerStatus
from app.modules.wallets.services import WalletService
from app.platform.distributed.raft.node import raft_node
from app.platform.distributed.failover_service import FailoverService
from app.platform.core.config import settings

class TransferService:
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

    async def initiate_transfer(self, sender_wallet_id: str, receiver_wallet_id: str, amount: Decimal, currency: str = "USD") -> Transfer:
        FailoverService.ensure_leader()
        
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Transfer amount must be positive")
        
        if sender_wallet_id == receiver_wallet_id:
            raise HTTPException(status_code=400, detail="Cannot transfer to the same wallet")

        # 1. Validate Sender Balance
        sender_balance_info = self.wallet_service.get_wallet_balance(sender_wallet_id)
        if sender_balance_info["available_balance"] < amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        # 2. Prepare Local Model Representation
        from app.platform.core.utils.ids import generate_id
        transfer = Transfer(
            id=generate_id("trf"),
            sender_wallet_id=sender_wallet_id,
            receiver_wallet_id=receiver_wallet_id,
            amount=Decimal(str(amount)),
            currency=currency,
            status=TransferStatus.COMPLETED # Will be COMPLETED immediately upon Raft quorum
        )
        
        # 3. Prepare Double-Entry Ledger Command
        ledger_entry = LedgerEntry(
            id=f"led_{uuid.uuid4().hex}",
            transaction_id=transfer.id,
            leader_node=settings.NODE_ID,
            debit_account_id=sender_wallet_id,
            credit_account_id=receiver_wallet_id,
            transaction_type=TransactionType.TRANSFER,
            amount=amount,
            currency=currency,
            status=LedgerStatus.COMMITTED
        )

        # 4. Propose to Raft Log
        command = {
            "type": "TRANSFER",
            "transfer": self._to_dict(transfer),
            "ledger_entry": self._to_dict(ledger_entry)
        }

        # Wait for Majority Quorum Commit
        quorum_achieved = await raft_node.submit_command(command)
        
        if quorum_achieved:
            # Note: We return a dict since we do not add to db session here, avoiding detached instance issues.
            return {
                "id": transfer.id,
                "sender_wallet_id": sender_wallet_id,
                "receiver_wallet_id": receiver_wallet_id,
                "amount": transfer.amount,
                "currency": transfer.currency,
                "status": transfer.status.value if hasattr(transfer.status, "value") else transfer.status
            }
        else:
            raise Exception("Failed to achieve Raft quorum for transfer.")

    def get_transfer(self, transfer_id: str) -> Transfer:
        return self.db.query(Transfer).filter(Transfer.id == transfer_id).first()
