from prometheus_client import start_http_server, Counter, Histogram
import time
import random
import logging
import signal
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define the counter metric with additional labels for instance and job
REQUESTS = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["status", "instance", "job"],
)
ERRORS = Counter("http_requests_errors", "Total number of HTTP request errors")
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Histogram for the duration of HTTP requests"
)


# Define the shutdown handler
def shutdown_handler(signal, frame):
    logging.info("Shutting down gracefully...")
    sys.exit(0)


# Register the shutdown handler
signal.signal(signal.SIGINT, shutdown_handler)

# Start the Prometheus HTTP server on port 8000
logging.info("Starting metrics server on port 8000...")
start_http_server(8000)

# Simulate a web service with a loop to increment the counter and track errors
while True:
    with REQUEST_LATENCY.time():  # Start measuring request duration
        try:
            # Simulate successful request
            status = "200"
            REQUESTS.labels(
                status=status, instance="pipeline:8000", job="knightshift"
            ).inc()
            time.sleep(random.uniform(0.5, 2))  # Simulate varying load

        except Exception as e:
            # Handle errors and increment error counter
            ERRORS.inc()
            logging.error(f"Error: {e}")
            time.sleep(1)
