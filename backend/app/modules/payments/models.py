from sqlalchemy import Column, String, Numeric, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.sql import func
import enum
from app.platform.infrastructure.db.base import Base

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class Payment(Base):
    """
    Represents a payment request in the system.
    In a distributed system, a payment might be initiated on one node,
    but processed or retried by another.
    """
    __tablename__ = "payments"

    id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=True, comment="Globally unique distributed transaction ID")
    stripe_payment_intent_id = Column(String, unique=True, index=True, nullable=True, comment="Stripe PaymentIntent ID")
    idempotency_key = Column(String, index=True, nullable=True, comment="Client-provided idempotency key")
    
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    
    sender_id = Column(String, index=True, nullable=False)
    receiver_id = Column(String, index=True, nullable=False)
    
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Track which node initially accepted this payment
    originating_node_id = Column(String, nullable=False)
    
    # Track which node actually completed the processing (could be different during failover)
    processing_node_id = Column(String, nullable=True)

    # Distributed consistency flags
    replicated = Column(Boolean, default=False, nullable=False, comment="True if replicated to quorum")
    committed = Column(Boolean, default=False, nullable=False, comment="True if locally committed after quorum")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
