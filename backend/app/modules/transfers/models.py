from sqlalchemy import Column, String, Numeric, Enum, DateTime, ForeignKey
from app.platform.infrastructure.db.base import Base
import enum
from datetime import datetime, timezone
from app.platform.core.utils.ids import generate_id

class TransferStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(String, primary_key=True, default=lambda: generate_id("trf"))
    sender_wallet_id = Column(String, ForeignKey("wallets.id"), index=True, nullable=False)
    receiver_wallet_id = Column(String, ForeignKey("wallets.id"), index=True, nullable=False)
    
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    
    status = Column(Enum(TransferStatus), default=TransferStatus.PENDING, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<Transfer {self.id} (Sender: {self.sender_wallet_id}, Receiver: {self.receiver_wallet_id}, Amount: {self.amount})>"
