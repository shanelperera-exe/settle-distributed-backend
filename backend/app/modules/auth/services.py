from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.modules.users.models import User, UserState
from app.modules.auth.schemas import UserCreate
from app.modules.auth.security import get_password_hash, verify_password

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def register_user(self, user_in: UserCreate) -> User:
        user = self.get_user_by_email(user_in.email)
        if user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user with this email already exists in the system.",
            )
        
        # Create new user
        db_user = User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            state=UserState.ACTIVE # For this MVP, we automatically activate users. In prod, PENDING_VERIFICATION.
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
