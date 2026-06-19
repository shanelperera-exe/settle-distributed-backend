import pytest
from sqlalchemy.orm import Session
from app.modules.wallets.services import WalletService
from app.modules.wallets.models import Wallet
from app.financial.ledger.models import LedgerEntry, TransactionType, LedgerStatus
from decimal import Decimal
import uuid

def test_create_wallet(db: Session):
    service = WalletService(db)
    user_id = f"usr_{uuid.uuid4().hex}"
    wallet = service.create_wallet(user_id=user_id, currency="USD")
    
    assert wallet is not None
    assert wallet.user_id == user_id
    assert wallet.currency == "USD"
    assert wallet.id.startswith("wal_")

    fetched = service.get_wallet(wallet.id)
    assert fetched is not None
    assert fetched.id == wallet.id

def test_get_wallet_balance(db: Session):
    service = WalletService(db)
    user_id = f"usr_{uuid.uuid4().hex}"
    wallet = service.create_wallet(user_id=user_id, currency="USD")

    # Initial balance should be 0
    balance = service.get_wallet_balance(wallet.id)
    assert balance["available_balance"] == Decimal("0.00")
    assert balance["pending_balance"] == Decimal("0.00")

    # Add COMMITTED credit (e.g. deposit)
    db.add(LedgerEntry(
        id=f"led_{uuid.uuid4().hex}",
        transaction_id="txn_1",
        debit_account_id="sys_stripe_clearing",
        credit_account_id=wallet.id,
        amount=100.0,
        currency="USD",
        transaction_type=TransactionType.DEPOSIT,
        status=LedgerStatus.COMMITTED
    ))

    # Add PENDING credit
    db.add(LedgerEntry(
        id=f"led_{uuid.uuid4().hex}",
        transaction_id="txn_2",
        debit_account_id="sys_stripe_clearing",
        credit_account_id=wallet.id,
        amount=50.0,
        currency="USD",
        transaction_type=TransactionType.DEPOSIT,
        status=LedgerStatus.PENDING
    ))

    # Add COMMITTED debit (e.g. transfer out)
    db.add(LedgerEntry(
        id=f"led_{uuid.uuid4().hex}",
        transaction_id="txn_3",
        debit_account_id=wallet.id,
        credit_account_id="another_wallet",
        amount=25.0,
        currency="USD",
        transaction_type=TransactionType.TRANSFER,
        status=LedgerStatus.COMMITTED
    ))

    db.commit()

    balance = service.get_wallet_balance(wallet.id)
    assert balance["available_balance"] == Decimal("75.00") # 100 - 25
    assert balance["pending_balance"] == Decimal("50.00")

def test_get_user_wallets(db: Session):
    service = WalletService(db)
    user_id = f"usr_{uuid.uuid4().hex}"
    
    wallets = service.get_user_wallets(user_id)
    assert len(wallets) == 0

    w1 = service.create_wallet(user_id=user_id, currency="USD")
    w2 = service.create_wallet(user_id=user_id, currency="EUR")

    wallets = service.get_user_wallets(user_id)
    assert len(wallets) == 2
    assert {w.id for w in wallets} == {w1.id, w2.id}
