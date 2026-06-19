import threading
import time
import json
import uuid
from typing import Dict, Any, List
from collections import defaultdict
from app.platform.core.config import settings
from app.platform.observability.logging import logger
from app.platform.observability.metrics import reorder_buffer_size as reorder_buffer_size_metric

class ReorderBuffer:
    """
    Reorder Buffer handles out-of-order logs.
    
    In a distributed system, network latency causes logs and events to arrive out of sequence.
    Example: Node A creates a payment at 12:00:01, but the replication request to Node B
    arrives and is logged before the original creation log is processed due to varying network routes.
    
    The Reorder Buffer temporarily stores logs, sorts them strictly by their HLC timestamp,
    and flushes them out after a configurable sliding window, reconstructing the exact 
    causal timeline of events.
    """
    
    def __init__(self):
        self.buffer: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self.flush_interval_seconds = settings.REORDER_BUFFER_FLUSH_INTERVAL_MS / 1000.0
        
        self._is_running = False
        self._flush_thread = None
        
    def start(self):
        if not self._is_running:
            self._is_running = True
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True, name="ReorderBufferThread")
            self._flush_thread.start()
            logger.info("Reorder Buffer started.")

    def stop(self):
        self._is_running = False
        if self._flush_thread:
            self._flush_thread.join(timeout=2.0)
            # Flush whatever is left
            self._flush_buffer(force=True)
            logger.info("Reorder Buffer stopped.")

    def add_log(self, log_entry: Dict[str, Any]):
        """
        Adds a log entry to the buffer.
        log_entry MUST contain an 'hlc_timestamp' field (e.g., '1716800000000:4')
        and an 'ingest_time' field representing local reception time.
        """
        # We add an ingestion timestamp to know when it entered the buffer
        log_entry["_ingest_time"] = time.time()
        
        with self._lock:
            self.buffer.append(log_entry)
            reorder_buffer_size_metric.labels(node_id=settings.NODE_ID).set(len(self.buffer))

    def _flush_loop(self):
        """Periodically flushes logs that are older than the flush interval."""
        while self._is_running:
            time.sleep(1)
            self._flush_buffer(force=False)
            
    def _flush_buffer(self, force: bool = False):
        current_time = time.time()
        to_flush = []
        
        with self._lock:
            retained = []
            for entry in self.buffer:
                # If forced, or if it has been in the buffer longer than the interval
                if force or (current_time - entry.get("_ingest_time", 0)) > self.flush_interval_seconds:
                    to_flush.append(entry)
                else:
                    retained.append(entry)
            self.buffer = retained
            reorder_buffer_size_metric.labels(node_id=settings.NODE_ID).set(len(self.buffer))
            
        if not to_flush:
            return
            
        # Sort the flushed entries strictly by their HLC Timestamp
        # HLC format is "<physical_ms>:<logical_counter>".
        # We can split and convert to int tuples for perfect chronological sorting.
        def hlc_key(entry):
            hlc_str = entry.get("hlc_timestamp", "0:0")
            try:
                pt, count = hlc_str.split(":")
                return (int(pt), int(count))
            except:
                return (0, 0)
                
        to_flush.sort(key=hlc_key)
        
        # In a real production system, this is where you would send the sorted logs 
        # to Elasticsearch, Datadog, Splunk, etc. We will use the structured Python logger.
        for entry in to_flush:
            # Remove internal tracking field before output
            entry.pop("_ingest_time", None)
            # Emit the pre-formatted structured line directly through the sink logger
            import logging as _logging
            _logging.getLogger("structured_logger").info(json.dumps(entry, ensure_ascii=False))

# Singleton instance
reorder_manager = ReorderBuffer()
