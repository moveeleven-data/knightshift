# ----------------------------------------------------------------------
# KnightShift pipeline container
# Builds a Python app container that runs the run.sh script on launch.
# ----------------------------------------------------------------------

FROM python:3.10-slim

WORKDIR /app

# Install bash, Postgres client, and procps (for ps command)
RUN apt-get update && apt-get install -y bash postgresql-client procps && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY knightshift/ ./knightshift/
COPY scripts/run.sh ./run.sh

# Make run.sh executable
RUN chmod +x run.sh

# Create log directory (for Airflow usage) with broad permissions
RUN mkdir -p /opt/airflow/logs/pipeline_logs && chmod -R 777 /opt/airflow/logs/pipeline_logs

# Run the pipeline
ENTRYPOINT ["./run.sh"]

# Healthcheck to verify Postgres is reachable
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pg_isready -h db -p 5432 -U postgres || exit 1

# Healthcheck to verify Postgres is reachable
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pg_isready -h db -p 5432 -U postgres || exit 1

# --interval=30s: Run health check every 30 seconds
# --timeout=10s: Fail if health check takes longer than 10 seconds
# --start-period=5s: Wait 5 seconds before first health check
# --retries=3: Retry the health check up to 3 times before marking as unhealthy
# CMD: Command to run for health check
# pg_isready: Checks if Postgres is accepting connections
# -h db: Hostname of the Postgres service (defined in Docker Compose)
# -p 5432: Port number for Postgres
# -U postgres: User to check Postgres connection with
# || exit 1: Fail health check if pg_isready fails
