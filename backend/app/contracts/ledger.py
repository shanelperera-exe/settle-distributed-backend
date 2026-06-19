from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime

class LedgerEntryCreate(BaseModel):
    payment_id: str
    account_id: str
    operation: str
    amount: Decimal
    currency: str = "USD"
    
class LedgerEntryResponse(BaseModel):
    id: str
    transaction_id: Optional[str]
    payment_id: str
    node_id: str
    account_id: str
    operation: str
    amount: Decimal
    currency: str
    status: str
    replicated: bool
    committed: bool
    timestamp: datetime
    
    class Config:
        from_attributes = True
