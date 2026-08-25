import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

RULE_CATEGORIES = {
    "settle_infrastructure": {
        "LeaderNodeDown": {
            "expr": 'sum(raft_node_role{role="LEADER"}) == 0',
            "for": "30s",
            "severity": "critical",
            "team": "sre",
            "description": "No node reports role=LEADER. The cluster cannot process payments until a new leader is elected.",
            "runbook_url": "https://docs.settle.internal/runbooks/leader-failure",
            "summary": "No Raft leader detected in the SETTLE cluster"
        },
        "NodeOffline": {
            "expr": 'up{job="settle_node"} == 0',
            "for": "15s",
            "severity": "warning",
            "team": "sre",
            "description": "A node has dropped from the cluster and is no longer responding to ZooKeeper heartbeats.",
            "runbook_url": "https://docs.settle.internal/runbooks/node-offline",
            "summary": "Settle node is unreachable"
        },
        "QuorumFailure": {
            "expr": 'count(up{job="settle_node"} == 1) < 3',
            "for": "10s",
            "severity": "critical",
            "team": "sre",
            "description": "Active nodes have fallen below the Raft quorum size (3). Cluster is completely halted.",
            "runbook_url": "https://docs.settle.internal/runbooks/quorum-recovery",
            "summary": "Raft quorum lost"
        },
        "ZooKeeperDisconnected": {
            "expr": 'settle_zk_connected == 0',
            "for": "30s",
            "severity": "critical",
            "team": "sre",
            "description": "Backend nodes have lost connection to the ZooKeeper ensemble.",
            "runbook_url": "https://docs.settle.internal/runbooks/zookeeper-down",
            "summary": "ZooKeeper split brain or failure"
        },
        "HighCPUUsage": {
            "expr": 'rate(process_cpu_seconds_total[5m]) > 0.85',
            "for": "2m",
            "severity": "warning",
            "team": "sre",
            "description": "Settle backend process is consuming excessive CPU.",
            "runbook_url": "https://docs.settle.internal/runbooks/cpu-spike",
            "summary": "High CPU utilization detected"
        },
        "MemoryExhaustion": {
            "expr": 'process_resident_memory_bytes / 1024 / 1024 > 1024',
            "for": "5m",
            "severity": "critical",
            "team": "sre",
            "description": "Settle backend is approaching its OOM boundary.",
            "runbook_url": "https://docs.settle.internal/runbooks/oom-prevention",
            "summary": "Node memory exhaustion imminent"
        },
        "NetworkBandwidthSaturation": {
            "expr": 'rate(node_network_receive_bytes_total[5m]) > 1000000000',
            "for": "5m",
            "severity": "warning",
            "team": "sre",
            "description": "Network traffic is saturating the node's NIC.",
            "runbook_url": "https://docs.settle.internal/runbooks/network-saturation",
            "summary": "Network bandwidth saturated"
        }
    },
    "settle_payments": {
        "PaymentFailureSpike": {
            "expr": 'rate(settle_payment_failures_total[5m]) > 10',
            "for": "1m",
            "severity": "critical",
            "team": "payments",
            "description": "Spike in payment transaction failures detected at the consensus layer.",
            "runbook_url": "https://docs.settle.internal/runbooks/payment-failures",
            "summary": "Payment processing degradation"
        },
        "StripeHighLatency": {
            "expr": 'histogram_quantile(0.95, rate(stripe_api_latency_seconds_bucket[5m])) > 2.0',
            "for": "5m",
            "severity": "warning",
            "team": "payments",
            "description": "Calls to Stripe API are experiencing high latency.",
            "runbook_url": "https://docs.settle.internal/runbooks/stripe-latency",
            "summary": "Stripe API latency spike"
        }
    },
    "settle_replication": {
        "HighReplicationLag": {
            "expr": 'settle_raft_commit_index - settle_raft_apply_index > 500',
            "for": "30s",
            "severity": "warning",
            "team": "database",
            "description": "Follower nodes are falling behind the Leader's state machine.",
            "runbook_url": "https://docs.settle.internal/runbooks/replication-lag",
            "summary": "Follower replication lag"
        },
        "ExcessiveElectionTimeouts": {
            "expr": 'rate(settle_raft_election_timeouts_total[5m]) > 5',
            "for": "2m",
            "severity": "critical",
            "team": "database",
            "description": "Raft cluster is struggling to maintain a stable leader.",
            "runbook_url": "https://docs.settle.internal/runbooks/election-storm",
            "summary": "Raft election instability"
        }
    }
}

class AlertManager:
    def __init__(self):
        self.queues: List[asyncio.Queue] = []
        
        # Initialize state with all rules inactive
        self.state: Dict[str, Dict[str, Any]] = {}
        for category, rules in RULE_CATEGORIES.items():
            self.state[category] = {}
            for rule in rules:
                self.state[category][rule] = {
                    "active_count": 0,
                    "instances": {} # instance_id -> details
                }
        self.total_alerts_fired = 0

    def set_alert_state(self, category: str, rule: str, instance_id: str, active: bool, message: str = "", severity: str = "error", sync: bool = True, labels: Dict[str, str] = None):
        if category not in self.state or rule not in self.state[category]:
            logger.warning(f"Unknown alert rule: {category}.{rule}")
            return

        rule_state = self.state[category][rule]
        
        if active:
            # Add or update instance
            if instance_id not in rule_state["instances"]:
                logger.info(f"Alert FIRING: {rule} for {instance_id}")
                self.total_alerts_fired += 1
            rule_state["instances"][instance_id] = {
                "id": str(uuid.uuid4()),
                "message": message,
                "severity": severity,
                "labels": labels or {},
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        else:
            # Resolve instance
            if instance_id in rule_state["instances"]:
                logger.info(f"Alert RESOLVED: {rule} for {instance_id}")
                del rule_state["instances"][instance_id]
                
        rule_state["active_count"] = len(rule_state["instances"])
        
        self._broadcast_state()

        if sync:
            from app.platform.distributed.raft.node import raft_node
            from app.platform.core.config import settings
            import httpx

            async def _broadcast():
                payload = {
                    "category": category,
                    "rule": rule,
                    "instance_id": instance_id,
                    "active": active,
                    "message": message,
                    "severity": severity
                }
                tasks = []
                async with httpx.AsyncClient(timeout=2.0) as client:
                    for node_id, ip in raft_node.peer_ips.items():
                        if node_id != settings.NODE_ID:
                            url = f"http://{ip}:{settings.INTERNAL_PORT}/api/v1/alerts/internal/sync"
                            tasks.append(client.post(url, json=payload))
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
            
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_broadcast())
            except RuntimeError:
                pass
        
    def _broadcast_state(self):
        # Notify all connected SSE clients with the entire state
        for q in self.queues:
            try:
                q.put_nowait(self.get_full_state())
            except asyncio.QueueFull:
                pass

    def get_full_state(self) -> Dict[str, Any]:
        """Format state for API response"""
        formatted = []
        for category, rules in self.state.items():
            cat_obj = {
                "category": category,
                "rules": []
            }
            for rule_name, rule_data in rules.items():
                cat_obj["rules"].append({
                    "name": rule_name,
                    "active_count": rule_data["active_count"],
                    "instances": list(rule_data["instances"].values()),
                    "metadata": RULE_CATEGORIES.get(category, {}).get(rule_name, {})
                })
            formatted.append(cat_obj)
            
        return {"categories": formatted, "total_alerts_fired": self.total_alerts_fired}

    async def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=100)
        # Send initial state
        q.put_nowait(self.get_full_state())
        self.queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self.queues:
            self.queues.remove(q)

alert_manager = AlertManager()
