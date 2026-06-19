import pytest
import asyncio
from sqlalchemy.orm import Session
from app.modules.transfers.services import TransferService
from app.modules.wallets.services import WalletService
from app.financial.ledger.models import LedgerEntry, TransactionType, LedgerStatus
from app.modules.payments.applier import _apply_sync
from fastapi import HTTPException
from decimal import Decimal
import uuid

@pytest.mark.asyncio
async def test_mass_concurrent_transfers(db: Session, monkeypatch):
    """
    Stress Test: Simulates 50 concurrent requests trying to transfer 1 USD
    out of a wallet that only has 10 USD. Verifies that exactly 10 succeed
    and 40 fail, proving ACID-like transaction boundaries and no double spending.
    """
    wallet_service = WalletService(db)
    
    sender_wallet = wallet_service.create_wallet(f"usr_{uuid.uuid4().hex}")
    receiver_wallet = wallet_service.create_wallet(f"usr_{uuid.uuid4().hex}")

    # Give sender exactly 10 USD
    db.add(LedgerEntry(
        id=f"led_{uuid.uuid4().hex}",
        transaction_id="txn_init",
        debit_account_id="sys_clearing",
        credit_account_id=sender_wallet.id,
        amount=10.0,
        currency="USD",
        transaction_type=TransactionType.DEPOSIT,
        status=LedgerStatus.COMMITTED
    ))
    db.commit()

    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)

    # Mock SessionLocal for the background applier
    import contextlib
    @contextlib.contextmanager
    def mock_session():
        yield db
    monkeypatch.setattr("app.modules.payments.applier.SessionLocal", mock_session)

    # We need a locking mechanism because SQLite in memory might complain about concurrent writes
    # But in reality, Raft serializes the state machine.
    # To mimic Raft's serial execution of state machine applier:
    apply_lock = asyncio.Lock()
    
    async def mock_submit(self, cmd, *args, **kwargs):
        async with apply_lock:
            _apply_sync(cmd)
        return True
    
    monkeypatch.setattr("app.platform.distributed.raft.node.RaftNode.submit_command", mock_submit)

    transfer_service = TransferService(db)

    async def attempt_transfer():
        try:
            await transfer_service.initiate_transfer(
                sender_wallet_id=sender_wallet.id,
                receiver_wallet_id=receiver_wallet.id,
                amount=Decimal("1.00")
            )
            return True
        except HTTPException as e:
            if "Insufficient funds" in e.detail:
                return False
            raise e

    # Launch 50 concurrent transfer attempts
    tasks = [attempt_transfer() for _ in range(50)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successes = sum(1 for r in results if r is True)
    failures = sum(1 for r in results if r is False)
    
    # Exceptions that are not caught (if any)
    errors = [r for r in results if isinstance(r, Exception)]
    assert len(errors) == 0

    assert successes == 10
    assert failures == 40

    # Verify Balances
    assert wallet_service.get_wallet_balance(sender_wallet.id)["available_balance"] == Decimal("0.00")
    assert wallet_service.get_wallet_balance(receiver_wallet.id)["available_balance"] == Decimal("10.00")
