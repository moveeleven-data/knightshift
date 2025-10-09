# ==============================================================================
#  KnightShift Pipeline Container
#  Purpose: Builds a Python app container that runs run.sh on launch
# ==============================================================================
FROM python:3.10-slim

# ------------------------------------------------------------------------------
# Working directory
# ------------------------------------------------------------------------------
WORKDIR /app

# ------------------------------------------------------------------------------
# System dependencies
#   - bash: required for run.sh
#   - postgresql-client: provides pg_isready
#   - procps: enables ps/top utilities for debugging
# ------------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
      bash \
      postgresql-client \
      procps \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------------------
# Python dependencies
# ------------------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------------------
# Project code
# ------------------------------------------------------------------------------
COPY knightshift/ ./knightshift/
COPY scripts/run.sh ./run.sh
RUN chmod +x run.sh

# ------------------------------------------------------------------------------
# Logging (shared with Airflow)
# ------------------------------------------------------------------------------
RUN mkdir -p /opt/airflow/logs/pipeline_logs \
    && chmod -R 777 /opt/airflow/logs/pipeline_logs

# ------------------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------------------
ENTRYPOINT ["./run.sh"]

# ------------------------------------------------------------------------------
# Healthcheck
#   interval: every 30s
#   timeout: 10s
#   start-period: wait 5s before first check
#   retries: fail after 3 unsuccessful attempts
# ------------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pg_isready -h db -p 5432 -U postgres || exit 1
