import threading
import time
from typing import Tuple

from app.platform.distributed.clock.ntp_client import ntp_manager

class HybridLogicalClock:
    """
    Hybrid Logical Clock (HLC).
    
    Pure physical clocks suffer from skew and drift, making it impossible to guarantee 
    event ordering (causality) across distributed nodes. Pure logical clocks (Lamport) 
    guarantee causality but lose all connection to real physical time, making debugging 
    and log correlation impossible.
    
    HLC combines both:
    1. A physical timestamp (from our NTP-corrected physical clock).
    2. A logical counter (for events that happen in the same physical millisecond).
    
    Format: <physical_timestamp_ms>:<logical_counter>
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        
        # We store physical time in integer milliseconds
        self._last_physical_time_ms: int = 0
        self._logical_counter: int = 0
        
    def _get_current_physical_time_ms(self) -> int:
        """Get the NTP-corrected physical time in milliseconds."""
        return int(ntp_manager.get_physical_time() * 1000)
        
    def now(self) -> Tuple[int, int]:
        """
        Generates a new HLC timestamp for a local event.
        Guarantees that the timestamp is monotonically increasing.
        """
        with self._lock:
            current_pt_ms = self._get_current_physical_time_ms()
            
            if current_pt_ms > self._last_physical_time_ms:
                # Physical time has moved forward. Reset the counter.
                self._last_physical_time_ms = current_pt_ms
                self._logical_counter = 0
            else:
                # Physical time has NOT moved forward (or went backwards due to skew).
                # We MUST preserve monotonicity by freezing the physical time and incrementing the logical counter.
                self._logical_counter += 1
                
            return (self._last_physical_time_ms, self._logical_counter)
            
    def update(self, remote_physical_ms: int, remote_logical_counter: int) -> Tuple[int, int]:
        """
        Updates the local HLC based on a timestamp received from a remote node.
        This ensures causality: if Node A sends a message to Node B, Node B's clock
        will strictly advance past Node A's clock.
        """
        with self._lock:
            current_pt_ms = self._get_current_physical_time_ms()
            
            # The new physical time is the maximum of:
            # 1. Local wall clock
            # 2. Local HLC state
            # 3. Remote HLC state
            max_pt_ms = max(current_pt_ms, self._last_physical_time_ms, remote_physical_ms)
            
            if max_pt_ms == current_pt_ms and max_pt_ms > self._last_physical_time_ms and max_pt_ms > remote_physical_ms:
                # Local wall clock is the highest
                self._logical_counter = 0
            elif max_pt_ms == self._last_physical_time_ms and max_pt_ms == remote_physical_ms:
                # Both local and remote are at the exact same physical millisecond.
                # Take the highest counter and increment.
                self._logical_counter = max(self._logical_counter, remote_logical_counter) + 1
            elif max_pt_ms == self._last_physical_time_ms:
                # Local HLC physical time is highest
                self._logical_counter += 1
            else:
                # Remote HLC physical time is highest
                self._logical_counter = remote_logical_counter + 1
                
            self._last_physical_time_ms = max_pt_ms
            
            return (self._last_physical_time_ms, self._logical_counter)

    def pack(self, pt_ms: int, counter: int) -> str:
        """Packs a tuple into a string representation: '1716800000000:4'"""
        return f"{pt_ms}:{counter}"
        
    def unpack(self, hlc_str: str) -> Tuple[int, int]:
        """Unpacks a string representation into a tuple."""
        try:
            pt, count = hlc_str.split(":")
            return (int(pt), int(count))
        except (ValueError, AttributeError):
            # If invalid or missing, fallback to current local time
            return (self._get_current_physical_time_ms(), 0)
            
    def get_current_packed(self) -> str:
        """Gets the current HLC timestamp packed as a string."""
        return self.pack(*self.now())

# Singleton instance
hlc_manager = HybridLogicalClock()
