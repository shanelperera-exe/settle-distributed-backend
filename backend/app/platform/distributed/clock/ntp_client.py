import time
import ntplib
import threading
from typing import Optional, Dict, Any
from app.platform.core.config import settings
from app.platform.observability.logging import logger
from app.platform.observability.metrics import clock_skew_milliseconds, ntp_sync_offset_seconds

class NTPClient:
    """
    NTPClient handles physical clock synchronization.
    
    Distributed systems cannot rely purely on the local system clock due to 'clock skew' (clocks
    showing different times) and 'clock drift' (clocks running at different speeds).
    
    This client queries reliable NTP (Network Time Protocol) servers to calculate an 'offset' 
    between the local machine's time and the true global time.
    """
    
    def __init__(self):
        self.ntp_client = ntplib.NTPClient()
        self.servers = [s.strip() for s in settings.NTP_SERVERS.split(",")] if settings.NTP_SERVERS else []
        self.interval = settings.NTP_SYNC_INTERVAL_SECONDS
        
        self._offset: float = 0.0
        self._last_sync_time: Optional[float] = None
        self._is_running = False
        self._sync_thread = None
        self._lock = threading.Lock()
        
    def start(self):
        """Starts the background thread that periodically synchronizes with NTP servers."""
        if not self._is_running:
            self._is_running = True
            self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True, name="NTPSyncThread")
            self._sync_thread.start()
            logger.info("NTP Client background synchronization started.")
            
            # Block briefly to get the initial offset before returning
            self.force_sync()

    def stop(self):
        """Stops the background synchronization thread."""
        self._is_running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=2.0)
            logger.info("NTP Client stopped.")

    def _sync_loop(self):
        """Background loop to periodically query NTP servers."""
        while self._is_running:
            # Sleep in small increments to allow quick shutdown
            for _ in range(self.interval):
                if not self._is_running:
                    break
                time.sleep(1)
            
            if self._is_running:
                self.force_sync()

    def force_sync(self) -> bool:
        """
        Forces an immediate NTP synchronization.
        Iterates through configured servers until one succeeds.
        Returns True if synchronization was successful.
        """
        if not self.servers:
            logger.info("NTP_SERVERS is empty. Skipping NTP synchronization and falling back to host clock.")
            with self._lock:
                self._offset = 0.0
                self._last_sync_time = time.time()
            return True
            
        for server in self.servers:
            try:
                # Provide a short timeout to prevent blocking
                response = self.ntp_client.request(server, version=3, timeout=2.0)
                
                with self._lock:
                    self._offset = response.offset
                    self._last_sync_time = time.time()
                
                # Update Prometheus metrics
                skew_ms = abs(self._offset * 1000)
                clock_skew_milliseconds.labels(node_id=settings.NODE_ID).set(skew_ms)
                ntp_sync_offset_seconds.labels(node_id=settings.NODE_ID).set(self._offset)
                
                # Check for severe skew
                if skew_ms > settings.MAX_ALLOWED_SKEW_MS:
                    logger.warning(f"SEVERE CLOCK SKEW DETECTED: {skew_ms:.2f}ms offset from {server}")
                else:
                    logger.debug(f"NTP Sync successful. Server: {server}, Offset: {self._offset:.4f}s")
                    
                return True
            except Exception as e:
                logger.warning(f"NTP Sync failed for server {server}: {e}")
                
        logger.error("All NTP servers failed to synchronize.")
        return False

    def get_physical_time(self) -> float:
        """
        Returns the corrected physical time (time.time() + offset).
        This should be used instead of time.time() throughout the distributed system.
        """
        with self._lock:
            # We don't overwrite the system clock (which requires root/admin).
            # Instead, we apply the calculated offset in our application layer.
            return time.time() + self._offset

    def get_health_status(self) -> Dict[str, Any]:
        """Returns the health and status of the physical clock synchronization."""
        with self._lock:
            time_since_sync = (time.time() - self._last_sync_time) if self._last_sync_time else None
            
            return {
                "status": "healthy" if self._last_sync_time and (time_since_sync < self.interval * 2) else "degraded",
                "offset_seconds": self._offset,
                "skew_ms": self._offset * 1000,
                "last_sync_time_unix": self._last_sync_time,
                "time_since_last_sync_seconds": time_since_sync
            }

# Singleton instance
ntp_manager = NTPClient()
