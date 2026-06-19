import random
import time
import logging

logger = logging.getLogger(__name__)

class ElectionManager:
    """
    Manages the randomized election timeouts for a Raft node.
    Timeouts are increased for Python/HTTP environments to prevent false elections from jitter.
    """
    def __init__(self, min_timeout_ms: int = None, max_timeout_ms: int = None):
        from app.platform.core.config import settings
        min_ms = min_timeout_ms if min_timeout_ms is not None else settings.RAFT_MIN_ELECTION_TIMEOUT_MS
        max_ms = max_timeout_ms if max_timeout_ms is not None else settings.RAFT_MAX_ELECTION_TIMEOUT_MS
        self.min_timeout = min_ms / 1000.0
        self.max_timeout = max_ms / 1000.0
        self.last_heartbeat_time = time.time()
        self.current_timeout = self._generate_timeout()

    def _generate_timeout(self) -> float:
        """Returns a randomized timeout in seconds."""
        return random.uniform(self.min_timeout, self.max_timeout)

    def reset_timer(self):
        """
        Called whenever a valid heartbeat (AppendEntries) is received from a Leader,
        or when a node grants a vote to a Candidate.
        """
        self.last_heartbeat_time = time.time()
        self.current_timeout = self._generate_timeout()

    def is_timeout_reached(self) -> bool:
        """
        Checks if the randomized timeout has expired since the last heartbeat.
        If True, the node should transition to CANDIDATE and trigger an election.
        """
        return (time.time() - self.last_heartbeat_time) > self.current_timeout
