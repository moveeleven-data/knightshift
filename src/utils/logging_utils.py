import logging
from pathlib import Path
from datetime import datetime
import sys
import os


def setup_logger(name: str, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Detect Airflow container and route logs accordingly
    inside_airflow = Path("/opt/airflow").exists()
    if inside_airflow:
        logs_dir = Path("/opt/airflow/logs/pipeline_logs")
    else:
        logs_dir = Path(__file__).resolve().parent.parent.parent / "logs"

    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_handler = logging.FileHandler(
            logs_dir / f"{name}_{timestamp}.log", encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except PermissionError:
        # Skip file handler if permission is denied (failsafe)
        logger.warning(f"Could not write to log directory: {logs_dir}")

    return logger
