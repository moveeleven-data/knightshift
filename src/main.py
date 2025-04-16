#!/usr/bin/env python3

"""
Top-level orchestrator for running the full KnightShift pipeline:
Ingest → Clean → Enrich.
Logs each step to pipeline.log and prints progress to console.
"""

import sys
import logging
from pathlib import Path

# Setup project root to enable internal imports
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))


from src.pipeline.run_ingestion import run_tv_ingestion
from src.pipeline.run_cleaning import validate_and_clean
from src.pipeline.run_enrichment import main as run_enrichment

# Define where logs should be stored (in the top-level /logs folder)
# If the folder doesn’t exist yet, create it — this prevents file-not-found errors later
# Build the full path to the log file where all output will be saved
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)
log_file_path = LOGS_DIR / "pipeline.log"

# Redirect all printed output (sys.stdout) and error messages (sys.stderr)
# so that everything goes into our pipeline.log file
sys.stdout = open(log_file_path, "a")
sys.stderr = open(log_file_path, "a")

# Initialize Python’s logging system. This gives us:
# Timestamps, log levels (INFO, WARNING, ERROR), and structured logging across all scripts
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Wrap each stage of the pipeline (ingest, clean, enrich)
# It prints/logs when a stage starts and ends
def log_and_run(msg, func):
    print(f"Starting: {msg}")
    logging.info(f"Starting: {msg}")
    func()
    print(f"Finished: {msg}")
    logging.info(f"Finished: {msg}")


if __name__ == "__main__":
    log_and_run("TV Game Ingestion", run_tv_ingestion)
    log_and_run("Sanitize Game Records", validate_and_clean)
    log_and_run("Backfill User Profiles", run_enrichment)
