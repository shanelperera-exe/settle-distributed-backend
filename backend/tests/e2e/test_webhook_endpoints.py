import pytest
import time
import json
import stripe
from app.modules.payments.models import Payment, PaymentStatus
from app.financial.ledger.models import LedgerEntry

@pytest.mark.asyncio
async def test_stripe_webhook_success(async_client, db, monkeypatch):
    """
    Simulate a successful Stripe webhook via the API endpoint.
    """
    # 1. Setup a dummy payment in the database to be finalized
    from app.modules.payments.applier import _apply_sync
    import contextlib
    
    @contextlib.contextmanager
    def mock_session():
        yield db
        
    monkeypatch.setattr("app.modules.payments.applier.SessionLocal", mock_session)
    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.ensure_leader", lambda: None)
    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)
    
    # Mock submit_command to process the internal webhook command
    async def mock_submit(self, cmd, *args, **kwargs):
        _apply_sync(cmd)
        return True
    monkeypatch.setattr("app.platform.distributed.raft.node.RaftNode.submit_command", mock_submit)
    
    # Create the pending payment directly via DB fixture
    payment = Payment(
        id="pay_webhook_test_1",
        transaction_id="txn_webhook_test_1",
        stripe_payment_intent_id="pi_webhook_test_1",
        amount=100.0,
        currency="USD",
        sender_id="alice",
        receiver_id="bob",
        status=PaymentStatus.PENDING,
        originating_node_id="node-1",
        replicated=True,
        committed=True
    )
    db.add(payment)
    db.commit()
    
    # 2. Mock Stripe signature validation to return our event
    class MockEvent:
        type = "payment_intent.succeeded"
        class data:
            class object:
                id = "pi_webhook_test_1"
                metadata = {}
                
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, sig, secret: MockEvent())
    
    # 3. Send Webhook
    payload = json.dumps({"id": "evt_test", "type": "payment_intent.succeeded"})
    headers = {"Stripe-Signature": "t=123,v1=mock_signature"}
    
    response = await async_client.post("/api/v1/webhooks/stripe", content=payload, headers=headers)
    assert response.status_code == 200
    
    # 4. Verify Payment Status and Ledger Entries
    db.refresh(payment)
    assert payment.status == PaymentStatus.COMPLETED
    
    ledger_entries = db.query(LedgerEntry).filter(LedgerEntry.transaction_id == payment.transaction_id).all()
    assert len(ledger_entries) == 1
    assert ledger_entries[0].debit_account_id == "alice"
    assert ledger_entries[0].credit_account_id == "bob"

@pytest.mark.asyncio
async def test_stripe_webhook_invalid_signature(async_client, monkeypatch):
    """
    Ensure webhooks with invalid signatures are strictly rejected.
    """
    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)
    
    def raise_signature_error(*args, **kwargs):
        raise stripe.error.SignatureVerificationError("Invalid signature", "sig", "payload")
        
    monkeypatch.setattr(stripe.Webhook, "construct_event", raise_signature_error)
    
    payload = json.dumps({"id": "evt_test", "type": "payment_intent.succeeded"})
    headers = {"Stripe-Signature": "t=123,v1=bad_signature"}
    
    response = await async_client.post("/api/v1/webhooks/stripe", content=payload, headers=headers)
    assert response.status_code == 400
