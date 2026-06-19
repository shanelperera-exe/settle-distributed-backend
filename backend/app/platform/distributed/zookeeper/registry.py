import logging
import json
from kazoo.client import KazooClient
from app.platform.distributed.zookeeper.client import ZKClientManager
from app.platform.core.config import settings

logger = logging.getLogger(__name__)

class ZKRegistry:
    """
    Handles registering this node in the ZooKeeper cluster.
    This fulfills the "Service Discovery" and "Failure Detection" requirements.
    """
    def __init__(self):
        self.zk: KazooClient = ZKClientManager.get_client()
        self.base_path = "/settle/nodes"
        self.node_id = settings.NODE_ID

    def register_node(self):
        """
        Creates an EPHEMERAL znode in ZooKeeper.
        
        Why Ephemeral?
        If this SETTLE node crashes, its TCP session to ZooKeeper terminates.
        ZooKeeper automatically deletes ephemeral nodes when the session dies.
        This provides instant, highly-available failure detection to the rest of the cluster
        without relying entirely on Raft heartbeat timeouts.
        """
        self.zk.ensure_path(self.base_path)
        
        node_path = f"{self.base_path}/{self.node_id}"
        
        metadata = {
            "node_id": self.node_id,
            "host": self.node_id,
            "port": settings.INTERNAL_PORT
        }
        
        data = json.dumps(metadata).encode('utf-8')
        
        # Clean up stale node if a rapid restart occurred
        if self.zk.exists(node_path):
            self.zk.delete(node_path)
            
        # Create the ephemeral node
        self.zk.create(node_path, data, ephemeral=True, makepath=True)
        logger.info(f"Registered ephemeral node in ZooKeeper at {node_path}")

    def get_active_nodes(self) -> list[str]:
        """Fetch the current list of active nodes from ZooKeeper."""
        self.zk.ensure_path(self.base_path)
        return self.zk.get_children(self.base_path)