from prometheus_client import start_http_server, Counter, Histogram
import time
import random
import logging
import signal
import sys
import os

# Set up logging with proper format
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Use environment variables for instance and job labels
instance = os.getenv("INSTANCE_NAME", "pipeline:8000")  # Default to "pipeline:8000"
job = os.getenv("JOB_NAME", "knightshift")  # Default to "knightshift"

# Define Prometheus metrics for HTTP requests and ingestion
REQUESTS = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["status", "instance", "job"],
)

ERRORS = Counter("http_requests_errors", "Total number of HTTP request errors")
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Histogram for the duration of HTTP requests"
)

# New metrics for the ingestion process
GAMES_INGESTED = Counter(
    "games_ingested_total",
    "Total number of games ingested from Lichess TV",
    ["instance", "job"],
)

UPDATES = Counter(
    "games_updated_total",
    "Total number of games updated",
    ["instance", "job"],
)

ADDITIONS = Counter(
    "games_added_total",
    "Total number of new games added",
    ["instance", "job"],
)

INGESTION_DURATION = Histogram(
    "ingestion_duration_seconds",
    "Histogram for the duration of the ingestion process",
    ["instance", "job"],
)


# Define the shutdown handler for graceful termination
def shutdown_handler(signal, frame):
    logging.info("Shutting down gracefully...")
    sys.exit(0)


# Register the shutdown handler for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, shutdown_handler)


# Ensure the server starts successfully before processing
def start_metrics_server():
    try:
        logging.info("Starting metrics server on port 8000...")
        start_http_server(8000)
        logging.info("Metrics server started successfully.")
    except Exception as e:
        logging.error(f"Failed to start metrics server: {e}")
        sys.exit(1)


# Ingestion simulation function
def simulate_ingestion():
    while True:
        with REQUEST_LATENCY.time():  # Start measuring request duration
            try:
                # Simulate ingestion process
                status = "200"
                REQUESTS.labels(status=status, instance=instance, job=job).inc()
                GAMES_INGESTED.labels(
                    instance=instance, job=job
                ).inc()  # Increment the games ingested counter

                # Simulate adding a new game
                ADDITIONS.labels(instance=instance, job=job).inc()
                time.sleep(random.uniform(0.5, 2))  # Simulate varying load

            except Exception as e:
                # Handle errors and increment error counter
                ERRORS.inc()
                logging.error(f"Error occurred during ingestion: {e}")
                time.sleep(1)  # Sleep before retrying to avoid fast continuous errors


# Main execution
if __name__ == "__main__":
    try:
        start_metrics_server()  # Start the Prometheus server before ingestion
        logging.info("Simulating ingestion of games...")
        simulate_ingestion()
    except Exception as ex:
        logging.critical(f"Unexpected error during ingestion: {ex}")
        sys.exit(1)
