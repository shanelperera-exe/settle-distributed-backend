from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, DateTime, Enum, Boolean
from app.platform.infrastructure.db.base import Base
import enum
from app.platform.core.utils.ids import generate_id

class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPPORT = "SUPPORT"
    OPERATOR = "OPERATOR"

class UserState(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    LOCKED = "LOCKED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: generate_id("usr"))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    state = Column(Enum(UserState), default=UserState.PENDING_VERIFICATION, nullable=False)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<User {self.email} (Role: {self.role}, State: {self.state})>"
