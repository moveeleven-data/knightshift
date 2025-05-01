#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  KnightShift - pipeline container entry-point
#  1. Wait until Postgres answers on $PGHOST:$PGPORT
#  2. Run the project’s main module  (now lives in knightshift/, not src/)
#  3. Keep the container alive so you can docker exec into it for debugging
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
echo "KnightShift pipeline finished"

# ───────────────────────  Keep container alive  ──────────────────────────────
# Makes `docker exec -it <container> bash` possible after the run.
tail -f /dev/null
