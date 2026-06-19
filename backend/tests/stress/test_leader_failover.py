import pytest
import asyncio
from app.platform.distributed.raft.node import RaftNode
from app.platform.distributed.raft.state import NodeState

@pytest.mark.asyncio
async def test_leader_failover_simulation(monkeypatch):
    """
    Simulate a cluster of 3 nodes and force a leader failover by manipulating timeouts.
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
    
    # Mock network RPCs to route between them in-memory
    async def mock_send_request_vote(self_node, peer_id, term, last_idx, last_term):
        target = {"node-1": node1, "node-2": node2, "node-3": node3}[peer_id]
        return await target.handle_request_vote(term, self_node.node_id, last_idx, last_term)
        
    async def mock_send_append_entries(self_node, peer_id, term, prev_idx, prev_term, entries, commit):
        target = {"node-1": node1, "node-2": node2, "node-3": node3}[peer_id]
        return await target.handle_append_entries(term, self_node.node_id, prev_idx, prev_term, entries, commit)

    # Apply mocks
    from app.platform.distributed.raft.log import LogEntry
    for n in [node1, node2, node3]:
        n._send_request_vote = lambda p, t, li, lt, sn=n: mock_send_request_vote(sn, p, t, li, lt)
        n._send_append_entries = lambda p, t, pi, pt, e, c, sn=n: mock_send_append_entries(sn, p, t, pi, pt, e, c)
        
        # Mock load state
        n.state.current_term = 0
        n.state.voted_for = None
        n.state.commit_index = 0
        n.log.last_included_index = 0
        n.log.entries = [LogEntry(term=0, command={"type": "init"})]

    # Make Node 1 the leader
    node1.state.role = NodeState.LEADER
    node1.state.current_term = 1
    node2.state.role = NodeState.FOLLOWER
    node2.state.current_term = 1
    node3.state.role = NodeState.FOLLOWER
    node3.state.current_term = 1
    
    # Force node 2's timeout
    import time
    node2.election_manager.last_heartbeat_time = time.time() - 100
    
    # Run 1 tick of node2's follower loop to trigger election
    if node2.election_manager.is_timeout_reached():
        node2.state.role = NodeState.CANDIDATE
        await node2._candidate_loop()
        
    # After election, Node 2 should be the new leader with term 2
    assert node2.state.role == NodeState.LEADER
    assert node2.state.current_term == 2
    
    # Node 1 and Node 3 should be followers for term 2
    # But wait, Node 1 hasn't received an append_entries yet.
    # Let's run a leader tick on Node 2
    task = asyncio.create_task(node2._leader_loop())
    await asyncio.sleep(0.2) # let it send heartbeats
    node2.state.role = NodeState.FOLLOWER # force stop
    await task
    
    assert node1.state.role == NodeState.FOLLOWER
    assert node1.state.current_term == 2
    assert node3.state.role == NodeState.FOLLOWER
    assert node3.state.current_term == 2
