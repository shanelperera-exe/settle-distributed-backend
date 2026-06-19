from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.sql import func
from app.platform.infrastructure.db.base import Base

class NodeState(Base):
    """
    Tracks the historical and current state of a node in the cluster.
    While ZooKeeper is the source of truth for *liveness* (ephemeral znodes),
    the database tracks persistent metadata, such as how many times a node has restarted,
    when it was last seen, etc. This is useful for auditing and recovery.
    """
    __tablename__ = "node_states"

    node_id = Column(String, primary_key=True, index=True)
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    
    # Is the node currently perceived as alive?
    is_active = Column(Boolean, default=True)
    
    # Is this node the current leader?
    is_leader = Column(Boolean, default=False)
    
    # Timestamps for auditing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_heartbeat = Column(DateTime(timezone=True))