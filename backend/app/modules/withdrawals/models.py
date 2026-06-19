from sqlalchemy import Column, String, Numeric, Enum, DateTime, ForeignKey
from app.platform.infrastructure.db.base import Base
import enum
from datetime import datetime, timezone
from app.platform.core.utils.ids import generate_id

class WithdrawalStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"

class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(String, primary_key=True, default=lambda: generate_id("wdl"))
    wallet_id = Column(String, ForeignKey("wallets.id"), index=True, nullable=False)
    
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    
    stripe_payout_id = Column(String, unique=True, index=True, nullable=True)
    status = Column(Enum(WithdrawalStatus), default=WithdrawalStatus.PENDING, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<Withdrawal {self.id} (Wallet: {self.wallet_id}, Amount: {self.amount}, Status: {self.status})>"
