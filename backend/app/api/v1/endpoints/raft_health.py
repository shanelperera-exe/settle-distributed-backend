from fastapi import APIRouter
from app.platform.distributed.raft.node import raft_node
from app.platform.distributed.raft.state import NodeState

router = APIRouter()

@router.get("/raft")
async def raft_health():
    """
    Exposes the internal Raft state for monitoring.
    """
    state = raft_node.state
    return {
        "node_id": raft_node.node_id,
        "role": state.role.name,
        "current_term": state.current_term,
        "voted_for": state.voted_for,
        "leader_id": state.leader_id,
        "commit_index": state.commit_index,
        "last_applied": state.last_applied,
        "log_length": raft_node.log.get_last_log_index() + 1
    }
    
@router.get("/cluster")
async def cluster_health():
    """
    Exposes the ZooKeeper cluster membership view.
    """
    return {
        "active_peers": raft_node.active_peers,
        "total_active_nodes": len(raft_node.active_peers)
    }
