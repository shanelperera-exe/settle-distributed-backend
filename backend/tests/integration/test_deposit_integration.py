import pytest
from sqlalchemy.orm import Session
from app.modules.deposits.services import DepositService
from app.modules.wallets.services import WalletService
from app.financial.ledger.models import LedgerEntry, TransactionType, LedgerStatus
from app.modules.payments.applier import _apply_sync
from decimal import Decimal
import uuid
import stripe
from app.modules.deposits.models import Deposit, DepositStatus

@pytest.mark.asyncio
async def test_webhook_finalizes_deposit(db: Session, monkeypatch):
    """
    Integration test: Simulates the webhook trigger to finalize a pending deposit via Raft.
    """
    deposit_service = DepositService(db)
    wallet_service = WalletService(db)
    
    wallet = wallet_service.create_wallet(f"usr_{uuid.uuid4().hex}")

    # Seed pending deposit
    deposit = Deposit(
        wallet_id=wallet.id,
        amount=Decimal("250.00"),
        currency="USD",
        status=DepositStatus.PENDING,
        stripe_payment_intent_id=f"pi_mock_{uuid.uuid4().hex}"
    )
    db.add(deposit)
    db.commit()

    # Mock SessionLocal for the background applier
    import contextlib
    @contextlib.contextmanager
    def mock_session():
        yield db
    monkeypatch.setattr("app.modules.payments.applier.SessionLocal", mock_session)
    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)


    # Intercept Raft submission and apply synchronously
    async def mock_submit(self, cmd, *args, **kwargs):
        _apply_sync(cmd)
        return True
    monkeypatch.setattr("app.platform.distributed.raft.node.RaftNode.submit_command", mock_submit)

    # Process finalization (simulating webhook calling finalize_deposit)
    await deposit_service.finalize_deposit(deposit.id)

    # Verify wallet balance
    balance = wallet_service.get_wallet_balance(wallet.id)
    assert balance["available_balance"] == Decimal("250.00")

    # Verify Ledger
    entries = db.query(LedgerEntry).filter(LedgerEntry.credit_account_id == wallet.id).all()
    assert len(entries) == 1
    assert entries[0].transaction_type == TransactionType.DEPOSIT
    assert entries[0].status == LedgerStatus.COMMITTED
    assert entries[0].debit_account_id == "sys_stripe_clearing"
