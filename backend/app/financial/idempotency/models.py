from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from app.platform.infrastructure.db.base import Base

class IdempotencyKey(Base):
    """
    Crucial for distributed systems where network retries are common.
    Ensures that if a client sends the same payment request twice (e.g., due to a timeout),
    the system does not process the payment twice.
    
    We store the response body so we can return the exact same response
    on subsequent identical requests.
    """
    __tablename__ = "idempotency_keys"

    key = Column(String, primary_key=True, index=True)
    request_hash = Column(String, nullable=True, comment="Hash of the request payload to prevent payload tampering during retries")
    payment_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="PROCESSING")
    
    # The HTTP status code of the saved response
    response_code = Column(String, nullable=False)
    
    # The serialized JSON response body
    response_body = Column(JSON, nullable=False)
    
    # When this key was first used
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
