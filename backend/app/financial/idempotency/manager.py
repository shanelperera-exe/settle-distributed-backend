import hashlib
import json
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from app.financial.idempotency.models import IdempotencyKey
from app.platform.observability.logging import logger

class IdempotencyException(Exception):
    pass

class IdempotencyManager:
    """
    Subsystem to enforce EXACTLY-ONCE semantics in a distributed environment.
    
    Why Deduplication?
    In distributed systems, clients or proxies may retry requests due to network
    timeouts. A timeout does not mean the server failed to process the payment;
    the response might have just been lost on the way back.
    If we process a retry without deduplication, we charge the user twice.
    
    Idempotency allows a client to safely retry a payment request by attaching a
    unique 'Idempotency-Key' header. We store the response of the first successful
    processing and return that cached response for any subsequent retries.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def _generate_hash(self, payload: Dict[str, Any]) -> str:
        """
        Creates a deterministic hash of the request payload.
        This prevents a client from reusing the same idempotency key for a 
        completely different payment request (Replay Prevention).
        """
        # Sort keys to ensure deterministic JSON serialization
        serialized = json.dumps(payload, sort_keys=True).encode('utf-8')
        return hashlib.sha256(serialized).hexdigest()

    def _check_or_create_lock_sync(self, key: str, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], int]:
        """
        Validates the idempotency key before processing begins.
        
        Returns a tuple: (is_duplicate, cached_response_body, cached_response_code)
        
        If is_duplicate is True, the caller should immediately return the cached response.
        If is_duplicate is False, the caller proceeds to process the payment.
        """
        req_hash = self._generate_hash(payload)
        
        # We attempt to insert the new key directly.
        # If another concurrent request inserted it first, an IntegrityError will be thrown.
        new_key = IdempotencyKey(
            key=key,
            request_hash=req_hash,
            status="PROCESSING",
            response_code="0", # Placeholder
            response_body={},  # Placeholder
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24) # Keys expire after 24h
        )
        
        try:
            self.db.add(new_key)
            self.db.commit()
            return False, None, 0
        except IntegrityError:
            # Race condition caught! Another request beat us to the lock.
            self.db.rollback()
            existing_key = self.db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
            
            if existing_key:
                # 1. Tamper/Replay Prevention Check
                if existing_key.request_hash and existing_key.request_hash != req_hash:
                    logger.error(f"Idempotency key {key} reused with different payload.")
                    raise IdempotencyException("Idempotency key already used with a different request payload.")
                    
                # 2. Concurrent Processing Check
                if existing_key.status == "PROCESSING":
                    # The first request is still being processed.
                    logger.warning(f"Concurrent request detected for idempotency key {key}.")
                    raise IdempotencyException("A request with this idempotency key is currently being processed.")
                    
                # 3. Duplicate Request Detected
                logger.info(f"Duplicate request detected for key {key}. Returning cached response.")
                return True, existing_key.response_body, int(existing_key.response_code)
            
            # This should never happen unless the row was instantly deleted
            raise IdempotencyException("Failed to acquire idempotency lock.")

    async def check_or_create_lock(self, key: str, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], int]:
        import asyncio
        return await asyncio.to_thread(self._check_or_create_lock_sync, key, payload)

    def _finalize_sync(self, key: str, payment_id: str, response_code: int, response_body: Dict[str, Any]):
        """
        After the payment is successfully committed locally (and replicated),
        we update the idempotency record with the final response.
        """
        existing_key = self.db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
        if existing_key:
            existing_key.status = "COMPLETED"
            existing_key.payment_id = payment_id
            existing_key.response_code = str(response_code)
            existing_key.response_body = response_body
            self.db.commit()
            logger.info(f"Finalized idempotency record for key {key}.")
            
    async def finalize(self, key: str, payment_id: str, response_code: int, response_body: Dict[str, Any]):
        import asyncio
        await asyncio.to_thread(self._finalize_sync, key, payment_id, response_code, response_body)
            
    def _release_lock_on_failure_sync(self, key: str):
        """
        If the payment fails (e.g., due to bad validation before quorum),
        we should delete or fail the idempotency key so the client can retry.
        """
        existing_key = self.db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
        if existing_key and existing_key.status == "PROCESSING":
            self.db.delete(existing_key)
            self.db.commit()
            logger.info(f"Released processing lock for idempotency key {key} due to failure.")

    async def release_lock_on_failure(self, key: str):
        import asyncio
        await asyncio.to_thread(self._release_lock_on_failure_sync, key)
