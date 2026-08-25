"""
Prometheus Metrics Registry for the SETTLE Distributed Payment System.

This module defines ALL application-level metrics in a single, centralized location.
Every metric is registered on a shared CollectorRegistry to avoid duplicate
registration errors when the module is imported from multiple places.

Metric Types (Prometheus Data Model):
─────────────────────────────────────
  Counter   – Monotonically increasing value. Only goes up (or resets to 0 on restart).
              Use for: total requests, total errors, total payments.
  
  Gauge     – Can go up or down. Represents a current snapshot.
              Use for: in-flight requests, current term, queue depth, connection state.
  
  Histogram – Samples observations and counts them in configurable buckets.
              Automatically provides _sum, _count, and _bucket time series.
              Use for: latency distributions, processing durations.
  
  Summary   – Similar to histogram but calculates quantiles client-side.
              Generally prefer histograms for aggregation across nodes.

Label Design:
─────────────
  Every metric includes a `node_id` label so that Prometheus queries can filter
  or aggregate across the 5-node SETTLE cluster. Additional labels are added
  only where the cardinality is bounded (e.g., `status` ∈ {success, failure},
  `role` ∈ {FOLLOWER, CANDIDATE, LEADER}).

  WARNING: Unbounded labels (e.g., user_id, payment_id) must NEVER be used as
  metric labels — they cause cardinality explosion and OOM in Prometheus.
"""

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# ── Shared Registry ──────────────────────────────────────────────────────────
# Using a custom registry instead of the default avoids conflicts with
# prometheus_client's built-in process/platform collectors that may not be
# relevant in a containerized environment.
REGISTRY = CollectorRegistry(auto_describe=True)

# Register process metrics to our custom registry to get CPU and memory stats
from prometheus_client import ProcessCollector
ProcessCollector(registry=REGISTRY)

# ── Histogram Bucket Definitions ─────────────────────────────────────────────
# Tuned for payment processing and distributed consensus latencies.
# Sub-10ms buckets capture fast Raft heartbeats; 10s+ captures slow Stripe calls.
LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENT METRICS
# ═══════════════════════════════════════════════════════════════════════════════

payments_processed_total = Counter(
    "payments_processed_total",
    "Total number of payments processed (success or failure)",
    labelnames=["node_id", "status"],
    registry=REGISTRY,
)

payments_failed_total = Counter(
    "payments_failed_total",
    "Total number of failed payments by failure reason",
    labelnames=["node_id", "reason"],
    registry=REGISTRY,
)

payments_pending = Gauge(
    "payments_pending",
    "Number of payments currently in PENDING state",
    labelnames=["node_id"],
    registry=REGISTRY,
)

payment_processing_duration_seconds = Histogram(
    "payment_processing_duration_seconds",
    "Duration of end-to-end payment processing in seconds",
    labelnames=["node_id", "stage"],
    buckets=LATENCY_BUCKETS,
    registry=REGISTRY,
)

stripe_api_latency_seconds = Histogram(
    "stripe_api_latency_seconds",
    "Duration of Stripe API calls in seconds",
    labelnames=["node_id", "operation"],
    buckets=LATENCY_BUCKETS,
    registry=REGISTRY,
)

webhook_processing_duration_seconds = Histogram(
    "webhook_processing_duration_seconds",
    "Duration of Stripe webhook processing in seconds",
    labelnames=["node_id", "event_type"],
    buckets=LATENCY_BUCKETS,
    registry=REGISTRY,
)


# ═══════════════════════════════════════════════════════════════════════════════
# RAFT CONSENSUS METRICS
# ═══════════════════════════════════════════════════════════════════════════════

raft_leader_changes_total = Counter(
    "raft_leader_changes_total",
    "Total number of leader election transitions",
    labelnames=["node_id"],
    registry=REGISTRY,
)

raft_current_term = Gauge(
    "raft_current_term",
    "Current Raft consensus term",
    labelnames=["node_id"],
    registry=REGISTRY,
)

raft_commit_index = Gauge(
    "raft_commit_index",
    "Current Raft commit index (highest log index known to be committed)",
    labelnames=["node_id"],
    registry=REGISTRY,
)

raft_replication_lag = Gauge(
    "raft_replication_lag",
    "Replication lag between leader and follower (log index difference)",
    labelnames=["node_id", "peer_id"],
    registry=REGISTRY,
)

raft_election_timeouts_total = Counter(
    "raft_election_timeouts_total",
    "Total number of election timeouts triggered",
    labelnames=["node_id"],
    registry=REGISTRY,
)

raft_heartbeat_latency_seconds = Histogram(
    "raft_heartbeat_latency_seconds",
    "Round-trip time for leader heartbeats to each peer",
    labelnames=["node_id", "peer_id"],
    buckets=LATENCY_BUCKETS,
    registry=REGISTRY,
)

raft_node_role = Gauge(
    "raft_node_role",
    "Current Raft role of this node (1 = active for the labeled role)",
    labelnames=["node_id", "role"],
    registry=REGISTRY,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ZOOKEEPER METRICS
# ═══════════════════════════════════════════════════════════════════════════════

zookeeper_connected = Gauge(
    "zookeeper_connected",
    "Whether this node is connected to ZooKeeper (1 = connected, 0 = disconnected)",
    labelnames=["node_id"],
    registry=REGISTRY,
)

zookeeper_session_state = Gauge(
    "zookeeper_session_state",
    "ZooKeeper session state (1 = active for the labeled state)",
    labelnames=["node_id", "state"],
    registry=REGISTRY,
)

zookeeper_node_count = Gauge(
    "zookeeper_node_count",
    "Number of registered nodes in ZooKeeper cluster",
    labelnames=["node_id"],
    registry=REGISTRY,
)


# ═══════════════════════════════════════════════════════════════════════════════
# REPLICATION METRICS
# ═══════════════════════════════════════════════════════════════════════════════

replication_queue_size = Gauge(
    "replication_queue_size",
    "Number of log entries pending replication",
    labelnames=["node_id"],
    registry=REGISTRY,
)

replication_lag_seconds = Gauge(
    "replication_lag_seconds",
    "Estimated replication lag in seconds",
    labelnames=["node_id"],
    registry=REGISTRY,
)

quorum_commit_latency_seconds = Histogram(
    "quorum_commit_latency_seconds",
    "Time taken to achieve quorum commit for a log entry",
    labelnames=["node_id"],
    buckets=LATENCY_BUCKETS,
    registry=REGISTRY,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TIME SYNCHRONIZATION METRICS
# ═══════════════════════════════════════════════════════════════════════════════

clock_skew_milliseconds = Gauge(
    "clock_skew_milliseconds",
    "Current clock skew between this node and NTP reference in milliseconds",
    labelnames=["node_id"],
    registry=REGISTRY,
)

ntp_sync_offset_seconds = Gauge(
    "ntp_sync_offset_seconds",
    "NTP synchronization offset in seconds",
    labelnames=["node_id"],
    registry=REGISTRY,
)

reorder_buffer_size = Gauge(
    "reorder_buffer_size",
    "Number of log entries currently held in the reorder buffer",
    labelnames=["node_id"],
    registry=REGISTRY,
)


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP / REQUEST METRICS
# ═══════════════════════════════════════════════════════════════════════════════

http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests received",
    labelnames=["node_id", "method", "endpoint", "status"],
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Duration of HTTP request processing in seconds",
    labelnames=["node_id", "method", "endpoint"],
    buckets=LATENCY_BUCKETS,
    registry=REGISTRY,
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    labelnames=["node_id"],
    registry=REGISTRY,
)
