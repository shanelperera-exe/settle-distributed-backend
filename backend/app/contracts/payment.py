from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime

class PaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    sender_id: str
    receiver_id: str
    payment_method: str = Field(default="pm_card_visa")

class PaymentResponse(BaseModel):
    id: str
    transaction_id: Optional[str]
    amount: Decimal
    currency: str
    sender_id: str
    receiver_id: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
