import pytest
from httpx import AsyncClient
from app.financial.ledger.models import LedgerEntry, TransactionType, LedgerStatus
from sqlalchemy.orm import Session
import uuid

@pytest.fixture
async def users_and_wallets(async_client: AsyncClient, db: Session):
    # User 1 (Sender)
    await async_client.post("/api/v1/auth/register", json={"email": "sender@example.com", "password": "password", "full_name": "Sender"})
    res1 = await async_client.post("/api/v1/auth/login", data={"username": "sender@example.com", "password": "password"})
    token1 = res1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}
    
    wallet_res1 = await async_client.post("/api/v1/wallets/?currency=USD", headers=headers1)
    sender_wallet_id = wallet_res1.json()["id"]

    # User 2 (Receiver)
    await async_client.post("/api/v1/auth/register", json={"email": "receiver@example.com", "password": "password", "full_name": "Receiver"})
    res2 = await async_client.post("/api/v1/auth/login", data={"username": "receiver@example.com", "password": "password"})
    token2 = res2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    wallet_res2 = await async_client.post("/api/v1/wallets/?currency=USD", headers=headers2)
    receiver_wallet_id = wallet_res2.json()["id"]

    # Give sender 500 USD
    db.add(LedgerEntry(
        id=f"led_{uuid.uuid4().hex}",
        transaction_id="txn_init",
        debit_account_id="sys_stripe_clearing",
        credit_account_id=sender_wallet_id,
        amount=500.0,
        currency="USD",
        transaction_type=TransactionType.DEPOSIT,
        status=LedgerStatus.COMMITTED
    ))
    db.commit()

    return headers1, sender_wallet_id, headers2, receiver_wallet_id

@pytest.mark.asyncio
async def test_transfer_success(async_client: AsyncClient, users_and_wallets, monkeypatch, db: Session):
    headers1, sender_wallet_id, headers2, receiver_wallet_id = users_and_wallets

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

    payload = {
        "receiver_wallet_id": receiver_wallet_id,
        "amount": 100.0,
        "currency": "USD"
    }

    # Send transfer
    response = await async_client.post(f"/api/v1/transfers/?sender_wallet_id={sender_wallet_id}", json=payload, headers=headers1)
    assert response.status_code == 201
    transfer = response.json()
    assert float(transfer["amount"]) == 100.0
    assert transfer["sender_wallet_id"] == sender_wallet_id
    assert transfer["status"] == "COMPLETED"

    # Check sender balance (500 - 100 = 400)
    bal_res1 = await async_client.get(f"/api/v1/wallets/{sender_wallet_id}/balance", headers=headers1)
    assert bal_res1.json()["available_balance"] == 400.0

    # Check receiver balance (0 + 100 = 100)
    bal_res2 = await async_client.get(f"/api/v1/wallets/{receiver_wallet_id}/balance", headers=headers2)
    assert bal_res2.json()["available_balance"] == 100.0

@pytest.mark.asyncio
async def test_transfer_insufficient_funds(async_client: AsyncClient, users_and_wallets, monkeypatch, db: Session):
    headers1, sender_wallet_id, _, receiver_wallet_id = users_and_wallets

    import contextlib
    @contextlib.contextmanager
    def mock_session():
        yield db
    monkeypatch.setattr("app.modules.payments.applier.SessionLocal", mock_session)
    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)

    payload = {
        "receiver_wallet_id": receiver_wallet_id,
        "amount": 9999.0, # More than 500
        "currency": "USD"
    }

    response = await async_client.post(f"/api/v1/transfers/?sender_wallet_id={sender_wallet_id}", json=payload, headers=headers1)
    assert response.status_code == 400
    assert "Insufficient funds" in response.json()["detail"]
