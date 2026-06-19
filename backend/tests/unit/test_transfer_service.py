import pytest
from sqlalchemy.orm import Session
from app.modules.transfers.services import TransferService
from app.modules.wallets.services import WalletService
from decimal import Decimal
from fastapi import HTTPException
import uuid

@pytest.mark.asyncio
async def test_initiate_transfer_success(db: Session, monkeypatch):
    transfer_service = TransferService(db)
    wallet_service = WalletService(db)
    
    sender_wallet = wallet_service.create_wallet(f"usr_{uuid.uuid4().hex}")
    receiver_wallet = wallet_service.create_wallet(f"usr_{uuid.uuid4().hex}")

    # Mock wallet balance check
    monkeypatch.setattr(
        "app.modules.wallets.services.WalletService.get_wallet_balance",
        lambda self, w_id: {"available_balance": Decimal("100.00")} if w_id == sender_wallet.id else {"available_balance": Decimal("0.00")}
    )

    # Mock failover service leader check
    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)

    # Mock Raft submission
    async def mock_submit(*args, **kwargs):
        return True
    monkeypatch.setattr("app.platform.distributed.raft.node.RaftNode.submit_command", mock_submit)

    transfer = await transfer_service.initiate_transfer(
        sender_wallet_id=sender_wallet.id,
        receiver_wallet_id=receiver_wallet.id,
        amount=Decimal("25.00")
    )

    # Returns dict now due to recent detached instance optimization
    assert transfer["amount"] == Decimal("25.00")
    assert transfer["sender_wallet_id"] == sender_wallet.id
    assert transfer["receiver_wallet_id"] == receiver_wallet.id
    assert transfer["status"] == "COMPLETED"

@pytest.mark.asyncio
async def test_initiate_transfer_insufficient_funds(db: Session, monkeypatch):
    transfer_service = TransferService(db)
    wallet_service = WalletService(db)
    
    sender_wallet = wallet_service.create_wallet(f"usr_{uuid.uuid4().hex}")
    receiver_wallet = wallet_service.create_wallet(f"usr_{uuid.uuid4().hex}")

    # Mock zero balance
    monkeypatch.setattr(
        "app.modules.wallets.services.WalletService.get_wallet_balance",
        lambda self, w_id: {"available_balance": Decimal("10.00")}
    )

    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)

    with pytest.raises(HTTPException) as exc_info:
        await transfer_service.initiate_transfer(
            sender_wallet_id=sender_wallet.id,
            receiver_wallet_id=receiver_wallet.id,
            amount=Decimal("50.00")
        )
    assert exc_info.value.status_code == 400
    assert "Insufficient funds" in exc_info.value.detail

@pytest.mark.asyncio
async def test_initiate_transfer_same_wallet(db: Session, monkeypatch):
    transfer_service = TransferService(db)
    wallet_service = WalletService(db)
    
    wallet = wallet_service.create_wallet(f"usr_{uuid.uuid4().hex}")

    monkeypatch.setattr("app.platform.distributed.failover_service.FailoverService.is_leader", lambda: True)

    with pytest.raises(HTTPException) as exc_info:
        await transfer_service.initiate_transfer(
            sender_wallet_id=wallet.id,
            receiver_wallet_id=wallet.id,
            amount=Decimal("10.00")
        )
    assert exc_info.value.status_code == 400
    assert "Cannot transfer to the same wallet" in exc_info.value.detail
