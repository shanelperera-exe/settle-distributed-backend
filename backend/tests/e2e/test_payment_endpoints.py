import pytest
from app.platform.core.config import settings

@pytest.mark.asyncio
async def test_create_and_get_payment(async_client, monkeypatch):
    headers = {
        "Authorization": f"Bearer {settings.API_KEY}",
        "Idempotency-Key": "test-e2e-pay-1"
    }
    
    payload = {
        "amount": 10.50,
        "currency": "USD",
        "sender_id": "alice",
        "receiver_id": "bob"
    }
    
    # Mock leader check
    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)
    
    # Mock stripe intent
    class MockIntent:
        id = "pi_mock_123"
        client_secret = "secret_mock_123"
        
    def mock_stripe(*args, **kwargs):
        return MockIntent()
        
    monkeypatch.setattr("app.platform.integrations.stripe_service.stripe_service.create_payment_intent", mock_stripe)
    
    # Mock raft submission
    async def mock_initiate(*args, **kwargs):
        from app.modules.payments.models import Payment, PaymentStatus
        return Payment(id="pay_mock_123", transaction_id="txn_123", status=PaymentStatus.PENDING)
        
    monkeypatch.setattr("app.modules.payments.services.PaymentService.initiate_payment", mock_initiate)

    resp = await async_client.post("/api/v1/payments/", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["payment_id"] == "pay_mock_123"
    assert data["client_secret"] == "secret_mock_123"

@pytest.mark.asyncio
async def test_get_payments_unauthorized(async_client):
    resp = await async_client.get("/api/v1/payments/")
    assert resp.status_code == 401
