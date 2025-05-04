#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  Observability Sim Entry-Point
#  This script starts the Prometheus metrics simulation server and verifies that
#  it runs successfully. It is used inside the Docker container launched by
#  experiments/observability_sim/docker-compose.yml.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

echo "run.sh – starting Prometheus metrics simulation"
echo "• Python  : $(python --version 2>&1)"
echo "• Workdir : $(pwd)"

# ───────────────────────  Start Prometheus Metrics Server  ───────────────────
echo "Starting prometheus_metrics.py..."
python3 /app/prometheus_metrics.py &  # Run in background

# Give it a few seconds to initialize
sleep 3

# ───────────────────────  Verify the process is running  ─────────────────────
echo "Checking if prometheus_metrics.py is running..."
ps aux | grep prometheus_metrics | grep -v grep

echo "Prometheus metrics simulation started."

# ───────────────────────  Keep container alive  ──────────────────────────────
# Makes `docker exec -it` possible for inspection
tail -f /dev/null
