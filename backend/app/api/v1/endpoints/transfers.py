from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from decimal import Decimal
from sqlalchemy.orm import Session
from app.platform.infrastructure.db.session import get_db
from app.api.dependencies.auth import get_current_active_user
from app.modules.users.models import User
from app.modules.transfers.services import TransferService
from app.modules.wallets.services import WalletService

class TransferRequest(BaseModel):
    receiver_wallet_id: str
    amount: Decimal
    currency: str = "USD"

class TransferResponse(BaseModel):
    id: str
    sender_wallet_id: str
    receiver_wallet_id: str
    amount: Decimal
    currency: str
    status: str

    class Config:
        from_attributes = True

router = APIRouter()

@router.post("/", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    transfer_in: TransferRequest,
    sender_wallet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Initiate a transfer between wallets.
    """
    wallet_service = WalletService(db)
    
    # Ensure sender owns the source wallet
    sender_wallet = wallet_service.get_wallet(sender_wallet_id)
    if not sender_wallet or sender_wallet.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to send from this wallet")

    transfer_service = TransferService(db)
    
    try:
        transfer = await transfer_service.initiate_transfer(
            sender_wallet_id=sender_wallet_id,
            receiver_wallet_id=transfer_in.receiver_wallet_id,
            amount=transfer_in.amount,
            currency=transfer_in.currency
        )
        return transfer
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
