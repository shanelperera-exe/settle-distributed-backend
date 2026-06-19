import pytest
from httpx import AsyncClient
from app.financial.ledger.models import LedgerEntry, TransactionType, LedgerStatus
from sqlalchemy.orm import Session
import uuid
import stripe

@pytest.fixture
async def user_and_wallet(async_client: AsyncClient, db: Session):
    await async_client.post("/api/v1/auth/register", json={"email": "stripe@example.com", "password": "password", "full_name": "Stripe User"})
    res = await async_client.post("/api/v1/auth/login", data={"username": "stripe@example.com", "password": "password"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    wallet_res = await async_client.post("/api/v1/wallets/?currency=USD", headers=headers)
    wallet_id = wallet_res.json()["id"]

    return headers, wallet_id

@pytest.mark.asyncio
async def test_deposit_initiate(async_client: AsyncClient, user_and_wallet, monkeypatch):
    headers, wallet_id = user_and_wallet

    # Mock Stripe
    class MockPaymentIntent:
        id = "pi_mock_123"
        client_secret = "secret_123"
    
    monkeypatch.setattr(stripe.PaymentIntent, "create", lambda **kwargs: MockPaymentIntent())

    payload = {
        "wallet_id": wallet_id,
        "amount": 200.0,
        "currency": "USD"
    }

    response = await async_client.post("/api/v1/deposits/", json=payload, headers=headers)
    assert response.status_code == 201
    deposit = response.json()
    assert float(deposit["amount"]) == 200.0
    assert deposit["status"] == "PENDING"
    assert deposit["stripe_payment_intent_id"] == "pi_mock_123"

@pytest.mark.asyncio
async def test_withdrawal_initiate(async_client: AsyncClient, user_and_wallet, monkeypatch, db: Session):
    headers, wallet_id = user_and_wallet

    # Give wallet 500 USD
    db.add(LedgerEntry(
        id=f"led_{uuid.uuid4().hex}",
        transaction_id="txn_init",
        debit_account_id="sys_stripe_clearing",
        credit_account_id=wallet_id,
        amount=500.0,
        currency="USD",
        transaction_type=TransactionType.DEPOSIT,
        status=LedgerStatus.COMMITTED
    ))
    db.commit()

    import contextlib
    @contextlib.contextmanager
    def mock_session():
        yield db
    monkeypatch.setattr("app.modules.payments.applier.SessionLocal", mock_session)

    # Mock Raft submission to auto-apply sync
    from app.modules.payments.applier import _apply_sync
    async def mock_submit(self, cmd, *args, **kwargs):
        _apply_sync(cmd)
        return True
    monkeypatch.setattr("app.platform.distributed.raft.node.RaftNode.submit_command", mock_submit)
    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)

    # Mock Stripe Payout
    class MockPayout:
        id = "po_mock_123"
        status = "pending"
    monkeypatch.setattr(stripe.Payout, "create", lambda **kwargs: MockPayout())

    payload = {
        "wallet_id": wallet_id,
        "amount": 100.0,
        "currency": "USD"
    }

    response = await async_client.post("/api/v1/withdrawals/", json=payload, headers=headers)
    assert response.status_code == 201
    withdrawal = response.json()
    assert float(withdrawal["amount"]) == 100.0
    assert withdrawal["status"] in ["PENDING", "SUCCEEDED", "COMPLETED"]
    assert withdrawal["stripe_payout_id"] == "po_mock_123"

    # Check sender balance (500 - 100 = 400)
    bal_res = await async_client.get(f"/api/v1/wallets/{wallet_id}/balance", headers=headers)
    assert bal_res.json()["available_balance"] == 400.0
