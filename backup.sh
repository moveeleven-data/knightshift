#!/bin/bash

# ── Configuration ─────────────────────────────────────────────
DB_CONTAINER=$(docker compose ps -q db)
DB_NAME="knightshift"
DB_USER="postgres"

# ── Timestamped filename ──────────────────────────────────────
TODAY=$(date +"%Y-%m-%d")
FILENAME="backups/${DB_NAME}_${TODAY}.sql"

# ── Start logging to backup.log ───────────────────────────────
exec >> backups/backup.log 2>&1
echo "===== Running backup on $(date) ====="

# ── Run pg_dump from inside the container ─────────────────────
echo "Dumping database '${DB_NAME}' to '${FILENAME}'..."
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$FILENAME"

if [ $? -eq 0 ]; then
  echo "Backup completed: ${FILENAME}"
else
  echo "Backup failed"
  exit 1
fi

# ── Compress the backup file ──────────────────────────────────
echo "Compressing ${FILENAME} to ${FILENAME}.gz..."
gzip "$FILENAME"

# ── Delete compressed backups older than 7 days ───────────────
echo "Cleaning up old compressed backups..."
find backups/ -type f -name "*.sql.gz" -mtime +7 -exec rm {} \;

# ── Optional: delete any raw .sql files too ───────────────────
find backups/ -type f -name "*.sql" -mtime +7 -exec rm {} \;

echo "All done. Logged to backups/backup.log"
