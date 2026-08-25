import secrets
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.platform.core.config import settings

# HTTPBearer expects an Authorization header with a Bearer token
security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validates the Bearer token against the configured API_KEY.
    Uses constant-time comparison to prevent timing attacks.
    """
    # Compare token securely
    is_valid = secrets.compare_digest(credentials.credentials, settings.API_KEY)
    
    if is_valid:
        return credentials.credentials
        
    # If not API key, check if it's a valid JWT
    from jose import jwt, JWTError
    try:
        jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return credentials.credentials
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key/Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
