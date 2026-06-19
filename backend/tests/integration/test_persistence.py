import pytest
from app.platform.distributed.raft.persistence import (
    _save_raft_state_sync,
    _load_raft_state_sync,
    _append_raft_log_entry_sync,
    _load_raft_log_sync,
    _truncate_and_append_raft_log_sync,
    _compact_raft_log_sync,
)
from app.platform.distributed.raft.models import RaftStateModel, RaftLogModel

def test_raft_state_persistence(db):
    from sqlalchemy import text
    db.execute(text("DELETE FROM raft_state"))
    db.execute(text("DELETE FROM raft_log"))
    db.commit()
    import uuid
    node_id = f"test-node-{uuid.uuid4().hex}"
    
    # Save state
    _save_raft_state_sync(node_id, current_term=5, voted_for="test-node-2")
    
    # Load state
    term, voted_for = _load_raft_state_sync(node_id)
    assert term == 5
    assert voted_for == "test-node-2"
    
    # Update state
    _save_raft_state_sync(node_id, current_term=6, voted_for=None)
    term, voted_for = _load_raft_state_sync(node_id)
    assert term == 6
    assert voted_for is None

def test_raft_log_persistence(db):
    from sqlalchemy import text
    db.execute(text("DELETE FROM raft_log"))
    db.commit()
    import uuid
    node_id = f"test-node-{uuid.uuid4().hex}"
    
    # Append
    _append_raft_log_entry_sync(node_id, 1, 1, {"type": "test_1"})
    _append_raft_log_entry_sync(node_id, 2, 1, {"type": "test_2"})
    
    # Load
    logs = _load_raft_log_sync(node_id)
    
    assert logs[-2]["command"]["type"] == "test_1"
    assert logs[-1]["command"]["type"] == "test_2"
    
def test_raft_log_compaction(db):
    from sqlalchemy import text
    db.execute(text("DELETE FROM raft_log"))
    db.commit()
    import uuid
    node_id = f"test-node-{uuid.uuid4().hex}"
    
    # Add entries 0 to 5
    for i in range(6):
        _append_raft_log_entry_sync(node_id, i, 1, {"type": f"test_{i}"})
        
    # Compact up to 3. This should delete < 3 (i.e. 0, 1, 2).
    _compact_raft_log_sync(node_id, 3)
    
    logs = _load_raft_log_sync(node_id)
    # Remaining should be 3, 4, 5
    assert len(logs) == 3
    assert logs[0]["index"] == 3
    assert logs[1]["index"] == 4
    assert logs[2]["index"] == 5
