import logging
from kazoo.client import KazooClient
from kazoo.recipe.election import Election
from app.platform.distributed.zookeeper.client import ZKClientManager
from app.platform.core.config import settings

logger = logging.getLogger(__name__)

class ZKClusterElection:
    """
    ZooKeeper Leader Election mechanism.
    
    NOTE: As per SETTLE Architecture requirements, RAFT is responsible for 
    the PRIMARY leader election for payment coordination and consensus.
    
    This ZooKeeper election recipe is provided as an infrastructure-level backup
    or to elect a "Cluster Bootstrapper" for tasks that do not require strict
    log consensus (e.g., triggering a global cluster snapshot, or external 
    health monitoring duties).
    """
    def __init__(self):
        self.zk: KazooClient = ZKClientManager.get_client()
        self.election_path = "/settle/election"
        self.node_id = settings.NODE_ID
        self.election = Election(self.zk, self.election_path, self.node_id)
        self.is_zk_leader = False

    def run_for_election(self):
        """
        Submits this node as a candidate for the ZooKeeper-based election.
        This runs in a background thread. When the node wins, the provided 
        function is executed.
        """
        def leader_func():
            logger.info(f"[{self.node_id}] WON ZooKeeper Cluster Election! Acting as ZK Leader.")
            self.is_zk_leader = True
            # Block indefinitely to maintain leadership until crash or shutdown
            try:
                import time
                while True:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"ZooKeeper Leader loop exited: {e}")
            finally:
                self.is_zk_leader = False

        # kazoo.recipe.election.run runs asynchronously via gevent/threading 
        # depending on handler, but blockingly for the current thread if called directly.
        # It's better to run it in a background thread.
        import threading
        t = threading.Thread(target=self.election.run, args=(leader_func,), daemon=True)
        t.start()
