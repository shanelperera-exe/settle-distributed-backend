import os
import time
import asyncio
import httpx
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.platform.core.config import settings
from app.platform.observability.logging import logger
from app.platform.observability.alerts import alert_manager
from app.platform.distributed.raft.node import raft_node
from app.platform.distributed.raft.state import NodeState

router = APIRouter()

class ChaosInjectionRequest(BaseModel):
    target_node: str
    scenario: str

def kill_node_task():
    logger.warning(f"[{settings.NODE_ID}] Simulating Node Death. Stopping ZK and sleeping...")
    try:
        raft_node.zk_registry.zk.stop()
    except Exception as e:
        logger.error(f"Error stopping ZK: {e}")
    time.sleep(15)
    os._exit(1)

async def cpu_spike_task():
    logger.warning(f"[{settings.NODE_ID}] Starting CPU spike...")
    end_time = time.time() + 15
    while time.time() < end_time:
        _ = 2 ** 1000
    logger.warning(f"[{settings.NODE_ID}] Finished CPU spike.")

async def mem_spike_task():
    logger.warning(f"[{settings.NODE_ID}] Starting Memory spike...")
    try:
        # Allocate roughly a few hundred MBs
        dummy = ["A" * 1024 * 1024 for _ in range(500)]
        await asyncio.sleep(15)
        del dummy
    except MemoryError:
        pass
    logger.warning(f"[{settings.NODE_ID}] Finished Memory spike.")

async def network_partition_task():
    logger.warning(f"[{settings.NODE_ID}] Simulating Network Partition for 15s...")
    raft_node._fault_network_partition = True
    await asyncio.sleep(15)
    raft_node._fault_network_partition = False
    logger.warning(f"[{settings.NODE_ID}] Network Partition resolved.")

@router.post("/inject")
async def inject_chaos(request: ChaosInjectionRequest, background_tasks: BackgroundTasks):
    logger.info(f"Received chaos injection request for {request.target_node}: {request.scenario}")

    if request.target_node != settings.NODE_ID:
        # Forward to target node
        ip = raft_node.peer_ips.get(request.target_node)
        if not ip:
            # We don't know the IP, just fail or mock
            logger.warning(f"Unknown target_node {request.target_node} for chaos injection")
            return {"status": "mocked", "message": f"Target node {request.target_node} IP unknown. Logged only."}

        url = f"http://{ip}:{settings.INTERNAL_PORT}/api/v1/chaos/inject"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=request.model_dump())
                return resp.json()
            except httpx.RequestError as e:
                logger.error(f"Failed to forward chaos request to {request.target_node}: {e}")
                raise HTTPException(status_code=503, detail="Service Unavailable")

    # Execution on the target node
    scenario = request.scenario
    logger.warning(f"[{settings.NODE_ID}] EXECUTING CHAOS SCENARIO: {scenario}")

    if scenario == "KILL_NODE":
        background_tasks.add_task(kill_node_task)
        return {"status": "success", "message": f"Node {settings.NODE_ID} will simulate extended death and crash."}
    
    elif scenario == "GRACEFUL_RESTART":
        background_tasks.add_task(os._exit, 0)
        return {"status": "success", "message": f"Node {settings.NODE_ID} will restart gracefully."}

    elif scenario == "CPU_SPIKE":
        background_tasks.add_task(cpu_spike_task)
        return {"status": "success", "message": f"Node {settings.NODE_ID} CPU spiking for 15s."}

    elif scenario == "MEMORY_SPIKE":
        background_tasks.add_task(mem_spike_task)
        return {"status": "success", "message": f"Node {settings.NODE_ID} Memory spiking for 15s."}

    elif scenario == "NETWORK_PARTITION":
        background_tasks.add_task(network_partition_task)
        return {"status": "success", "message": f"Node {settings.NODE_ID} Network partitioned for 15s."}

    elif scenario == "DB_DELAY":
        async def db_delay_task():
            from app.platform.core.chaos_state import chaos_state
            logger.warning(f"[{settings.NODE_ID}] Starting DB Delay...")
            chaos_state.db_delay_seconds = 2.0
            await asyncio.sleep(15)
            chaos_state.db_delay_seconds = 0.0
            logger.warning(f"[{settings.NODE_ID}] Finished DB Delay.")
        background_tasks.add_task(db_delay_task)
        return {"status": "success", "message": f"Node {settings.NODE_ID} DB delay injected for 15s."}

    elif scenario == "PAUSE_REPLICATION":
        async def pause_rep_task():
            logger.warning(f"[{settings.NODE_ID}] Pausing replication...")
            raft_node._fault_pause_replication = True
            await asyncio.sleep(15)
            raft_node._fault_pause_replication = False
            logger.warning(f"[{settings.NODE_ID}] Resumed replication.")
        background_tasks.add_task(pause_rep_task)
        return {"status": "success", "message": f"Node {settings.NODE_ID} paused replication for 15s."}

    elif scenario == "REPLICATION_LAG":
        async def rep_lag_task():
            logger.warning(f"[{settings.NODE_ID}] Simulating replication lag...")
            raft_node._fault_replication_lag = 3.0
            await asyncio.sleep(15)
            raft_node._fault_replication_lag = 0.0
            logger.warning(f"[{settings.NODE_ID}] Finished replication lag.")
        background_tasks.add_task(rep_lag_task)
        return {"status": "success", "message": f"Node {settings.NODE_ID} replication delayed for 15s."}

    elif scenario == "PAYMENT_BURST":
        import uuid
        logger.warning(f"[{settings.NODE_ID}] Starting payment burst (50 Tx)...")
        
        async def send_tx(i):
            # Space requests exactly 200ms apart (5 TPS) to guarantee no clumping
            # that triggers Stripe's 25 TPS test-mode limits.
            await asyncio.sleep(i * 0.2)
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"http://127.0.0.1:{settings.INTERNAL_PORT}/api/v1/payments/",
                        headers={
                            "Authorization": f"Bearer {settings.API_KEY}",
                            "idempotency-key": str(uuid.uuid4())
                        },
                        json={
                            "amount": 10.0 + i,
                            "currency": "usd",
                            "payment_method": "pm_card_visa",
                            "sender_id": f"user_chaos_sender",
                            "receiver_id": f"user_chaos_receiver"
                        }
                    )
                    if resp.status_code >= 400:
                        logger.error(f"Burst tx {i} failed with {resp.status_code}: {resp.text}")
                        return False
                    return True
            except Exception as e:
                logger.error(f"Burst tx {i} failed: {e}")
                return False

        results = await asyncio.gather(*(send_tx(i) for i in range(50)))
        success_count = sum(results)
        logger.warning(f"[{settings.NODE_ID}] Finished payment burst. Success: {success_count}/50")
        return {"status": "success", "message": f"Node {settings.NODE_ID} burst completed. {success_count}/50 requests accepted."}

    elif scenario == "FORCE_ELECTION":
        async def force_election():
            async with raft_node.lock:
                raft_node.state.role = NodeState.CANDIDATE
                raft_node._update_role_metric()
                raft_node.election_manager.reset_timer()
        background_tasks.add_task(force_election)
        return {"status": "success", "message": f"Node {settings.NODE_ID} forced to election."}

    else:
        # Mock other scenarios that require OS-level access
        logger.warning(f"[{settings.NODE_ID}] Mocking unsupported scenario {scenario}")
        return {"status": "mocked", "message": f"Scenario {scenario} executed as mock (Requires OS privileges)."}
