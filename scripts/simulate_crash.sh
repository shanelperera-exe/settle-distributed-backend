#!/bin/bash
# script to simulate a node crash

echo "Simulating failure of settle-node-1..."
docker stop settle-node-1

echo "Wait 20 seconds for ZooKeeper session to expire and watcher to trigger..."
sleep 20

echo "Checking cluster health from node-2..."
curl -s http://localhost:8002/api/v1/health/cluster | python3 -m json.tool

echo "Restarting node-1 (simulating recovery)..."
docker start settle-node-1

echo "Wait 10 seconds for node-1 to rejoin..."
sleep 10

echo "Checking cluster health again..."
curl -s http://localhost:8002/api/v1/health/cluster | python3 -m json.tool
