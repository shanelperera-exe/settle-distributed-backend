from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.platform.infrastructure.db.session import get_db
from app.api.dependencies.auth import get_current_active_user
from app.modules.users.models import User
from app.modules.wallets.services import WalletService
from pydantic import BaseModel

class WalletResponse(BaseModel):
    id: str
    currency: str
    status: str

    class Config:
        from_attributes = True

class BalanceResponse(BaseModel):
    wallet_id: str
    available_balance: float
    pending_balance: float
    currency: str

from datetime import datetime

class TransactionResponse(BaseModel):
    id: str
    transaction_id: str | None
    amount: float
    currency: str
    transaction_type: str
    status: str
    created_at: datetime
    debit_account_id: str
    credit_account_id: str

    class Config:
        from_attributes = True

router = APIRouter()

@router.post("/", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
def create_wallet(
    currency: str = "USD",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new wallet for the current user.
    """
    wallet_service = WalletService(db)
    return wallet_service.create_wallet(current_user.id, currency)

@router.get("/me", response_model=List[WalletResponse])
def get_my_wallets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get all wallets owned by the current user.
    """
    wallet_service = WalletService(db)
    return wallet_service.get_user_wallets(current_user.id)

@router.get("/{wallet_id}/balance", response_model=BalanceResponse)
def get_wallet_balance(
    wallet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get the dynamically calculated balance for a wallet from the immutable ledger.
    """
    wallet_service = WalletService(db)
    wallet = wallet_service.get_wallet(wallet_id)
    if not wallet or wallet.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Wallet not found")
        
    return wallet_service.get_wallet_balance(wallet_id)

@router.get("/{wallet_id}/transactions", response_model=List[TransactionResponse])
def get_wallet_transactions(
    wallet_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get recent transactions for a wallet.
    """
    wallet_service = WalletService(db)
    wallet = wallet_service.get_wallet(wallet_id)
    if not wallet or wallet.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Wallet not found")
        
    return wallet_service.get_wallet_transactions(wallet_id, limit)
