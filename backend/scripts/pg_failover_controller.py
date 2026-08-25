#!/usr/bin/env python3
import os
import sys
import time
import logging
import subprocess
from kazoo.client import KazooClient
from kazoo.recipe.election import Election
from kazoo.protocol.states import EventType

# Configuration
ZK_HOST = os.getenv("ZOOKEEPER_HOST", "localhost:2181")
PG_DATA = os.getenv("PGDATA", "/var/lib/postgresql/data")
NODE_ID = os.getenv("NODE_ID", f"pg-node-{os.getpid()}")
IS_PRIMARY_INITIALLY = os.getenv("IS_PRIMARY", "false").lower() == "true"

ZK_PRIMARY_PATH = "/postgres/primary"
ZK_ELECTION_PATH = "/postgres/election"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("pg_failover")

zk = KazooClient(hosts=ZK_HOST)

def promote_to_primary():
    logger.info("Executing pg_ctl promote to become primary...")
    try:
        # Run pg_ctl promote
        # In a real environment, this might use 'touch /tmp/postgresql.trigger' or similar
        subprocess.run(["pg_ctl", "promote", "-D", PG_DATA], check=True)
        logger.info("PostgreSQL successfully promoted to primary.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to promote PostgreSQL: {e}")
        # Even if promotion fails, we might still want to hold the lock or retry
        raise e

def register_as_primary(client):
    logger.info(f"Registering {NODE_ID} as the primary in ZooKeeper...")
    client.ensure_path("/postgres")
    
    # Try to create the ephemeral primary node
    if client.exists(ZK_PRIMARY_PATH):
        logger.warning("Primary node already exists! Cleaning it up.")
        client.delete(ZK_PRIMARY_PATH)
        
    client.create(ZK_PRIMARY_PATH, value=NODE_ID.encode('utf-8'), ephemeral=True)
    logger.info(f"Node {NODE_ID} is now recognized as the Primary by ZooKeeper.")

def watch_primary(client):
    """
    Sets a watch on the primary node. If it disappears, triggers election.
    """
    logger.info("Setting watch on primary znode...")
    
    @client.DataWatch(ZK_PRIMARY_PATH)
    def primary_watch(data, stat, event):
        if event and event.type == EventType.DELETED:
            logger.warning("Primary znode deleted! Primary has died. Entering election...")
            enter_election(client)
            # return False to stop watching since we're now in election
            return False

def enter_election(client):
    logger.info(f"Node {NODE_ID} entering leader election...")
    election = Election(client, ZK_ELECTION_PATH, NODE_ID)
    
    def leader_func():
        logger.info(f"Node {NODE_ID} WON the election! Promoting to primary...")
        promote_to_primary()
        register_as_primary(client)
        # Keep alive as primary
        while True:
            time.sleep(10)
            
    election.run(leader_func)

def main():
    zk.start()
    logger.info(f"Connected to ZooKeeper at {ZK_HOST}")

    # Ensure base path exists
    zk.ensure_path("/postgres")

    if IS_PRIMARY_INITIALLY:
        # This node is starting as the primary
        logger.info(f"Node {NODE_ID} starting as initial Primary.")
        register_as_primary(zk)
        while True:
            time.sleep(10)
    else:
        # This node is starting as a replica
        logger.info(f"Node {NODE_ID} starting as Replica. Monitoring Primary...")
        if not zk.exists(ZK_PRIMARY_PATH):
            logger.warning("No primary found on startup. Entering election immediately.")
            enter_election(zk)
        else:
            watch_primary(zk)
            while True:
                time.sleep(10)

if __name__ == "__main__":
    main()
