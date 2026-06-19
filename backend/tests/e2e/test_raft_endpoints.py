import pytest
from app.platform.core.config import settings

@pytest.mark.asyncio
async def test_request_vote(async_client):
    payload = {
        "term": 10,
        "candidate_id": "test-node-2",
        "last_log_index": 5,
        "last_log_term": 10
    }
    
    headers = {
        "X-Raft-Token": settings.RAFT_INTERNAL_TOKEN
    }
    
    resp = await async_client.post("/api/v1/raft/request_vote", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "term" in data
    assert "vote_granted" in data

@pytest.mark.asyncio
async def test_append_entries(async_client):
    payload = {
        "term": 10,
        "leader_id": "test-node-2",
        "prev_log_index": 5,
        "prev_log_term": 10,
        "entries": [],
        "leader_commit": 5
    }
    
    headers = {
        "X-Raft-Token": settings.RAFT_INTERNAL_TOKEN
    }
    
    resp = await async_client.post("/api/v1/raft/append_entries", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "term" in data
    assert "success" in data
