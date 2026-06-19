from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from decimal import Decimal
from sqlalchemy.orm import Session
from app.platform.infrastructure.db.session import get_db
from app.api.dependencies.auth import get_current_active_user
from app.modules.users.models import User
from app.modules.withdrawals.services import WithdrawalService
from app.modules.wallets.services import WalletService

class WithdrawalRequest(BaseModel):
    wallet_id: str
    amount: Decimal
    currency: str = "USD"

class WithdrawalResponse(BaseModel):
    id: str
    wallet_id: str
    amount: Decimal
    currency: str
    status: str
    stripe_payout_id: str | None = None

    class Config:
        from_attributes = True

router = APIRouter()

@router.post("/", response_model=WithdrawalResponse, status_code=status.HTTP_201_CREATED)
async def create_withdrawal(
    withdrawal_in: WithdrawalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Initiate a withdrawal from a wallet.
    Uses the Raft Consensus Engine to atomically lock the funds, then uses Stripe to payout.
    """
    wallet_service = WalletService(db)
    
    wallet = wallet_service.get_wallet(withdrawal_in.wallet_id)
    if not wallet or wallet.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to withdraw from this wallet")

    withdrawal_service = WithdrawalService(db)
    withdrawal = await withdrawal_service.initiate_withdrawal(
        wallet_id=withdrawal_in.wallet_id,
        amount=withdrawal_in.amount,
        currency=withdrawal_in.currency
    )
    return withdrawal
