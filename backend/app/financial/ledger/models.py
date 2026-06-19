from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
import enum
from app.platform.infrastructure.db.base import Base

class TransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"
    FEE = "FEE"
    REFUND = "REFUND"

class LedgerStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"

class LedgerEntry(Base):
    """
    Immutable double-entry ledger of all financial movements.
    Used for reconciliation and ensuring consistency across the distributed system.
    """
    __tablename__ = "ledger_entries"

    id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, index=True, nullable=True) # E.g., the high-level transfer ID
    
    # Double-entry fields
    debit_account_id = Column(String, index=True, nullable=False, comment="Account from which funds are deducted")
    credit_account_id = Column(String, index=True, nullable=False, comment="Account to which funds are added")
    
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    transaction_type = Column(Enum(TransactionType), nullable=False)
    
    status = Column(Enum(LedgerStatus), default=LedgerStatus.PENDING, nullable=False)
    
    # Distributed consistency metadata
    consensus_term = Column(Numeric, nullable=True, comment="Raft term when this was proposed")
    leader_node = Column(String, nullable=True, comment="The node that proposed this entry")
    replicated = Column(Boolean, default=False, nullable=False, comment="True if replicated to quorum")
    committed = Column(Boolean, default=False, nullable=False, comment="True if locally committed after quorum")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
