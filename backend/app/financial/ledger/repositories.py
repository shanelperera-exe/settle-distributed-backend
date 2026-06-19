from sqlalchemy.orm import Session
from app.financial.ledger.models import LedgerEntry, LedgerStatus
from typing import Optional, List

class LedgerRepository:
    def __init__(self, db: Session):
        self.db = db

    def append_entry(self, entry: LedgerEntry) -> LedgerEntry:
        """
        Append a new entry to the immutable ledger.
        """
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_by_id(self, entry_id: str) -> Optional[LedgerEntry]:
        return self.db.query(LedgerEntry).filter(LedgerEntry.id == entry_id).first()

    def get_by_transaction_id(self, transaction_id: str) -> List[LedgerEntry]:
        """
        Retrieves all ledger entries associated with a specific distributed transaction.
        Usually, there's a DEBIT and CREDIT entry for a single transaction.
        """
        return self.db.query(LedgerEntry).filter(LedgerEntry.transaction_id == transaction_id).all()

    def update_status_by_transaction(self, transaction_id: str, status: LedgerStatus, replicated: bool = False, committed: bool = False):
        """
        Updates the status of all ledger entries for a given transaction_id.
        This is used during the distributed commit/rollback phase.
        """
        entries = self.get_by_transaction_id(transaction_id)
        for entry in entries:
            entry.status = status
            if replicated:
                entry.replicated = True
            if committed:
                entry.committed = True
        self.db.commit()
        
    def get_unreplicated_entries(self, limit: int = 100) -> List[LedgerEntry]:
        return self.db.query(LedgerEntry).filter(LedgerEntry.replicated == False).limit(limit).all()
