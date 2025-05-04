from prometheus_client import start_http_server, Counter, Histogram
import time
import random
import logging
import signal
import sys
import os

# ─────────────────────────────────────────────────────────────────────────────
# Configuration and Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

INSTANCE_NAME = os.getenv("INSTANCE_NAME", "fake_pipeline:8000")
JOB_NAME = os.getenv("JOB_NAME", "observability_sim")

# ─────────────────────────────────────────────────────────────────────────────
# Prometheus Metrics Definitions
# ─────────────────────────────────────────────────────────────────────────────
REQUESTS = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["status", "instance", "job"],
)

ERRORS = Counter("http_requests_errors", "Total number of HTTP request errors")

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Histogram for the duration of HTTP requests"
)

GAMES_INGESTED = Counter(
    "games_ingested_total", "Total number of games ingested", ["instance", "job"]
)

UPDATES = Counter(
    "games_updated_total", "Total number of games updated", ["instance", "job"]
)

ADDITIONS = Counter(
    "games_added_total", "Total number of new games added", ["instance", "job"]
)

INGESTION_DURATION = Histogram(
    "ingestion_duration_seconds",
    "Histogram for simulated ingestion durations",
    ["instance", "job"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Graceful Shutdown Handler
# ─────────────────────────────────────────────────────────────────────────────
def shutdown_handler(signal_num, frame):
    logging.info("Received shutdown signal. Exiting cleanly.")
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)


# ─────────────────────────────────────────────────────────────────────────────
# Start Prometheus Metrics Server
# ─────────────────────────────────────────────────────────────────────────────
def start_metrics_server():
    try:
        logging.info("Starting Prometheus metrics server on port 8000...")
        start_http_server(8000)
        logging.info("Prometheus metrics server running.")
    except Exception as e:
        logging.error(f"Failed to start metrics server: {e}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Simulated Ingestion Loop
# ─────────────────────────────────────────────────────────────────────────────
def simulate_ingestion():
    while True:
        with REQUEST_LATENCY.time():
            try:
                # Simulate successful request
                REQUESTS.labels(
                    status="200", instance=INSTANCE_NAME, job=JOB_NAME
                ).inc()

                # Simulate ingestion logic
                GAMES_INGESTED.labels(instance=INSTANCE_NAME, job=JOB_NAME).inc()
                ADDITIONS.labels(instance=INSTANCE_NAME, job=JOB_NAME).inc()

                # Simulate variable processing time
                time.sleep(random.uniform(0.5, 2.0))
            except Exception as e:
                ERRORS.inc()
                logging.error(f"Ingestion error: {e}")
                time.sleep(1)


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    start_metrics_server()
    logging.info("Simulating ingestion of fake Lichess TV data...")
    simulate_ingestion()
