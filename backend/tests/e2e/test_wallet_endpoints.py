import pytest
from httpx import AsyncClient
from app.financial.ledger.models import LedgerEntry, TransactionType, LedgerStatus
from sqlalchemy.orm import Session
import uuid

@pytest.fixture
async def auth_headers(async_client: AsyncClient, db: Session):
    # Register & Login to get token
    payload = {
        "email": "walletuser@example.com",
        "password": "walletpassword123",
        "full_name": "Wallet User"
    }
    await async_client.post("/api/v1/auth/register", json=payload)
    login_data = {"username": "walletuser@example.com", "password": "walletpassword123"}
    login_response = await async_client.post("/api/v1/auth/login", data=login_data)
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_create_wallet_and_get(async_client: AsyncClient, auth_headers):
    # Create wallet
    response = await async_client.post("/api/v1/wallets/?currency=USD", headers=auth_headers)
    assert response.status_code == 201
    wallet = response.json()
    assert wallet["currency"] == "USD"
    assert wallet["status"] == "ACTIVE"
    wallet_id = wallet["id"]

    # Get my wallets
    response = await async_client.get("/api/v1/wallets/me", headers=auth_headers)
    assert response.status_code == 200
    wallets = response.json()
    assert len(wallets) >= 1
    assert any(w["id"] == wallet_id for w in wallets)

@pytest.mark.asyncio
async def test_get_wallet_balance(async_client: AsyncClient, auth_headers, db: Session):
    # Create wallet
    response = await async_client.post("/api/v1/wallets/?currency=USD", headers=auth_headers)
    wallet_id = response.json()["id"]

    # Check empty balance
    bal_response = await async_client.get(f"/api/v1/wallets/{wallet_id}/balance", headers=auth_headers)
    assert bal_response.status_code == 200
    data = bal_response.json()
    assert data["available_balance"] == 0.0
    assert data["pending_balance"] == 0.0

    # Insert mock ledger entries to simulate funds (double-entry: sys_clearing -> wallet)
    entry1 = LedgerEntry(
        id=f"led_{uuid.uuid4().hex}",
        transaction_id="txn_1",
        debit_account_id="sys_stripe_clearing",
        credit_account_id=wallet_id,
        amount=150.0,
        currency="USD",
        transaction_type=TransactionType.DEPOSIT,
        status=LedgerStatus.COMMITTED
    )
    entry2 = LedgerEntry(
        id=f"led_{uuid.uuid4().hex}",
        transaction_id="txn_2",
        debit_account_id=wallet_id,
        credit_account_id="sys_stripe_clearing",
        amount=50.0,
        currency="USD",
        transaction_type=TransactionType.WITHDRAWAL,
        status=LedgerStatus.COMMITTED
    )
    db.add(entry1)
    db.add(entry2)
    db.commit()

    # Check balance again (150 - 50 = 100)
    bal_response = await async_client.get(f"/api/v1/wallets/{wallet_id}/balance", headers=auth_headers)
    assert bal_response.status_code == 200
    data = bal_response.json()
    assert data["available_balance"] == 100.0
