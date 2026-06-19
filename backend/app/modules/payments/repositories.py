from sqlalchemy.orm import Session
from app.modules.payments.models import Payment, PaymentStatus
from typing import Optional, List

class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_by_id(self, payment_id: str) -> Optional[Payment]:
        return self.db.query(Payment).filter(Payment.id == payment_id).first()

    def get_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        return self.db.query(Payment).filter(Payment.transaction_id == transaction_id).first()

    def get_by_stripe_intent_id(self, stripe_intent_id: str) -> Optional[Payment]:
        return self.db.query(Payment).filter(Payment.stripe_payment_intent_id == stripe_intent_id).first()

    def update_status(self, payment_id: str, status: PaymentStatus, processing_node_id: Optional[str] = None) -> Optional[Payment]:
        payment = self.get_by_id(payment_id)
        if payment:
            payment.status = status
            if processing_node_id:
                payment.processing_node_id = processing_node_id
            self.db.commit()
            self.db.refresh(payment)
        return payment

    def get_pending_payments(self, limit: int = 100) -> List[Payment]:
        return self.db.query(Payment).filter(Payment.status == PaymentStatus.PENDING).limit(limit).all()
