from enum import Enum
from typing import Optional, Dict

class NodeState(Enum):
    """
    The three Raft Node States:
    
    1. FOLLOWER: 
       - Passive state. Only responds to RPCs from leaders and candidates.
       - Starts election timer. If timeout occurs without receiving heartbeat, transitions to CANDIDATE.
       
    2. CANDIDATE:
       - Active state during elections.
       - Increments current_term, votes for self, and sends RequestVote RPCs to all peers.
       - If receives majority votes, transitions to LEADER.
       - If receives AppendEntries from a valid leader, transitions back to FOLLOWER.
       
    3. LEADER:
       - Active coordinator. Only one leader exists per term.
       - Sends periodic heartbeats (empty AppendEntries RPCs) to prevent followers from calling elections.
       - Accepts client requests (payments), appends to local log, and coordinates replication.
    """
    FOLLOWER = 1
    CANDIDATE = 2
    LEADER = 3

from app.platform.distributed.raft.persistence import load_raft_state

class RaftState:
    """
    Encapsulates all the Volatile and Persistent state required by the Raft Algorithm.
    In a true production environment, Persistent state must be flushed to stable storage (disk) 
    before responding to RPCs to survive crashes.
    """
    def __init__(self):
        # --- Persistent State (Should survive crashes) ---
        # Latest term server has seen (initialized to 0)
        self.current_term: int = 0
        
        # CandidateId that received vote in current term (None if none)
        self.voted_for: Optional[str] = None
        
    async def load(self, node_id: str):
        """Loads persistent state from the database on startup."""
        self.current_term, self.voted_for = await load_raft_state(node_id)
        
        # --- Volatile State (Reinitialized on startup) ---
        # Index of highest log entry known to be committed (initialized to 0)
        # Commit means a majority of nodes have replicated it.
        self.commit_index: int = 0
        
        # Index of highest log entry applied to state machine (Postgres)
        self.last_applied: int = 0
        
        # --- Volatile State for Leaders (Reinitialized after election) ---
        # For each server, index of the next log entry to send to that server
        # Initialized to leader's last log index + 1
        self.next_index: Dict[str, int] = {}
        
        # For each server, index of highest log entry known to be replicated on server
        # Initialized to 0, increases monotonically
        self.match_index: Dict[str, int] = {}
        
        # The current role of this node
        self.role: NodeState = NodeState.FOLLOWER
        
        # The current leader (known by followers)
        self.leader_id: Optional[str] = None
