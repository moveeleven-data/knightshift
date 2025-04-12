#!/usr/bin/env python3
"""
main.py

Top-level orchestrator for running the full KnightShift pipeline:
Ingest → Clean → Enrich (optional).
Logs each step to pipeline.log and prints progress to console.
"""

import sys
import logging
from pathlib import Path

# Add src/ folder to sys.path so imports like src.pipeline.* work
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import modular run steps
from src.pipeline.run_ingestion import run_tv_ingestion
from src.pipeline.run_cleaning import validate_and_clean
from src.pipeline.run_enrichment import main as run_enrichment  # renamed for clarity

# Logging Setup
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)
log_file_path = LOGS_DIR / "pipeline.log"

# Redirect stdout and stderr to the log file
sys.stdout = open(log_file_path, "a")
sys.stderr = open(log_file_path, "a")

# Initialize logging to same file
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


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
