#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  KnightShift - pipeline container entry-point
#  1. Wait until Postgres answers on $PGHOST:$PGPORT
#  2. Run the project’s main module  (now lives in knightshift/, not src/)
#  3. Start Prometheus metrics server
#  4. Keep the container alive so you can docker exec into it for debugging
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

echo "run.sh – starting KnightShift pipeline"
echo "• Python  : $(python --version 2>&1)"
echo "• Workdir : $(pwd)"

# ─────────────────────────  Wait for Postgres  ───────────────────────────────
echo "Waiting for Postgres on ${PGHOST:-db}:${PGPORT:-5432} …"
until pg_isready -h "${PGHOST:-db}" -p "${PGPORT:-5432}" -U "${PGUSER:-postgres}" \
      >/dev/null 2>&1; do
  echo "   ↳ still unreachable – sleeping 2 s"
  sleep 2
done
echo "Postgres is ready"

# ───────────────────────────  Run the job  ───────────────────────────────────
echo "python knightshift/main.py"
python knightshift/main.py

# ───────────────────────  Start Prometheus Metrics Server ───────────────────
echo "Starting Prometheus metrics server..."
# Add full path to ensure that it's being found properly
python3 /app/prometheus_metrics/prometheus_metrics.py &  # Run in background

# Wait to confirm if the metrics server started
sleep 5  # Wait for 5 seconds to make sure server has started

# Check if the process is running
echo "Checking if Prometheus metrics server is running..."
ps aux | grep prometheus_metrics

echo "KnightShift pipeline finished"

# ───────────────────────  Keep container alive  ──────────────────────────────
# Makes `docker exec -it <container> bash` possible after the run.
tail -f /dev/null
