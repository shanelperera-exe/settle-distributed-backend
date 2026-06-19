import pytest
from decimal import Decimal
from app.modules.payments.services import PaymentService
from app.contracts.payment import PaymentCreate
from app.modules.payments.models import PaymentStatus
from app.financial.ledger.models import LedgerEntry

@pytest.mark.asyncio
async def test_initiate_payment(db, monkeypatch):
    service = PaymentService(db)
    payment_in = PaymentCreate(
        amount=100.00,
        currency="USD",
        sender_id="alice",
        receiver_id="bob"
    )
    
    # Mock leader check
    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.ensure_leader", lambda: None)
    
    # Mock submit_command to avoid actually waiting for Raft
    async def mock_submit(*args, **kwargs):
        return True
    monkeypatch.setattr("app.platform.distributed.raft.node.RaftNode.submit_command", mock_submit)
    
    payment = await service.initiate_payment(payment_in, "key-test-1", "pi_test_123")
    
    assert payment.amount == Decimal("100.00")
    assert payment.status == PaymentStatus.PENDING
    assert payment.stripe_payment_intent_id == "pi_test_123"

@pytest.mark.asyncio
async def test_apply_payment_success(db, monkeypatch):
    from app.modules.payments.applier import _apply_sync
    import contextlib
    
    @contextlib.contextmanager
    def mock_session():
        yield db
        
    monkeypatch.setattr("app.modules.payments.applier.SessionLocal", mock_session)
    
    command = {
        "type": "PAYMENT_INIT",
        "payment": {
            "id": "pay_test_456",
            "transaction_id": "txn_test_456",
            "stripe_payment_intent_id": "pi_test_456",
            "idempotency_key": "key-test-2",
            "amount": 50.00,
            "currency": "USD",
            "sender_id": "charlie",
            "receiver_id": "dave",
            "status": "PENDING",
            "originating_node_id": "node-1",
            "processing_node_id": "node-1",
            "committed": True,
            "replicated": True
        }
    }
    
    _apply_sync(command)
    
    # Check DB
    from app.modules.payments.models import Payment
    payment = db.query(Payment).filter(Payment.id == "pay_test_456").first()
    assert payment is not None
    assert payment.status == PaymentStatus.PENDING
