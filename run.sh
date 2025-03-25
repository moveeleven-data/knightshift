#!/bin/bash

echo "RUN.SH started"
which python
python --version

echo "Waiting for Postgres to be ready..."

# Wait until the database is ready to accept connections
until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER"; do
  echo "Postgres is unavailable - sleeping"
  sleep 2
done

echo "Postgres is up - running main.py"
python src/main.py
echo "Done"
