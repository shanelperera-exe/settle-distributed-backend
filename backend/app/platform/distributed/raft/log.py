import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class LogEntry:
    def __init__(self, term: int, command: Dict[str, Any]):
        self.term = term
        self.command = command # The actual payment data
        
    def to_dict(self):
        return {"term": self.term, "command": self.command}
        
    @classmethod
    def from_dict(cls, data: dict):
        return cls(term=data["term"], command=data["command"])

from app.platform.distributed.raft.persistence import load_raft_log, append_raft_log_entry, truncate_and_append_raft_log, compact_raft_log

class RaftLog:
    """
    The Append-Only Replicated Log.
    Every state change in SETTLE (like a Payment) must first be written to this log.
    
    Log Matching Property:
    - If two entries in different logs have the same index and term, then they store the same command.
    - If two entries in different logs have the same index and term, then the logs are identical in all preceding entries.
    """
    def __init__(self):
        self.last_included_index = 0
        self.entries: List[LogEntry] = [LogEntry(term=0, command={"type": "init"})]

    async def load(self, node_id: str):
        """Loads persistent log entries from the database on startup."""
        logs = await load_raft_log(node_id)
        if logs:
            self.entries = [LogEntry(term=l["term"], command=l["command"]) for l in logs]
            self.last_included_index = logs[0]["index"]
            if self.last_included_index == 1:
                self.entries.insert(0, LogEntry(term=0, command={"type": "init"}))
                self.last_included_index = 0
            logger.info(f"Loaded {len(self.entries)} log entries from DB. Starting at index {self.last_included_index}")
        else:
            logger.info("No logs found in DB. Starting fresh.")

    def get_last_log_index(self) -> int:
        """Returns the highest index in the log."""
        return self.last_included_index + len(self.entries) - 1

    def get_last_log_term(self) -> int:
        """Returns the term of the highest index in the log."""
        if len(self.entries) > 0:
            return self.entries[-1].term
        return 0
        
    def get_term_at(self, index: int) -> int:
        """Safely gets the term at a specific index."""
        offset = index - self.last_included_index
        if 0 <= offset < len(self.entries):
            return self.entries[offset].term
        return 0
        
    def get_entry(self, index: int) -> Optional[LogEntry]:
        """Safely gets the entry at a specific index."""
        offset = index - self.last_included_index
        if 0 <= offset < len(self.entries):
            return self.entries[offset]
        return None

    def append_memory(self, entry: LogEntry) -> int:
        """Leader appends a new command from a client in memory only."""
        self.entries.append(entry)
        index = self.get_last_log_index()
        logger.info(f"Appended local log entry at index {index} for term {entry.term}")
        return index

    def truncate_and_append_memory(self, index: int, entries: List[LogEntry]) -> List[Tuple[int, int, dict]]:
        """
        Follower updates its log in memory and returns entries to be persisted.
        """
        if index <= self.last_included_index:
            # We are asked to truncate logs that are already compacted.
            diff = self.last_included_index - index + 1
            if diff >= len(entries):
                return []
            index += diff
            entries = entries[diff:]
            
        offset = index - self.last_included_index
        if offset <= len(self.entries):
            logger.warning(f"Truncating log at index {index}. Discarding stale logs.")
            self.entries = self.entries[:offset]
            
        for entry in entries:
            self.entries.append(entry)
            
        db_entries = []
        if len(entries) > 0:
            for i, entry in enumerate(entries):
                db_entries.append((index + i, entry.term, entry.command))
        logger.info(f"Replicated {len(entries)} logs. Current last index: {self.get_last_log_index()}")
        return db_entries

    def get_entries_from(self, next_index: int) -> List[dict]:
        """Returns serialized entries starting from the requested index (used by Leader to sync followers)."""
        offset = next_index - self.last_included_index
        if offset < 1:
            logger.warning(f"Follower requested next_index {next_index} but we compacted up to {self.last_included_index}. InstallSnapshot omitted.")
            return []
        if offset > len(self.entries) - 1:
            return []
        return [entry.to_dict() for entry in self.entries[offset:]]

    async def compact(self, node_id: str, threshold_index: int):
        """Compacts the log by removing entries before the threshold_index - 1."""
        keep_from_index = threshold_index - 1
        offset = keep_from_index - self.last_included_index
        if offset > 0 and offset < len(self.entries):
            self.entries = self.entries[offset:]
            self.last_included_index = keep_from_index
            await compact_raft_log(node_id, keep_from_index)
            logger.info(f"Compacted in-memory logs up to {keep_from_index-1}. Remaining logs: {len(self.entries)}")
