from sqlalchemy import Column, String, Integer, BigInteger, UniqueConstraint, JSON
from sqlalchemy.sql import func
from app.platform.infrastructure.db.base import Base

class RaftStateModel(Base):
    """
    Persists the core Raft consensus state that must survive crashes.
    Each node has exactly one row in this table.
    """
    __tablename__ = "raft_state"

    node_id = Column(String, primary_key=True, index=True, comment="The cluster node ID (e.g. node-1)")
    current_term = Column(BigInteger, nullable=False, default=0, comment="Latest term server has seen")
    voted_for = Column(String, nullable=True, comment="CandidateId that received vote in current term")

class RaftLogModel(Base):
    """
    Persists the Append-Only Replicated Log.
    Each node stores its own copy of the log here.
    """
    __tablename__ = "raft_log"

    node_id = Column(String, primary_key=True, comment="The cluster node ID")
    log_index = Column(BigInteger, primary_key=True, comment="The index of this entry in the Raft log")
    term = Column(BigInteger, nullable=False, comment="The term when this entry was received by the leader")
    command = Column(JSON, nullable=False, comment="The actual state machine command data")

