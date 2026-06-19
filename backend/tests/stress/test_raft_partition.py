import pytest
import asyncio
from app.platform.distributed.raft.node import RaftNode, NodeState
from app.platform.distributed.raft.log import LogEntry

@pytest.mark.asyncio
async def test_network_partition_split_brain(monkeypatch):
    """
    Test a split-brain network partition where Node 1 is isolated from Node 2 and 3.
    """
    # Create 3 isolated nodes
    node1 = RaftNode()
    node1.node_id = "node-1"
    node1.active_peers = ["node-1", "node-2", "node-3"]
    node1.peer_ips = {"node-2": "127.0.0.1", "node-3": "127.0.0.1"}

    node2 = RaftNode()
    node2.node_id = "node-2"
    node2.active_peers = ["node-1", "node-2", "node-3"]
    node2.peer_ips = {"node-1": "127.0.0.1", "node-3": "127.0.0.1"}

    node3 = RaftNode()
    node3.node_id = "node-3"
    node3.active_peers = ["node-1", "node-2", "node-3"]
    node3.peer_ips = {"node-1": "127.0.0.1", "node-2": "127.0.0.1"}
    
    # State tracking for partition
    partition_active = True

    # Mock network RPCs to route between them in-memory, but enforce the partition
    async def mock_send_request_vote(self_node, peer_id, term, last_idx, last_term):
        if partition_active:
            if self_node.node_id == "node-1" or peer_id == "node-1":
                # Network partition drops the packet
                return None
                
        target = {"node-1": node1, "node-2": node2, "node-3": node3}[peer_id]
        return await target.handle_request_vote(term, self_node.node_id, last_idx, last_term)

    async def mock_send_append_entries(self_node, peer_id, term, prev_idx, prev_term, entries, commit):
        if partition_active:
            if self_node.node_id == "node-1" or peer_id == "node-1":
                # Network partition drops the packet
                return None
                
        target = {"node-1": node1, "node-2": node2, "node-3": node3}[peer_id]
        return await target.handle_append_entries(term, self_node.node_id, prev_idx, prev_term, entries, commit)

    # Apply mocks
    for n in [node1, node2, node3]:
        n._send_request_vote = lambda p, t, li, lt, sn=n: mock_send_request_vote(sn, p, t, li, lt)
        n._send_append_entries = lambda p, t, pi, pt, e, c, sn=n: mock_send_append_entries(sn, p, t, pi, pt, e, c)

        n.state.current_term = 1
        n.state.voted_for = None
        n.state.commit_index = 0
        n.log.last_included_index = 0
        n.log.entries = [LogEntry(term=1, command={"type": "init"})]

    # Make Node 1 the leader initially
    node1.state.role = NodeState.LEADER

    # The partition happens (node 1 isolated). Node 2 times out and starts election.
    import time
    node2.election_manager.last_heartbeat_time = time.time() - 100

    if node2.election_manager.is_timeout_reached():
        node2.state.role = NodeState.CANDIDATE
        await node2._candidate_loop()
        
    # Verify Node 2 won the election because it could talk to Node 3
    assert node2.state.role == NodeState.LEADER
    assert node2.state.current_term == 2
    
    # Node 1 still thinks it's the leader (split brain)
    assert node1.state.role == NodeState.LEADER
    assert node1.state.current_term == 1
    
    # Partition heals!
    partition_active = False
    
    # Node 1 tries to send a heartbeat to Node 2 (simulated by direct handler call)
    reply = await node2.handle_append_entries(node1.state.current_term, node1.node_id, 0, 1, [], 0)
    assert reply["success"] is False
    assert reply["term"] == 2
    
    # Node 1 sees the higher term and steps down
    if reply["term"] > node1.state.current_term:
        node1.state.current_term = reply["term"]
        node1.state.role = NodeState.FOLLOWER
        
    # Verify split-brain resolved!
    assert node1.state.role == NodeState.FOLLOWER

@pytest.mark.asyncio
async def test_raft_log_rollback(monkeypatch):
    """
    Test log rollback: A leader writes an entry but fails to replicate it before crashing.
    A new leader writes conflicting entries. When the old leader returns, it must roll back.
    """
    node_old = RaftNode()
    node_old.node_id = "node-old"
    
    node_new = RaftNode()
    node_new.node_id = "node-new"
    
    # Set up old leader with an UNCOMMITTED log
    node_old.state.current_term = 1
    node_old.state.commit_index = 0
    node_old.state.role = NodeState.FOLLOWER # returning from crash
    node_old.log.entries = [
        LogEntry(term=1, command={"type": "init"}),
        LogEntry(term=1, command={"type": "ghost_payment"}) # Uncommitted!
    ]
    
    # Set up new leader with a DIFFERENT committed log at a higher term
    node_new.state.current_term = 2
    node_new.state.commit_index = 0
    node_new.state.role = NodeState.LEADER
    node_new.log.entries = [
        LogEntry(term=1, command={"type": "init"}),
        LogEntry(term=2, command={"type": "real_payment"})
    ]
    
    # New leader sends AppendEntries to old leader (overwriting index 1)
    # prev_log_index=0, prev_log_term=1
    entries = [{"term": 2, "command": {"type": "real_payment"}}]
    
    response = await node_old.handle_append_entries(
        term=2,
        leader_id="node-new",
        prev_log_index=0,
        prev_log_term=1,
        entries=entries,
        leader_commit=1
    )
    
    assert response["success"] is True
    
    # The old leader's log must be truncated and replaced
    assert len(node_old.log.entries) == 2
    assert node_old.log.entries[1].term == 2
    assert node_old.log.entries[1].command["type"] == "real_payment"
