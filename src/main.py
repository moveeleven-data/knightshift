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

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import modular run steps
from src.pipeline.run_ingestion import run_tv_ingestion
from src.pipeline.run_cleaning import validate_and_clean
from src.pipeline.run_enrichment import main as run_enrichment  # renamed for clarity

# Logging Setup
logging.basicConfig(
    filename="pipeline.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
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
