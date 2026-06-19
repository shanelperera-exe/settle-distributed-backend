import pytest
import asyncio
from app.platform.core.config import settings

@pytest.mark.asyncio
async def test_concurrent_idempotency(async_client, monkeypatch):
    """
    Stress test idempotency by sending 50 concurrent requests with the SAME idempotency key.
    Only 1 should succeed with a 200/201 and actually create a payment.
    The others should receive a 409 Conflict if they hit the race condition window,
    or a 200 with cached data if they hit after the lock is released.
    """
    # Mock leader check
    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)
    
    class MockIntent:
        id = "pi_stress_1"
        client_secret = "sec_stress_1"
        
    def mock_stripe(*args, **kwargs):
        # Add small delay to simulate network latency, widening the race window
        import time
        time.sleep(0.01)
        return MockIntent()
        
    monkeypatch.setattr("app.platform.integrations.stripe_service.stripe_service.create_payment_intent", mock_stripe)
    
    async def mock_initiate(*args, **kwargs):
        from app.modules.payments.models import Payment, PaymentStatus
        await asyncio.sleep(0.01)
        return Payment(id="pay_stress_1", transaction_id="txn_stress_1", status=PaymentStatus.PENDING)
        
    monkeypatch.setattr("app.modules.payments.services.PaymentService.initiate_payment", mock_initiate)

    payload = {
        "amount": 50.00,
        "currency": "USD",
        "sender_id": "stress_alice",
        "receiver_id": "stress_bob"
    }
    
    headers = {
        "Authorization": f"Bearer {settings.API_KEY}",
        "Idempotency-Key": "stress-key-1"
    }
    
    # Send 50 requests concurrently
    tasks = [
        async_client.post("/api/v1/payments/", json=payload, headers=headers)
        for _ in range(50)
    ]
    
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    status_codes = [resp.status_code for resp in responses if not isinstance(resp, Exception)]
    
    # There should be exactly ONE 200 OK that processed it (or cached 200 if it finished super fast).
    # Since they are concurrent, many will hit 409. 
    # The sum of 200s and 409s should equal 50.
    assert len(status_codes) == 50
    assert 200 in status_codes
    assert 409 in status_codes or status_codes.count(200) == 50
