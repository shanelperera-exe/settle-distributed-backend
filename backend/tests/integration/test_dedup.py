import pytest
import asyncio
import threading
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

from app.financial.idempotency.manager import IdempotencyManager, IdempotencyException
from app.modules.payments.models import Payment
from app.financial.ledger.models import LedgerEntry
from tests.conftest import engine, TestingSessionLocal

@pytest.mark.asyncio
async def test_idempotency_success(db):
    manager = IdempotencyManager(db)
    
    # 1. Create Lock
    key = "test-key-1"
    request_data = {"amount": 100}
    
    is_dup, cached_body, cached_code = manager.check_or_create_lock(key, request_data)
    assert is_dup is False
    assert cached_body is None
    
    # 2. Finalize
    manager.finalize(key, "pay_123", 200, {"status": "ok"})
    
    # 3. Check again -> should return dup
    is_dup2, cached_body2, cached_code2 = manager.check_or_create_lock(key, request_data)
    assert is_dup2 is True
    assert cached_code2 == 200
    assert cached_body2 == {"status": "ok"}

@pytest.mark.asyncio
async def test_idempotency_race_condition_simulation(db):
    """
    Simulate a race condition by manually triggering IntegrityError or 
    trying to lock concurrently.
    """
    manager = IdempotencyManager(db)
    key = "race-key-1"
    
    manager.check_or_create_lock(key, {"req": 1})
    
    # Second attempt should raise IdempotencyException (Conflict)
    with pytest.raises(IdempotencyException):
        manager.check_or_create_lock(key, {"req": 2})
        
@pytest.mark.asyncio
async def test_idempotency_failure_release(db):
    manager = IdempotencyManager(db)
    key = "fail-key-1"
    
    manager.check_or_create_lock(key, {"req": 1})
    
    manager.release_lock_on_failure(key)
    
    # After release, we should be able to lock again
    is_dup, _, _ = manager.check_or_create_lock(key, {"req": 1})
    assert is_dup is False
