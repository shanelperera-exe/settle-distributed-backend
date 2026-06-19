from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.platform.infrastructure.db.session import get_db
from app.modules.auth.schemas import Token, UserCreate, UserResponse, EmailVerificationRequest
from app.modules.auth.services import AuthService
from app.modules.auth.security import create_access_token, create_refresh_token
from app.api.dependencies.auth import get_current_user
from app.modules.users.models import User
from app.platform.integrations.brevo_service import email_service
from app.platform.core.config import settings
import random

router = APIRouter()

# Temporary in-memory store for verification codes (for MVP purposes)
# In production, use Redis or a database table.
verification_codes_store = {}

@router.post("/send-verification-code", status_code=status.HTTP_200_OK)
def send_verification_code(
    request: EmailVerificationRequest,
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Generate a 6-digit code and send it to the user's email.
    """
    code = f"{random.randint(0, 999999):06d}"
    verification_codes_store[request.email] = code
    
    background_tasks.add_task(
        email_service.send_template_email,
        template_name="welcome.html",
        context={
            "name": request.email.split('@')[0],
            "verification_code": code
        },
        to_email=request.email,
        subject="Settle - Your Verification Code"
    )
    
    return {"message": "Verification code sent successfully"}

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """
    Register a new user.
    """
    auth_service = AuthService(db)
    user = auth_service.register_user(user_in)
    
    return user

@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif user.state.value == "SUSPENDED":
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }
