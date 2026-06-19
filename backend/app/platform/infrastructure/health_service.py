# health_service.py - Service class responsible for managing the health and status of nodes in the cluster.

from datetime import datetime, timezone

from app.platform.core.config import get_settings
from app.contracts.node import NodeMetadata

class HealthService:
    """Service class responsible for managing the health and status of nodes in the cluster."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.started_at = datetime.now(timezone.utc)

    def build_node_metadata(self, status: str = "ACTIVE") -> NodeMetadata:
        """Constructs a NodeMetadata instance representing the current node's state."""
        
        now = datetime.now(timezone.utc)

        return NodeMetadata(
            node_id=self.settings.NODE_ID,
            node_name=self.settings.NODE_NAME,
            host=self.settings.NODE_HOST,
            port=self.settings.NODE_PORT,
            status=status,
            started_at=self.started_at,
            version=self.settings.APP_VERSION,
            last_seen=now,
        )