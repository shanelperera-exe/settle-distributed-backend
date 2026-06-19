from typing import Any
from fastapi import APIRouter, Depends
from app.modules.users.models import User
from app.modules.auth.schemas import UserResponse
from app.api.dependencies.auth import get_current_active_user
from sqlalchemy.orm import Session
from app.platform.infrastructure.db.session import get_db
from app.modules.wallets.models import Wallet
from pydantic import BaseModel
from typing import List

class UserSearchResponse(BaseModel):
    id: str
    email: str
    wallet_id: str | None
router = APIRouter()

@router.get("/me", response_model=UserResponse)
def read_user_me(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user profile.
    """
    return current_user

@router.get("/search", response_model=List[UserSearchResponse])
def search_users(
    query: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Search users by email and return their primary wallet ID.
    """
    users = db.query(User).filter(User.email.ilike(f"%{query}%")).limit(10).all()
    results = []
    for u in users:
        wallet = db.query(Wallet).filter(Wallet.user_id == u.id).first()
        results.append({
            "id": u.id,
            "email": u.email,
            "wallet_id": wallet.id if wallet else None
        })
    return results
