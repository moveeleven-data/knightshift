#!/usr/bin/env python3
# main.py  –  “one‑shot” runner for the full KnightShift pipeline

from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import FunctionType
from typing import Final

# Repo‑relative imports
SRC_DIR: Final[Path] = Path(__file__).resolve().parent
PROJECT_ROOT: Final[Path] = SRC_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knightshift.pipeline.run_cleaning import validate_and_clean  # noqa: E402
from knightshift.pipeline.run_enrichment import (
    run_enrichment_pipeline as run_enrichment,
)  # noqa: E402
from knightshift.pipeline.run_ingestion import run_tv_ingestion  # noqa: E402


# Logging setup (shared file across stages)
LOG_DIR: Final[Path] = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE: Final[Path] = LOG_DIR / "pipeline.log"

# Pipe everything (print + traceback) to the same log file
sys.stdout = sys.stderr = open(
    LOG_FILE, "a", buffering=1, encoding="utf-8"
)  # noqa: P201

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,  # override any previous basicConfig
)
logger = logging.getLogger("main")


def _stage(title: str, fn: FunctionType) -> None:
    """
    Wrapper that logs **start → finish** around a pipeline stage.
    """
    logger.info("%s – started", title)
    try:
        fn()
        logger.info("%s – finished", title)
    except Exception:  # pragma: no cover  (we want full stacktrace in log)
        logger.exception("%s – failed", title)
        raise


if __name__ == "__main__":
    _stage("TV Game Ingestion", run_tv_ingestion)
    _stage("Sanitize Game Records", validate_and_clean)
    _stage("Back‑fill User Profiles", run_enrichment)
