from fastapi import APIRouter
from app.platform.distributed.clock.ntp_client import ntp_manager
from app.platform.distributed.clock.hlc import hlc_manager

router = APIRouter()

@router.get("/time")
async def get_current_time():
    """
    Returns the current Hybrid Logical Clock (HLC) timestamp and the 
    NTP-corrected physical time for this node.
    """
    pt_ms, logical = hlc_manager.now()
    
    return {
        "node_id": ntp_manager.get_health_status().get("node_id"), # Or from settings
        "physical_time_ms": pt_ms,
        "logical_counter": logical,
        "hlc_timestamp": f"{pt_ms}:{logical}"
    }

@router.get("/clock/health")
async def get_clock_health():
    """
    Returns the health of the physical clock synchronization (NTP).
    Used by load balancers or orchestrators to remove severely skewed nodes.
    """
    return ntp_manager.get_health_status()

@router.get("/sync/status")
async def get_sync_status():
    """
    Provides a comprehensive overview of the node's time synchronization state.
    """
    return {
        "ntp": ntp_manager.get_health_status(),
        "hlc": {
            "current": hlc_manager.get_current_packed()
        }
    }
