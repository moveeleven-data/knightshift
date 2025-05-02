# ----------------------------------------------------------------------
# KnightShift pipeline container
# Builds a Python app container that runs the run.sh script on launch.
# ----------------------------------------------------------------------

FROM python:3.10-slim

WORKDIR /app

# Install bash and Postgres client
RUN apt-get update && apt-get install -y bash postgresql-client && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY knightshift/ ./knightshift/
COPY scripts/run.sh ./run.sh

# Copy Prometheus metrics script
COPY prometheus_metrics/ ./prometheus_metrics/

# Make run.sh executable
RUN chmod +x run.sh

# Create log directory (for Airflow usage) with broad permissions
RUN mkdir -p /opt/airflow/logs/pipeline_logs && chmod -R 777 /opt/airflow/logs/pipeline_logs

# Run the pipeline
ENTRYPOINT ["./run.sh"]

# Healthcheck to verify Postgres is reachable
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pg_isready -h db -p 5432 -U postgres || exit 1
