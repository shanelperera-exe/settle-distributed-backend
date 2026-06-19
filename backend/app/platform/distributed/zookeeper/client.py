import logging
from kazoo.client import KazooClient
from kazoo.retry import KazooRetry
from app.platform.core.config import settings

logger = logging.getLogger(__name__)

class ZKClientManager:
    """
    Singleton manager for the ZooKeeper KazooClient.
    Ensures that the application uses a single, robust connection
    to the ZooKeeper cluster for service discovery and coordination.
    """
    _client: KazooClient = None

    @classmethod
    def get_client(cls) -> KazooClient:
        if cls._client is None:
            # Configure retries for fault tolerance
            # If the network drops temporarily, Kazoo will automatically backoff and retry
            retry_policy = KazooRetry(max_tries=5, delay=1.0, backoff=2.0)
            
            # Initialize connection to ZooKeeper cluster
            # settings.ZOOKEEPER_HOST is typically "zookeeper:2181"
            cls._client = KazooClient(
                hosts=settings.ZOOKEEPER_HOST,
                connection_retry=retry_policy,
                command_retry=retry_policy,
                timeout=10.0
            )
            cls._client.start()
            logger.info(f"Connected to ZooKeeper at {settings.ZOOKEEPER_HOST}")
        return cls._client

    @classmethod
    def close(cls):
        """Gracefully close the connection upon application shutdown."""
        if cls._client:
            cls._client.stop()
            cls._client.close()
            cls._client = None
            logger.info("Disconnected from ZooKeeper")