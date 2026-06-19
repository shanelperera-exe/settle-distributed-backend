from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List
from decimal import Decimal
from app.modules.wallets.models import Wallet, WalletStatus
from app.financial.ledger.models import LedgerEntry, LedgerStatus

class WalletService:
    def __init__(self, db: Session):
        self.db = db

    def create_wallet(self, user_id: str, currency: str = "USD") -> Wallet:
        wallet = Wallet(user_id=user_id, currency=currency)
        self.db.add(wallet)
        self.db.commit()
        self.db.refresh(wallet)
        return wallet

    def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        return self.db.query(Wallet).filter(Wallet.id == wallet_id).first()

    def get_user_wallets(self, user_id: str) -> List[Wallet]:
        return self.db.query(Wallet).filter(Wallet.user_id == user_id).all()

    def get_wallet_balance(self, wallet_id: str) -> dict:
        """
        Dynamically calculates the wallet balance by summing all ledger entries.
        This ensures 100% strong consistency with the distributed ledger.
        
        A wallet's balance = (Sum of Credits) - (Sum of Debits)
        """
        # Calculate Total Credits (funds added to this wallet)
        credit_sum = self.db.query(func.sum(LedgerEntry.amount)).filter(
            LedgerEntry.credit_account_id == wallet_id,
            LedgerEntry.status == LedgerStatus.COMMITTED
        ).scalar() or Decimal('0.00')
        
        # Calculate Total Debits (funds deducted from this wallet)
        debit_sum = self.db.query(func.sum(LedgerEntry.amount)).filter(
            LedgerEntry.debit_account_id == wallet_id,
            LedgerEntry.status == LedgerStatus.COMMITTED
        ).scalar() or Decimal('0.00')

        # Calculate Pending Credits (e.g. Stripe deposits waiting for quorum)
        pending_credit_sum = self.db.query(func.sum(LedgerEntry.amount)).filter(
            LedgerEntry.credit_account_id == wallet_id,
            LedgerEntry.status == LedgerStatus.PENDING
        ).scalar() or Decimal('0.00')

        available_balance = Decimal(credit_sum) - Decimal(debit_sum)

        return {
            "wallet_id": wallet_id,
            "available_balance": available_balance,
            "pending_balance": pending_credit_sum,
            "currency": "USD" # Assuming single currency for MVP
        }

    def get_wallet_transactions(self, wallet_id: str, limit: int = 50) -> List[LedgerEntry]:
        """
        Get recent transactions for a wallet (both credits and debits).
        """
        return self.db.query(LedgerEntry).filter(
            or_(
                LedgerEntry.credit_account_id == wallet_id,
                LedgerEntry.debit_account_id == wallet_id
            )
        ).order_by(LedgerEntry.created_at.desc()).limit(limit).all()
