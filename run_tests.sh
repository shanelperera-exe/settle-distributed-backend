#!/bin/bash
set -e

echo "=========================================================="
echo "          Settle - Distributed Test Suite Runner          "
echo "=========================================================="
echo ""

echo "[*] Syncing latest test files to the cluster..."
docker cp backend/tests/ $(docker compose -f infra/docker-compose.yml ps -q node-1):/app/ > /dev/null 2>&1
docker cp backend/app/ $(docker compose -f infra/docker-compose.yml ps -q node-1):/app/ > /dev/null 2>&1

echo "[>] Running 35 test cases (Unit, Integration, Stress, E2E)..."
echo ""

# Run pytest inside node-1 with a clean, concise summary (-v for verbosity, --tb=short for concise tracebacks)
docker compose -f infra/docker-compose.yml exec node-1 bash -c "export PYTHONPATH=/app && pytest tests/ -v --tb=short"

echo ""
echo "=========================================================="
echo " [+] All tests completed successfully!"
echo "=========================================================="
