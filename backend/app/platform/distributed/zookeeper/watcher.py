import logging
from typing import List, Callable
from kazoo.client import KazooClient
from app.platform.distributed.zookeeper.client import ZKClientManager

logger = logging.getLogger(__name__)

class ZKWatcher:
    """
    Watches the ZooKeeper registry for changes in cluster membership.
    Notifies the Raft engine when nodes join or crash.
    """
    def __init__(self):
        self.zk: KazooClient = ZKClientManager.get_client()
        self.base_path = "/settle/nodes"
        self._callbacks: List[Callable[[List[str]], None]] = []
        
    def add_callback(self, callback: Callable[[List[str]], None]):
        """
        Register a callback function (typically from the Raft Node orchestrator)
        to be invoked whenever a node joins or leaves the cluster.
        """
        self._callbacks.append(callback)

    def start_watching(self):
        """
        Sets a Kazoo ChildrenWatch on the /settle/nodes directory.
        ZooKeeper immediately pushes updates to this client when the children list changes,
        providing real-time failure detection.
        """
        self.zk.ensure_path(self.base_path)
        
        @self.zk.ChildrenWatch(self.base_path)
        def watch_nodes(children):
            logger.info(f"[ZK Watcher] Cluster membership changed! Active nodes: {children}")
            for callback in self._callbacks:
                try:
                    callback(children)
                except Exception as e:
                    logger.error(f"[ZK Watcher] Error in callback: {e}")
