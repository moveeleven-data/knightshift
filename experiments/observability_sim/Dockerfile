# ------------------------------------------------------------------------------
# Observability Simulation Container
# Runs Prometheus metrics script as a standalone app for observability testing
# ------------------------------------------------------------------------------

FROM python:3.10-slim

# Create and set working directory
WORKDIR /app

# Install bash, Postgres client (optional), and procps for `ps` in run.sh
RUN apt-get update && \
    apt-get install -y bash postgresql-client procps && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install them
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy observability scripts
COPY run.sh .
COPY prometheus_metrics.py .

# Make run.sh executable
RUN chmod +x run.sh

# Run script on container startup
ENTRYPOINT ["./run.sh"]

# Optional health check (can be removed if not needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pg_isready -h db -p 5432 -U postgres || exit 1
