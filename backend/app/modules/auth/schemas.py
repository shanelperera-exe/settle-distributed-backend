from typing import Optional
from pydantic import BaseModel, EmailStr
from app.modules.users.models import UserRole, UserState

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    role: UserRole
    state: UserState
    mfa_enabled: bool

    class Config:
        from_attributes = True

class EmailVerificationRequest(BaseModel):
    email: EmailStr
