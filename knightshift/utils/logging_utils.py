# ==============================================================================
# logging_utils.py  –  Consistent dual-destination logging
#
# Features:
#   ✔ Console + rotating file output
#   ✔ Auto-detects Airflow vs. local path for logs
#   ✔ Idempotent: clears handlers before re-adding
# ==============================================================================

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------

_FMT = "%(asctime)s | %(levelname)-8s | %(message)s"
_DEFAULT_LEVEL = logging.INFO


# ------------------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------------------


def _detect_logs_dir() -> Path:
    """
    Detect where logs should be stored.

    • Airflow container → /opt/airflow/logs/pipeline_logs
    • Local dev        → <repo>/logs
    """
    airflow_home = Path("/opt/airflow")
    if airflow_home.exists():
        return airflow_home / "logs" / "pipeline_logs"

    return Path(__file__).resolve().parents[2] / "logs"


def _init_file_handler(
    logs_dir: Path, logger_name: str, fmt: logging.Formatter
) -> Optional[logging.Handler]:
    """
    Create a timestamped FileHandler if directory is writable.
    Falls back to console logging if not.
    """
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = logs_dir / f"{logger_name}_{timestamp}.log"

        fh = logging.FileHandler(file_path, encoding="utf-8")
        fh.setFormatter(fmt)
        return fh
    except PermissionError:
        logging.getLogger().warning("Cannot write logs to %s", logs_dir)
        return None


# ------------------------------------------------------------------------------
# Public factory
# ------------------------------------------------------------------------------


def setup_logger(
    name: str,
    level: int = _DEFAULT_LEVEL,
    logs_dir: Union[str, Path, None] = None,
) -> logging.Logger:
    """
    Return a fresh `logging.Logger`.

    Parameters
    ----------
    name : str
        Logger name (used in file naming).
    level : int
        Logging level (INFO by default).
    logs_dir : str | Path | None
        Override log directory (default: auto-detect).
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers for idempotency
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(_FMT)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler
    target_dir = Path(logs_dir) if logs_dir else _detect_logs_dir()
    file_handler = _init_file_handler(target_dir, name, formatter)
    if file_handler:
        logger.addHandler(file_handler)

    return logger
