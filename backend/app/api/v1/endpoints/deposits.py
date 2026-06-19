from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from decimal import Decimal
from sqlalchemy.orm import Session
from app.platform.infrastructure.db.session import get_db
from app.api.dependencies.auth import get_current_active_user
from app.modules.users.models import User
from app.modules.deposits.services import DepositService
from app.modules.wallets.services import WalletService

class DepositRequest(BaseModel):
    wallet_id: str
    amount: Decimal
    currency: str = "USD"

class DepositResponse(BaseModel):
    id: str
    wallet_id: str
    amount: Decimal
    currency: str
    status: str
    stripe_payment_intent_id: str

    class Config:
        from_attributes = True

router = APIRouter()

@router.post("/", response_model=DepositResponse, status_code=status.HTTP_201_CREATED)
def create_deposit(
    deposit_in: DepositRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Initiate a deposit to a wallet.
    Returns the Stripe PaymentIntent client secret indirectly through the deposit record (in a real app you'd return the client_secret directly to the frontend).
    """
    wallet_service = WalletService(db)
    
    wallet = wallet_service.get_wallet(deposit_in.wallet_id)
    if not wallet or wallet.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to deposit to this wallet")

    deposit_service = DepositService(db)
    deposit = deposit_service.initiate_deposit(
        wallet_id=deposit_in.wallet_id,
        amount=deposit_in.amount,
        currency=deposit_in.currency
    )
    return deposit
