import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from kazoo.client import KazooClient
from kazoo.protocol.states import EventType
import sys
import os

# Add scripts to path to import pg_failover_controller
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scripts")))
import pg_failover_controller

@pytest.fixture
def zk_client():
    client = KazooClient(hosts="localhost:2181")
    try:
        client.start(timeout=5)
    except Exception:
        pytest.skip("ZooKeeper not running locally. Skipping test.")
    
    yield client
    
    # Cleanup
    if client.exists("/postgres"):
        client.delete("/postgres", recursive=True)
    client.stop()
    client.close()

def test_pg_failover_promotion(zk_client, monkeypatch):
    """
    Simulates a primary dying and a replica taking over via ZooKeeper election.
    """
    zk_client.ensure_path("/postgres")
    
    # 1. Simulate existing primary
    zk_client.create("/postgres/primary", value=b"node-primary", ephemeral=True)
    assert zk_client.exists("/postgres/primary") is not None
    
    # Mock subprocess.run so we don't actually run pg_ctl on the test machine
    mock_run = MagicMock()
    monkeypatch.setattr("pg_failover_controller.subprocess.run", mock_run)
    
    # 2. Start replica controller logic in a thread
    replica_thread_event = threading.Event()
    
    def run_replica():
        pg_failover_controller.zk = zk_client
        pg_failover_controller.NODE_ID = "node-replica"
        
        # Override the watch callback to signal when promotion happens
        original_watch = pg_failover_controller.watch_primary
        
        @zk_client.DataWatch("/postgres/primary")
        def primary_watch(data, stat, event):
            if event and event.type == EventType.DELETED:
                pg_failover_controller.enter_election(zk_client)
                replica_thread_event.set()
                return False
                
    replica_thread = threading.Thread(target=run_replica)
    replica_thread.daemon = True
    replica_thread.start()
    
    time.sleep(1) # Give the watch time to establish
    
    # 3. Kill the primary
    zk_client.delete("/postgres/primary")
    
    # 4. Wait for replica to detect and elect itself
    replica_thread_event.wait(timeout=5)
    
    # Give it a tiny bit of time to execute pg_ctl and register
    time.sleep(1)
    
    # 5. Assertions
    # Did it run pg_ctl promote?
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0] == ["pg_ctl", "promote", "-D", pg_failover_controller.PG_DATA]
    
    # Is the new primary registered in ZK?
    assert zk_client.exists("/postgres/primary") is not None
    primary_data, _ = zk_client.get("/postgres/primary")
    assert primary_data.decode("utf-8") == "node-replica"
