from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.platform.infrastructure.db.session import SessionLocal
from app.platform.core.config import settings
from app.platform.core.models import User
from app.platform.core.security import verify_password, create_access_token
from app.api.deps import get_db, get_current_user

router = APIRouter()

@router.post("/login/access-token")
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    return {
        "access_token": create_access_token(
            data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
        "role": user.role,
        "username": user.username
    }

@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current user info.
    """
    return {
        "username": current_user.username,
        "role": current_user.role
    }
