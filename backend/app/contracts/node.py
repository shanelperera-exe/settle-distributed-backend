from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NodeMetadata(BaseModel):
    """
    Metadata stored in ZooKeeper for each node.
    Stored as JSON inside the ephemeral znode.
    """
    node_id: str
    host: str
    port: int
    status: str = "starting"
    joined_at: datetime
    last_heartbeat: Optional[datetime] = None