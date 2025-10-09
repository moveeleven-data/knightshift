#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  KnightShift - Pipeline Container Entry Point
#
#  Responsibilities:
#    1. Wait until Postgres answers on $PGHOST:$PGPORT
#    2. Run the project's main module (knightshift/main.py)
#    3. Print exit status
#    4. Keep the container alive for debugging via `docker exec`
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

log() {
  # Timestamped log lines for better traceability
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "KnightShift pipeline starting…"
log "Python version : $(python --version 2>&1)"
log "Working dir    : $(pwd)"

# ─────────────────────────  Wait for Postgres  ────────────────────────────────
PGHOST="${PGHOST:-db}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"

log "Waiting for Postgres at ${PGHOST}:${PGPORT} (user=${PGUSER})"
until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" >/dev/null 2>&1; do
  log "   ↳ still unreachable, retrying in 2 s"
  sleep 2
done
log "Postgres is ready"

# ───────────────────────────  Run the pipeline  ───────────────────────────────
log "Launching KnightShift main module"
if python knightshift/main.py; then
  log "KnightShift pipeline finished successfully"
else
  log "[ERROR] KnightShift pipeline failed"
  exit 1
fi

# ───────────────────────  Keep container alive  ───────────────────────────────
log "Keeping container alive (Ctrl+C to stop)"
exec tail -f /dev/null
