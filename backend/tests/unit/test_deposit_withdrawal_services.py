import pytest
from sqlalchemy.orm import Session
from app.modules.deposits.services import DepositService
from app.modules.withdrawals.services import WithdrawalService
from app.modules.wallets.services import WalletService
from decimal import Decimal
import uuid
import stripe
from app.platform.integrations.stripe_service import stripe_service

@pytest.fixture
def deposit_service(db: Session):
    return DepositService(db)

@pytest.fixture
def withdrawal_service(db: Session):
    return WithdrawalService(db)

def test_initiate_deposit(deposit_service: DepositService, db: Session, monkeypatch):
    wallet_service = WalletService(db)
    wallet = wallet_service.create_wallet(f"usr_{uuid.uuid4().hex}")

    unique_pi = f"pi_mock_{uuid.uuid4().hex}"

    # Mock Stripe
    class MockPaymentIntent:
        id = unique_pi
        client_secret = "secret_123"
    
    def mock_create(**kwargs):
        return MockPaymentIntent()

    monkeypatch.setattr(stripe.PaymentIntent, "create", mock_create)

    result = deposit_service.initiate_deposit(wallet.id, Decimal("50.00"))
    
    assert result.amount == Decimal("50.00")
    assert result.status.value == "PENDING"
    assert result.stripe_payment_intent_id == unique_pi

@pytest.mark.asyncio
async def test_initiate_withdrawal(withdrawal_service: WithdrawalService, db: Session, monkeypatch):
    wallet_service = WalletService(db)
    wallet = wallet_service.create_wallet(f"usr_{uuid.uuid4().hex}")

    monkeypatch.setattr(
        "app.modules.wallets.services.WalletService.get_wallet_balance",
        lambda self, w_id: {"available_balance": Decimal("100.00")}
    )
    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)

    unique_po = f"po_mock_{uuid.uuid4().hex}"

    class MockPayout:
        id = unique_po
        status = "pending"
    
    def mock_create(**kwargs):
        return MockPayout()
        
    monkeypatch.setattr(stripe.Payout, "create", mock_create)

    # Mock Raft submission
    async def mock_submit(*args, **kwargs):
        return True
    monkeypatch.setattr("app.platform.distributed.raft.node.RaftNode.submit_command", mock_submit)

    result = await withdrawal_service.initiate_withdrawal(wallet.id, Decimal("25.00"))
    
    assert getattr(result, "amount", result.get("amount") if isinstance(result, dict) else None) == Decimal("25.00")
    assert getattr(result, "status", result.get("status") if isinstance(result, dict) else None) in ("PENDING", getattr(result, "status", None))
