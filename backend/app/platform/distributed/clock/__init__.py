from app.platform.distributed.clock.ntp_client import ntp_manager
from app.platform.distributed.clock.hlc import hlc_manager
from app.platform.distributed.clock.reorder_buffer import reorder_manager

def start_clock_subsystem():
    ntp_manager.start()
    reorder_manager.start()

def stop_clock_subsystem():
    ntp_manager.stop()
    reorder_manager.stop()

__all__ = ["ntp_manager", "hlc_manager", "reorder_manager", "start_clock_subsystem", "stop_clock_subsystem"]
