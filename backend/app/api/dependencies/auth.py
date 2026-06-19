import secrets
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.platform.core.config import settings
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.platform.infrastructure.db.session import get_db, SessionLocal
from app.modules.users.models import User
from app.modules.auth.security import SECRET_KEY, ALGORITHM

# HTTPBearer expects an Authorization header with a Bearer token
security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validates the Bearer token against the configured API_KEY.
    Uses constant-time comparison to prevent timing attacks.
    """
    # Compare token securely
    is_valid = secrets.compare_digest(credentials.credentials, settings.API_KEY)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

async def verify_raft_token(x_raft_token: str = Header(...)):
    """
    Validates the internal X-Raft-Token for Raft RPC endpoints.
    """
    is_valid = secrets.compare_digest(x_raft_token, settings.RAFT_INTERNAL_TOKEN)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing internal Raft token",
        )
    return x_raft_token

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_type: str = payload.get("type")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    # Check if user is suspended
    from app.modules.users.models import UserState
    if user.state == UserState.SUSPENDED:
        raise HTTPException(status_code=403, detail="Inactive user")
        
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    # Just an alias for now, could add more checks
    return current_user

async def get_current_user_ws(token: str) -> User | None:
    db = SessionLocal()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        user = db.query(User).filter(User.id == user_id).first()
        
        from app.modules.users.models import UserState
        if user and user.state == UserState.SUSPENDED:
            return None
            
        return user
    except Exception:
        return None
    finally:
        db.close()
