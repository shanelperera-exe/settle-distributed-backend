import pytest
import time
from app.platform.distributed.raft.election import ElectionManager

def test_election_manager_timeout_bounds():
    manager = ElectionManager()
    assert 15.0 <= manager.current_timeout <= 20.0

def test_election_manager_reset():
    manager = ElectionManager()
    old_time = manager.last_heartbeat_time
    time.sleep(0.01)
    manager.reset_timer()
    assert manager.last_heartbeat_time > old_time

def test_election_manager_timeout_reached(monkeypatch):
    manager = ElectionManager()
    assert not manager.is_timeout_reached()
    
    # Mock time.time to be past the timeout
    monkeypatch.setattr(time, "time", lambda: manager.last_heartbeat_time + manager.current_timeout + 1.0)
    assert manager.is_timeout_reached()
