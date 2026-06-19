from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.platform.core.config import settings
from app.platform.observability.logging import logger
from app.platform.infrastructure.db.session import get_db
from app.platform.distributed.raft.node import raft_node
from app.platform.distributed.zookeeper.client import ZKClientManager

router = APIRouter()

@router.get("/live")
def liveness_check():
    """
    Kubernetes Liveness Probe.
    Returns 200 as long as the application process is running and can respond to HTTP.
    If this fails, the container orchestrator should restart the container.
    """
    return {"status": "alive", "node_id": settings.NODE_ID}

@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes Readiness Probe.
    Checks if the node is fully initialized, connected to backing services (ZK, DB),
    and ready to process traffic. If this fails, the orchestrator should remove this node
    from load balancer rotation.
    """
    # 1. Check Database Connectivity
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Readiness check failed: DB unavailable - {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")

    # 2. Check ZooKeeper Connectivity and Registration
    zk = ZKClientManager.get_client()
    if not zk or not zk.connected:
        raise HTTPException(status_code=503, detail="ZooKeeper disconnected")
    
    if settings.NODE_ID not in raft_node.active_peers:
        # Give it a tiny bit of leniency during fast boots
        logger.warning("Node not yet seen in ZK active peers list")

    return {
        "status": "ready",
        "node_id": settings.NODE_ID,
        "role": raft_node.state.role.name
    }

@router.get("/cluster")
def cluster_status():
    """
    Exposes the current state of the distributed cluster from the perspective of this node.
    """
    zk = ZKClientManager.get_client()
    zk_connected = bool(zk and zk.connected)
    
    return {
        "this_node": {
            "id": settings.NODE_ID,
            "role": raft_node.state.role.name,
            "zk_connected": zk_connected
        },
        "healthy_node_count": len(raft_node.active_peers),
        "cluster_members": raft_node.active_peers
    }