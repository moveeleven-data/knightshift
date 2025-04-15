# ----------------------------------------------------------------------
# This file defines how to build the KnightShift pipeline container.
# It creates a Python environment with all dependencies and code.
# When the container starts, it will automatically run the run.sh script.
# This file is used by `docker-compose.yml` to build the image.
# ----------------------------------------------------------------------

FROM python:3.10-slim

WORKDIR /app

# Install Postgres client tools
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY src/ ./src/
COPY run.sh .

# Make run.sh executable
RUN chmod +x run.sh

# Run the pipeline
ENTRYPOINT ["./run.sh"]

# Healthcheck: ping Postgres db using pg_isready
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pg_isready -h db -p 5432 -U postgres || exit 1