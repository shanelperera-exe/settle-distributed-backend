#!/bin/bash
# script to simulate ZooKeeper network partition

echo "Pausing ZooKeeper container to simulate network partition..."
docker pause zookeeper

echo "Wait 20 seconds. Nodes should enter SUSPENDED and then LOST state."
sleep 20

echo "Unpausing ZooKeeper. Nodes should reconnect and re-register."
docker unpause zookeeper

echo "Wait 10 seconds for recovery..."
sleep 10

echo "Checking cluster health..."
curl -s http://localhost:8001/api/v1/health/cluster | python3 -m json.tool
