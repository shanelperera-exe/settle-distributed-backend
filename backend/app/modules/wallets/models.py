from sqlalchemy import Column, String, Enum, DateTime, ForeignKey, Numeric
from app.platform.infrastructure.db.base import Base
import enum
from datetime import datetime, timezone
from app.platform.core.utils.ids import generate_id

class WalletStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String, primary_key=True, default=lambda: generate_id("wal"))
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(Enum(WalletStatus), default=WalletStatus.ACTIVE, nullable=False)
    
    # We do NOT store available_balance as a persistent raw number without strict ledger backing.
    # But caching it for read performance is standard fintech practice, as long as it's computed/reconciled.
    # For now, we rely on Ledger sums dynamically, but we can add cached balances later in reconciliation phase.
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<Wallet {self.id} (User: {self.user_id}, Currency: {self.currency})>"
