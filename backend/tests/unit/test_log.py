import pytest
import asyncio
from app.platform.distributed.raft.log import RaftLog, LogEntry

@pytest.mark.asyncio
async def test_raft_log_initialization():
    log = RaftLog()
    assert log.last_included_index == 0
    assert len(log.entries) == 1
    assert log.get_last_log_index() == 0
    assert log.get_last_log_term() == 0

@pytest.mark.asyncio
async def test_raft_log_append(monkeypatch):
    # Mock persistence
    async def mock_append(*args, **kwargs):
        pass
    monkeypatch.setattr("app.platform.distributed.raft.log.append_raft_log_entry", mock_append)
    
    log = RaftLog()
    entry = LogEntry(term=1, command={"type": "payment"})
    await log.append("node-1", entry)
    
    assert log.get_last_log_index() == 1
    assert log.get_last_log_term() == 1
    assert log.get_term_at(1) == 1
    assert log.get_entry(1).command == {"type": "payment"}

@pytest.mark.asyncio
async def test_raft_log_compaction(monkeypatch):
    async def mock_compact(*args, **kwargs):
        pass
    monkeypatch.setattr("app.platform.distributed.raft.log.compact_raft_log", mock_compact)
    
    log = RaftLog()
    # Manually append 5 entries
    for i in range(1, 6):
        log.entries.append(LogEntry(term=1, command={"type": f"cmd_{i}"}))
        
    assert log.get_last_log_index() == 5
    
    # Compact up to threshold index 4. This should keep index 3 as dummy, delete 0,1,2.
    await log.compact("node-1", 4)
    
    assert log.last_included_index == 3
    assert len(log.entries) == 3 # indices 3, 4, 5
    assert log.get_last_log_index() == 5
    assert log.get_term_at(3) == 1
    assert log.get_term_at(4) == 1
    assert log.get_entry(4).command == {"type": "cmd_4"}
    
    # Try getting an old entry
    assert log.get_entry(1) is None
