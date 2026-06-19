import pytest
import uuid
from app.platform.distributed.raft.node import RaftNode, NodeState
from app.platform.distributed.raft.persistence import _save_raft_state_sync, _append_raft_log_entry_sync
from sqlalchemy import text

@pytest.mark.asyncio
async def test_full_cluster_crash_and_recovery(db, monkeypatch):
    """
    Test total cluster power failure and recovery from the DB persistent logs.
    """
    # 1. Clear database logs
    db.execute(text("DELETE FROM raft_state"))
    db.execute(text("DELETE FROM raft_log"))
    db.commit()

    cluster_id = f"test-cluster-{uuid.uuid4().hex}"
    node1_id = f"node-1-{cluster_id}"
    node2_id = f"node-2-{cluster_id}"
    node3_id = f"node-3-{cluster_id}"
    
    # 2. Simulate Pre-Crash Persistence
    # Node 1 was the leader in term 3. It had 2 logs.
    _save_raft_state_sync(node1_id, current_term=3, voted_for=node1_id)
    _append_raft_log_entry_sync(node1_id, 1, 1, {"type": "init"})
    _append_raft_log_entry_sync(node1_id, 2, 3, {"type": "payment_1"})
    
    # Node 2 was a follower in term 3. It had 2 logs.
    _save_raft_state_sync(node2_id, current_term=3, voted_for=node1_id)
    _append_raft_log_entry_sync(node2_id, 1, 1, {"type": "init"})
    _append_raft_log_entry_sync(node2_id, 2, 3, {"type": "payment_1"})
    
    # Node 3 was a follower in term 3 but only received the first log.
    _save_raft_state_sync(node3_id, current_term=3, voted_for=node1_id)
    _append_raft_log_entry_sync(node3_id, 1, 1, {"type": "init"})
    
    # 3. Crash Recovery (Nodes reboot)
    # We initialize fresh RaftNode instances. They should load their state from DB!
    # Wait, the node loads state asynchronously in start() or synchronously? 
    # Currently node loads in `start()`. Let's mock `start()` components.
    
    node1 = RaftNode()
    node1.node_id = node1_id
    
    node2 = RaftNode()
    node2.node_id = node2_id
    
    node3 = RaftNode()
    node3.node_id = node3_id
    
    # Load persistence
    for n in [node1, node2, node3]:
        await n.state.load(n.node_id)
        await n.log.load(n.node_id)
        
    # 4. Verify Nodes recovered their state successfully
    assert node1.state.current_term == 3
    assert node1.state.voted_for == node1_id
    assert len(node1.log.entries) == 3 # including dummy 0
    assert node1.log.entries[-1].term == 3
    
    assert node3.state.current_term == 3
    assert len(node3.log.entries) == 2 # dummy 0 + 1 log
    
    # 5. Verify the election uses the recovered logs
    # Node 3 tries to become leader in term 4.
    node3.state.current_term = 4
    
    # Node 1 checks Node 3's request vote.
    # Node 3's last log is index 1, term 1. Node 1's last log is index 2, term 3.
    # Raft paper: Node 1 should REJECT Node 3 because Node 1's log is more up-to-date.
    response = await node1.handle_request_vote(term=4, candidate_id="node-3", last_log_index=1, last_log_term=1)
    
    assert response["vote_granted"] is False # Crucial for data safety!
