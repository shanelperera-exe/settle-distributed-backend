import pytest
from sqlalchemy.orm import Session
from app.modules.transfers.services import TransferService
from app.modules.wallets.services import WalletService
from app.financial.ledger.models import LedgerEntry, TransactionType, LedgerStatus
from app.modules.payments.applier import _apply_sync
from decimal import Decimal
import uuid

@pytest.mark.asyncio
async def test_transfer_commits_to_ledger(db: Session, monkeypatch):
    """
    Integration test: Initiates a transfer, intercepts the Raft submission,
    directly feeds it into _apply_sync (simulating Raft apply), and verifies
    the database accurately reflects the committed ledger entry.
    """
    transfer_service = TransferService(db)
    wallet_service = WalletService(db)
    
    sender_wallet = wallet_service.create_wallet(f"usr_{uuid.uuid4().hex}")
    receiver_wallet = wallet_service.create_wallet(f"usr_{uuid.uuid4().hex}")

    # Give sender initial funds
    db.add(LedgerEntry(
        id=f"led_{uuid.uuid4().hex}",
        transaction_id="txn_init",
        debit_account_id="sys_clearing",
        credit_account_id=sender_wallet.id,
        amount=100.0,
        currency="USD",
        transaction_type=TransactionType.DEPOSIT,
        status=LedgerStatus.COMMITTED
    ))
    db.commit()

    # Mock Failover (we must be leader to initiate)
    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)

    # Mock SessionLocal for the background applier
    import contextlib
    @contextlib.contextmanager
    def mock_session():
        yield db
    monkeypatch.setattr("app.modules.payments.applier.SessionLocal", mock_session)

    # Intercept Raft submission and apply synchronously
    async def mock_submit(self, cmd, *args, **kwargs):
        _apply_sync(cmd)
        return True
    monkeypatch.setattr("app.platform.distributed.raft.node.RaftNode.submit_command", mock_submit)

    transfer = await transfer_service.initiate_transfer(
        sender_wallet_id=sender_wallet.id,
        receiver_wallet_id=receiver_wallet.id,
        amount=Decimal("40.00")
    )

    assert transfer["status"] == "COMPLETED"

    # Verify balances via WalletService
    assert wallet_service.get_wallet_balance(sender_wallet.id)["available_balance"] == Decimal("60.00")
    assert wallet_service.get_wallet_balance(receiver_wallet.id)["available_balance"] == Decimal("40.00")

    # Verify LedgerEntry was physically committed
    entries = db.query(LedgerEntry).filter(LedgerEntry.transaction_id == transfer["id"]).all()
    assert len(entries) == 1
    assert entries[0].transaction_type == TransactionType.TRANSFER
    assert entries[0].amount == Decimal("40.00")
    assert entries[0].status == LedgerStatus.COMMITTED
    assert entries[0].debit_account_id == sender_wallet.id
    assert entries[0].credit_account_id == receiver_wallet.id
