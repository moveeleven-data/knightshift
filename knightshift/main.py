#!/usr/bin/env python3
# ==============================================================================
#  KnightShift - main.py
#  Purpose: one-shot runner for the full KnightShift pipeline
#           (ingestion → cleaning → enrichment)
# ==============================================================================

import logging
import sys
from pathlib import Path

# ------------------------------------------------------------------------------
# Paths & Imports
# ------------------------------------------------------------------------------

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knightshift.pipeline.run_cleaning import validate_and_clean
from knightshift.pipeline.run_enrichment import run_enrichment_pipeline as run_enrichment
from knightshift.pipeline.run_ingestion import run_tv_ingestion

# ------------------------------------------------------------------------------
# Logging Setup
# ------------------------------------------------------------------------------

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "pipeline.log"

# Redirect stdout and stderr (prints + tracebacks) to the same log file
sys.stdout = sys.stderr = open(LOG_FILE, "a", buffering=1, encoding="utf-8")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger("main")

# ------------------------------------------------------------------------------
# Stage Wrapper
# ------------------------------------------------------------------------------

def _stage(title, fn):
    """
    Run a pipeline stage with start → finish logging and full stacktrace on error.
    """
    logger.info("%s – started", title)
    try:
        fn()
        logger.info("%s – finished", title)
    except Exception:  # pragma: no cover
        logger.exception("%s – failed", title)
        raise


if __name__ == "__main__":
    _stage("TV Game Ingestion", run_tv_ingestion)
    _stage("Sanitize Game Records", validate_and_clean)
    _stage("Back-fill User Profiles", run_enrichment)
