import logging
import asyncio
import socket
import time
import httpx
from typing import List, Dict, Optional
from app.platform.core.config import settings
from app.platform.distributed.raft.state import RaftState, NodeState
from app.platform.distributed.raft.log import RaftLog, LogEntry
from app.platform.distributed.raft.election import ElectionManager
from app.platform.distributed.zookeeper.registry import ZKRegistry
from app.platform.distributed.zookeeper.watcher import ZKWatcher
from app.platform.distributed.raft.persistence import save_raft_state
from app.platform.observability.metrics import (
    raft_leader_changes_total,
    raft_current_term,
    raft_commit_index,
    raft_replication_lag,
    raft_election_timeouts_total,
    raft_heartbeat_latency_seconds,
    raft_node_role,
    replication_queue_size,
    quorum_commit_latency_seconds,
    zookeeper_connected,
    zookeeper_node_count,
)

logger = logging.getLogger(__name__)


class RaftNode:
    """
    The Core Raft Consensus Engine.
    This runs as a background task within the FastAPI application lifecycle.

    Key design decisions:
    - The asyncio lock (self.lock) protects ONLY state mutations (term, role, log, indices).
    - The election timer check in _follower_loop does NOT hold the lock, preventing starvation
      of handle_append_entries (which must reset_timer() while holding the lock).
    - All paths that discover a higher term and step down MUST call reset_timer().
    - Peer hostnames are resolved to IPv4 at startup and on membership changes to avoid
      Docker DNS AAAA lookup hangs.
    """

    def __init__(self):
        self.node_id = settings.NODE_ID
        self.state = RaftState()
        self.log = RaftLog()
        self.election_manager = ElectionManager()

        # Zookeeper Integration
        self.zk_registry = ZKRegistry()
        self.zk_watcher = ZKWatcher()
        self.active_peers: List[str] = []
        self.peer_ips: Dict[str, str] = {}
        self.apply_callback = None

        # Asyncio primitives
        self.lock = asyncio.Lock()
        self.loop_task = None
        self.applier_task = None

        # Heartbeat interval
        self.heartbeat_interval = settings.RAFT_HEARTBEAT_INTERVAL_SEC

        # Single shared HTTP client: short timeout, no keepalive pooling (avoids socket hangs).
        limits = httpx.Limits(max_keepalive_connections=0, max_connections=100)
        self.http_client = httpx.AsyncClient(timeout=settings.RAFT_RPC_TIMEOUT_SEC, limits=limits)

    # -------------------------------------------------------------------------
    # Startup / Shutdown
    # -------------------------------------------------------------------------

    async def start(self):
        """Called on FastAPI startup."""
        logger.info(f"[{self.node_id}] Starting Raft Consensus Engine...")
        
        # Load persistent state and log
        await self.state.load(self.node_id)
        await self.log.load(self.node_id)
        
        # Initialize metrics with current state
        raft_current_term.labels(node_id=self.node_id).set(self.state.current_term)
        self._update_role_metric()
        
        self.zk_registry.register_node()
        # Fetch initial peers and resolve their IPs immediately (blocking, before async loop).
        initial_peers = self.zk_registry.get_active_nodes()
        self._resolve_and_update_peers(initial_peers)

        # Track ZooKeeper connectivity
        zookeeper_connected.labels(node_id=self.node_id).set(1)
        zookeeper_node_count.labels(node_id=self.node_id).set(len(initial_peers))

        self.zk_watcher.add_callback(self._on_peers_changed)
        self.zk_watcher.start_watching()

        self.loop_task = asyncio.create_task(self._raft_loop())
        self.applier_task = asyncio.create_task(self._applier_loop())

    def _update_role_metric(self):
        """Updates the raft_node_role gauge to reflect the current role."""
        for role in ("FOLLOWER", "CANDIDATE", "LEADER"):
            raft_node_role.labels(node_id=self.node_id, role=role).set(
                1 if self.state.role.name == role else 0
            )

    async def _update_term_and_vote(self, term: int, voted_for: Optional[str]):
        """Safely updates term and vote, and persists them."""
        self.state.current_term = term
        self.state.voted_for = voted_for
        await save_raft_state(self.node_id, term, voted_for)
        raft_current_term.labels(node_id=self.node_id).set(term)

    def _resolve_and_update_peers(self, peers: List[str]):
        """Resolve hostnames to IPv4 IPs synchronously and update peer lists."""
        self.active_peers = peers
        for p in peers:
            try:
                ip = socket.gethostbyname(p)
                self.peer_ips[p] = ip
            except Exception as e:
                logger.error(f"[{self.node_id}] DNS resolution failed for {p}: {e}")
        logger.info(f"[{self.node_id}] Peers updated: {self.active_peers} => IPs: {self.peer_ips}")

    def set_apply_callback(self, callback):
        self.apply_callback = callback

    # -------------------------------------------------------------------------
    # Application-layer API
    # -------------------------------------------------------------------------

    async def submit_command(self, command: dict) -> bool:
        """
        Called by the application layer to propose a new command.
        Returns True if successfully committed, False otherwise.
        """
        if self.state.role != NodeState.LEADER:
            logger.warning(f"[{self.node_id}] Cannot submit command — not leader.")
            return False

        async with self.lock:
            entry = LogEntry(term=self.state.current_term, command=command)
            await self.log.append(self.node_id, entry)
            target_index = self.log.get_last_log_index()
            # Track pending replication queue
            replication_queue_size.labels(node_id=self.node_id).set(
                self.log.get_last_log_index() - self.state.commit_index
            )

        logger.info(f"[{self.node_id}] Command submitted at index {target_index}. Waiting for quorum commit...")

        # Poll for commit — in production use asyncio.Event for efficiency.
        timeout = settings.RAFT_COMMIT_TIMEOUT_SEC
        commit_start = time.perf_counter()
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            if self.state.commit_index >= target_index:
                # Record quorum commit latency
                quorum_commit_latency_seconds.labels(node_id=self.node_id).observe(
                    time.perf_counter() - commit_start
                )
                logger.info(f"[{self.node_id}] Command at index {target_index} committed.")
                return True
            if self.state.role != NodeState.LEADER:
                logger.warning(f"[{self.node_id}] Lost leadership while waiting for commit at index {target_index}.")
                return False
            await asyncio.sleep(0.05)

        logger.error(f"[{self.node_id}] Timeout waiting for quorum commit at index {target_index}.")
        return False

    async def wait_for_linearizable_read(self) -> bool:
        """
        Implements the Raft ReadIndex protocol for strictly linearizable reads.
        1. Records the current commit_index.
        2. Sends heartbeats to a majority to prove it is still the leader.
        3. Waits for the state machine to apply logs up to commit_index.
        """
        if self.state.role != NodeState.LEADER:
            return False

        async with self.lock:
            read_index = self.state.commit_index
            current_term = self.state.current_term

        peers = [p for p in self.active_peers if p != self.node_id]
        if peers:
            tasks = []
            for peer in peers:
                tasks.append(self._send_append_entries(
                    peer, current_term, self.log.get_last_log_index(), self.log.get_last_log_term(), [], self.state.commit_index
                ))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = 1  # Self
            majority = (settings.RAFT_CLUSTER_SIZE // 2) + 1
            
            for resp in responses:
                if isinstance(resp, dict):
                    if resp.get("term", 0) > current_term:
                        return False # Higher term seen, we are no longer leader
                    if resp.get("success"):
                        success_count += 1
                        
            if success_count < majority:
                logger.warning(f"[{self.node_id}] Failed ReadIndex quorum ({success_count}/{majority}).")
                return False

        # Wait for state machine to catch up
        timeout = settings.RAFT_READ_INDEX_TIMEOUT_SEC
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            if self.state.last_applied >= read_index:
                return True
            if self.state.role != NodeState.LEADER:
                return False
            await asyncio.sleep(0.01)

        logger.error(f"[{self.node_id}] Timeout waiting for state machine in linearizable read.")
        return False

    # -------------------------------------------------------------------------
    # ZooKeeper Callback
    # -------------------------------------------------------------------------

    def _on_peers_changed(self, peers: List[str]):
        """Callback fired by ZooKeeper when cluster membership changes."""
        self._resolve_and_update_peers(peers)
        zookeeper_node_count.labels(node_id=self.node_id).set(len(peers))

    # -------------------------------------------------------------------------
    # Main Raft Loop
    # -------------------------------------------------------------------------

    async def _raft_loop(self):
        """Main state machine dispatcher."""
        while True:
            try:
                role = self.state.role
                if role == NodeState.FOLLOWER:
                    await self._follower_loop()
                elif role == NodeState.CANDIDATE:
                    await self._candidate_loop()
                elif role == NodeState.LEADER:
                    await self._leader_loop()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.node_id}] Raft loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _applier_loop(self):
        """Continuously applies committed log entries to the state machine."""
        while True:
            try:
                logs_to_apply = []
                async with self.lock:
                    while self.state.commit_index > self.state.last_applied:
                        self.state.last_applied += 1
                        idx = self.state.last_applied
                        if idx <= self.log.get_last_log_index():
                            entry = self.log.get_entry(idx)
                            if entry:
                                logs_to_apply.append((idx, entry.command))

                for idx, command in logs_to_apply:
                    if self.apply_callback and command.get("type") != "init":
                        logger.info(f"[{self.node_id}] Applying log index {idx} to state machine.")
                        try:
                            await self.apply_callback(command)
                        except Exception as e:
                            logger.error(f"[{self.node_id}] State machine apply failed at index {idx}: {e}")

                # Check for log compaction
                if logs_to_apply:
                    async with self.lock:
                        # Keep a buffer of 100 entries.
                        buffer_size = 100
                        if self.state.last_applied - self.log.last_included_index > buffer_size:
                            threshold = self.state.last_applied - buffer_size + 1
                            await self.log.compact(self.node_id, threshold)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.node_id}] Applier loop error: {e}", exc_info=True)

            await asyncio.sleep(0.01)

    # -------------------------------------------------------------------------
    # Follower Loop
    # -------------------------------------------------------------------------

    async def _follower_loop(self):
        """
        Waits for heartbeats. Calls election if timeout expires.

        CRITICAL: We do NOT hold self.lock while checking the timeout.
        The election_manager uses time.time() internally (lock-free reads).
        This prevents handle_append_entries from being starved of the lock
        when it needs to call reset_timer().
        """
        # Always reset timer when entering follower state (safety: prevents stale timeouts
        # from a previous LEADER or CANDIDATE state triggering an immediate election).
        self.election_manager.reset_timer()

        while self.state.role == NodeState.FOLLOWER:
            # Check timeout WITHOUT the lock — election_manager is safe to read lock-free.
            if self.election_manager.is_timeout_reached():
                async with self.lock:
                    # Re-check role inside lock to avoid TOCTOU race.
                    if self.state.role == NodeState.FOLLOWER:
                        logger.warning(f"[{self.node_id}] Election timeout! Transitioning to CANDIDATE.")
                        self.state.role = NodeState.CANDIDATE
                        raft_election_timeouts_total.labels(node_id=self.node_id).inc()
                        self._update_role_metric()
                        break
            await asyncio.sleep(0.01)

    # -------------------------------------------------------------------------
    # Candidate Loop
    # -------------------------------------------------------------------------

    async def _candidate_loop(self):
        """Runs one election round."""
        async with self.lock:
            await self._update_term_and_vote(self.state.current_term + 1, self.node_id)
            self.election_manager.reset_timer()
            current_term = self.state.current_term
            last_log_index = self.log.get_last_log_index()
            last_log_term = self.log.get_last_log_term()

        logger.info(f"[{self.node_id}] Starting election for term {current_term}.")

        votes = 1  # Vote for self
        peers = [p for p in self.active_peers if p != self.node_id]
        majority = (settings.RAFT_CLUSTER_SIZE // 2) + 1

        # Single-node cluster: immediately become leader.
        if settings.RAFT_CLUSTER_SIZE == 1:
            async with self.lock:
                self._become_leader()
            return

        # Request votes from all peers concurrently.
        tasks = [self._send_request_vote(p, current_term, last_log_index, last_log_term) for p in peers]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        async with self.lock:
            # If we stepped down during the await, abort.
            if self.state.role != NodeState.CANDIDATE or self.state.current_term != current_term:
                return

            for resp in responses:
                if isinstance(resp, dict):
                    resp_term = resp.get("term", 0)
                    if resp_term > self.state.current_term:
                        logger.info(f"[{self.node_id}] Higher term {resp_term} seen. Stepping down.")
                        await self._update_term_and_vote(resp_term, None)
                        self.state.role = NodeState.FOLLOWER
                        self.election_manager.reset_timer()  # MUST reset so we don't immediately re-elect
                        return
                    if resp.get("vote_granted"):
                        votes += 1

            if votes >= majority:
                logger.info(f"[{self.node_id}] Won election for term {current_term} with {votes} votes!")
                self._become_leader()
            else:
                logger.info(f"[{self.node_id}] Lost election for term {current_term} ({votes}/{majority} votes). Backing off.")
                # Back off to follower; _follower_loop will reset_timer on entry.
                self.state.role = NodeState.FOLLOWER

    def _become_leader(self):
        """Transitions to LEADER state and reinitializes volatile leader state."""
        self.state.role = NodeState.LEADER
        self.state.leader_id = self.node_id
        last_log_index = self.log.get_last_log_index()
        self.state.next_index = {p: last_log_index + 1 for p in self.active_peers if p != self.node_id}
        self.state.match_index = {p: 0 for p in self.active_peers if p != self.node_id}
        # Track leader transitions in Prometheus
        raft_leader_changes_total.labels(node_id=self.node_id).inc()
        self._update_role_metric()
        logger.info(f"[{self.node_id}] Became LEADER for term {self.state.current_term}.")

    # -------------------------------------------------------------------------
    # Leader Loop
    # -------------------------------------------------------------------------

    async def _leader_loop(self):
        """Sends heartbeats / AppendEntries to all followers on each tick."""
        while self.state.role == NodeState.LEADER:
            async with self.lock:
                current_term = self.state.current_term
                commit_index = self.state.commit_index

            peers = [p for p in self.active_peers if p != self.node_id]

            # Build per-peer RPC payloads and send concurrently (outside lock).
            tasks = []
            peer_entries_map = {}
            peer_send_times = {}
            for peer in peers:
                async with self.lock:
                    next_idx = self.state.next_index.get(peer, 1)
                    prev_log_index = next_idx - 1
                    prev_log_term = self.log.get_term_at(prev_log_index)
                    entries = self.log.get_entries_from(next_idx)
                    peer_entries_map[peer] = (prev_log_index, entries)

                peer_send_times[peer] = time.perf_counter()
                tasks.append(self._send_append_entries(
                    peer, current_term, prev_log_index, prev_log_term, entries, commit_index
                ))

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            async with self.lock:
                if self.state.role != NodeState.LEADER:
                    self._update_role_metric()
                    break

                for peer, resp in zip(peers, responses):
                    # Record heartbeat RTT for this peer
                    rtt = time.perf_counter() - peer_send_times.get(peer, time.perf_counter())
                    raft_heartbeat_latency_seconds.labels(
                        node_id=self.node_id, peer_id=peer
                    ).observe(rtt)

                    if not isinstance(resp, dict):
                        continue

                    resp_term = resp.get("term", 0)
                    if resp_term > self.state.current_term:
                        logger.warning(f"[{self.node_id}] Stale leader! Stepping down (saw term {resp_term}).")
                        await self._update_term_and_vote(resp_term, None)
                        self.state.role = NodeState.FOLLOWER
                        self._update_role_metric()
                        self.election_manager.reset_timer()  # MUST reset or follower immediately calls election
                        break

                    if resp.get("success"):
                        prev_log_index, entries = peer_entries_map[peer]
                        if entries:
                            self.state.match_index[peer] = prev_log_index + len(entries)
                            self.state.next_index[peer] = self.state.match_index[peer] + 1
                    else:
                        # Log inconsistency — back up next_index and retry.
                        if self.state.next_index.get(peer, 1) > 1:
                            self.state.next_index[peer] -= 1

                    # Track per-peer replication lag
                    lag = self.log.get_last_log_index() - self.state.match_index.get(peer, 0)
                    raft_replication_lag.labels(
                        node_id=self.node_id, peer_id=peer
                    ).set(lag)

                self._advance_commit_index()

            await asyncio.sleep(self.heartbeat_interval)

    def _advance_commit_index(self):
        """
        Advance commit_index to the highest N where a majority of nodes have
        matchIndex >= N AND log[N].term == currentTerm.
        Must be called while holding self.lock.
        """
        majority = (settings.RAFT_CLUSTER_SIZE // 2) + 1

        if settings.RAFT_CLUSTER_SIZE == 1:
            last = self.log.get_last_log_index()
            if last > self.state.commit_index:
                self.state.commit_index = last
                logger.info(f"[{self.node_id}] Single-node commit index -> {self.state.commit_index}.")
            return

        for N in range(self.log.get_last_log_index(), self.state.commit_index, -1):
            count = 1  # Self
            for match_idx in self.state.match_index.values():
                if match_idx >= N:
                    count += 1
            if count >= majority and self.log.get_term_at(N) == self.state.current_term:
                self.state.commit_index = N
                raft_commit_index.labels(node_id=self.node_id).set(N)
                replication_queue_size.labels(node_id=self.node_id).set(
                    self.log.get_last_log_index() - N
                )
                logger.info(f"[{self.node_id}] Quorum! commit_index -> {self.state.commit_index}.")
                break

    # -------------------------------------------------------------------------
    # RPC Handlers (called by FastAPI endpoints)
    # -------------------------------------------------------------------------

    async def handle_request_vote(self, term: int, candidate_id: str,
                                   last_log_index: int, last_log_term: int) -> dict:
        """Incoming RequestVote RPC."""
        async with self.lock:
            if term > self.state.current_term:
                await self._update_term_and_vote(term, None)
                self.state.role = NodeState.FOLLOWER
                self.election_manager.reset_timer()

            vote_granted = False
            if term == self.state.current_term:
                if self.state.voted_for in (None, candidate_id):
                    our_last_term = self.log.get_last_log_term()
                    our_last_idx = self.log.get_last_log_index()
                    if (last_log_term > our_last_term) or \
                       (last_log_term == our_last_term and last_log_index >= our_last_idx):
                        vote_granted = True
                        await self._update_term_and_vote(term, candidate_id)
                        self.election_manager.reset_timer()

            return {"term": self.state.current_term, "vote_granted": vote_granted}

    async def handle_append_entries(self, term: int, leader_id: str,
                                     prev_log_index: int, prev_log_term: int,
                                     entries: List[dict], leader_commit: int) -> dict:
        """Incoming AppendEntries RPC (heartbeat + log replication)."""
        async with self.lock:
            if term < self.state.current_term:
                return {"term": self.state.current_term, "success": False}

            # Valid leader contact — always reset timer and step down if needed.
            if term > self.state.current_term:
                await self._update_term_and_vote(term, None)
            self.state.role = NodeState.FOLLOWER
            self.state.leader_id = leader_id
            self.election_manager.reset_timer()
            self._update_role_metric()

            # Log Matching Property check.
            if prev_log_index > self.log.get_last_log_index() or \
               self.log.get_term_at(prev_log_index) != prev_log_term:
                return {"term": self.state.current_term, "success": False}

            # Truncate conflicting entries and append new ones.
            log_entries = [LogEntry.from_dict(e) for e in entries]
            if log_entries:
                await self.log.truncate_and_append(self.node_id, prev_log_index + 1, log_entries)

            # Update commit index.
            if leader_commit > self.state.commit_index:
                self.state.commit_index = min(leader_commit, self.log.get_last_log_index())

            return {"term": self.state.current_term, "success": True}

    # -------------------------------------------------------------------------
    # RPC Senders (use cached IPs to bypass Docker DNS hangs)
    # -------------------------------------------------------------------------

    async def _send_request_vote(self, peer_id: str, term: int,
                                  last_log_index: int, last_log_term: int) -> Optional[dict]:
        ip = self.peer_ips.get(peer_id, peer_id)
        url = f"http://{ip}:{settings.INTERNAL_PORT}/api/v1/raft/request_vote"
        payload = {
            "term": term,
            "candidate_id": self.node_id,
            "last_log_index": last_log_index,
            "last_log_term": last_log_term,
        }
        try:
            headers = {"X-Raft-Token": settings.RAFT_INTERNAL_TOKEN}
            resp = await self.http_client.post(url, json=payload, headers=headers)
            return resp.json()
        except Exception as e:
            logger.error(f"[{self.node_id}] Failed to request vote from {peer_id} ({ip}): {repr(e)}")
            return None

    async def _send_append_entries(self, peer_id: str, term: int,
                                    prev_log_index: int, prev_log_term: int,
                                    entries: list, leader_commit: int) -> Optional[dict]:
        ip = self.peer_ips.get(peer_id, peer_id)
        url = f"http://{ip}:{settings.INTERNAL_PORT}/api/v1/raft/append_entries"
        payload = {
            "term": term,
            "leader_id": self.node_id,
            "prev_log_index": prev_log_index,
            "prev_log_term": prev_log_term,
            "entries": entries,
            "leader_commit": leader_commit,
        }
        try:
            headers = {"X-Raft-Token": settings.RAFT_INTERNAL_TOKEN}
            resp = await self.http_client.post(url, json=payload, headers=headers)
            return resp.json()
        except Exception as e:
            logger.error(f"[{self.node_id}] Failed to send heartbeat to {peer_id} ({ip}): {repr(e)}")
            return None


# Global Raft Node Instance
raft_node = RaftNode()
