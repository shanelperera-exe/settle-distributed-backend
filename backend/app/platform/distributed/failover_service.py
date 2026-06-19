import logging
from app.platform.distributed.raft.node import raft_node
from app.platform.distributed.raft.state import NodeState

logger = logging.getLogger(__name__)

class FailoverService:
    """
    Handles higher-level application failover logic.
    For example, if the active Raft node steps down from LEADER,
    this service could cancel pending background transactions 
    that were awaiting quorum.
    """
    
    @staticmethod
    def is_leader() -> bool:
        """Returns True if this node is currently the Raft Leader."""
        return raft_node.state.role == NodeState.LEADER
        
    @staticmethod
    def get_leader_id() -> str:
        """Returns the ID of the current leader, or None if unknown."""
        return raft_node.state.leader_id

    @staticmethod
    def ensure_leader():
        """
        Raises an exception if called on a Follower.
        Useful for intercepting payment writes on followers and redirecting them.
        """
        if not FailoverService.is_leader():
            raise Exception(f"Not the leader. Current leader is {FailoverService.get_leader_id()}")
