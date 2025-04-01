#!/usr/bin/env python3
"""
validate_tv_channel_games.py

This script validates and cleans rows in the tv_channel_games table.
It ensures that each row has the required fields (white, black, moves, result),
validates the URL format, cleans Elo values, and then updates or deletes the row accordingly.
Configuration parameters (e.g. TIME_LIMIT, SLEEP_INTERVAL, PAUSE_AFTER, PAUSE_DURATION) are read from environment variables.
Logs are written to both the console and a timestamped log file.
"""

import sys
from pathlib import Path
import os
import re
import time
from datetime import datetime
import logging

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Table,
    Column,
    String,
    MetaData,
    select,
    delete,
    update,
    Boolean,
    Integer,
    Date,
    Time,
)
from sqlalchemy.orm import sessionmaker

# --- Add Project Root to Python Path ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# --- Import Shared Utilities ---
from utils.db_utils import load_db_credentials, get_database_url
from utils.logging_utils import setup_logger

# --- Logging Setup ---
logger = setup_logger(name="validate_tv_channel_games", level=logging.INFO)

# --- Environment & Configuration ---
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env.local")
creds = load_db_credentials()
logger.info(
    "Loaded DB credentials successfully."
)  # In production, mask sensitive details.
DATABASE_URL = get_database_url(creds)
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Configuration parameters
TIME_LIMIT: int = int(
    os.getenv("TIME_LIMIT", 60)
)  # Total runtime in seconds (default: 60 for testing)
SLEEP_INTERVAL: int = int(os.getenv("SLEEP_INTERVAL", 40))  # Seconds between batches
PAUSE_AFTER: int = int(
    os.getenv("PAUSE_AFTER", 2500)
)  # Number of rows to process before pausing
PAUSE_DURATION: int = int(
    os.getenv("PAUSE_DURATION", 900)
)  # Pause duration in seconds (default: 15 minutes)
THROTTLE_DELAY: float = 0.5  # Delay (in seconds) between processing rows

# --- Define tv_channel_games Table Schema (autoload current schema) ---
tv_channel_games_table = Table("tv_channel_games", metadata, autoload_with=engine)
Session = sessionmaker(bind=engine)
session = Session()

# --- Utility Functions ---


def parse_elo(value: str) -> int | None:
    """
    Convert an Elo value to an integer.
    Returns None if conversion fails.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def is_valid_url(site: str) -> bool:
    """
    Validate a Lichess game URL.
    Expected format: "https://lichess.org/<alphanumeric>"
    """
    pattern = r"^https://lichess\.org/[a-zA-Z0-9]+$"
    return re.match(pattern, site or "") is not None


def should_keep_row(row) -> tuple[bool, str]:
    """
    Determine if a row has the minimum required fields: white, black, moves, and result.

    Returns:
        (bool, str): True and an empty string if the row is valid, or False and an error message.
    """
    required_fields = ["white", "black", "moves", "result"]
    for field in required_fields:
        value = getattr(row, field, None)
        if not value or str(value).strip() == "":
            return False, f"Missing required field: {field}"
    valid_results = {"1-0", "0-1", "1/2-1/2", "*"}
    if row.result not in valid_results:
        return False, f"Invalid result value: {row.result}"
    return True, ""


def validate_and_clean() -> None:
    """
    Validate and clean rows in tv_channel_games that have not been updated.

    For each row:
      1. Check that required fields are present.
      2. Validate the URL format and update the 'url_valid' flag accordingly.
      3. Clean Elo values.
      4. Mark the row as updated and commit changes.
    Logs progress and final statistics.
    """
    rows = session.execute(
        select(tv_channel_games_table).where(tv_channel_games_table.c.updated == False)
    ).fetchall()
    total_rows = len(rows)
    logger.info(f"Starting validation on {total_rows} rows from tv_channel_games.")

    total_deleted = 0
    total_updated = 0
    start_time = time.time()
    last_summary_time = start_time

    for row in rows:
        game_id = row.id
        # Check required fields.
        valid, error_message = should_keep_row(row)
        if not valid:
            logger.info(f"Game {game_id}: Dropping row due to: {error_message}")
            session.execute(
                delete(tv_channel_games_table).where(
                    tv_channel_games_table.c.id == game_id
                )
            )
            total_deleted += 1
            continue

        # Validate URL.
        site = row.site or ""
        if not is_valid_url(site):
            logger.info(f"Game {game_id}: Invalid URL '{site}'. Marking as invalid.")
            session.execute(
                update(tv_channel_games_table)
                .where(tv_channel_games_table.c.id == game_id)
                .values(url_valid=False)
            )
        else:
            session.execute(
                update(tv_channel_games_table)
                .where(tv_channel_games_table.c.id == game_id)
                .values(url_valid=True)
            )

        # Clean Elo values.
        cleaned_white_elo = parse_elo(row.white_elo)
        cleaned_black_elo = parse_elo(row.black_elo)

        # Update row with cleaned values and mark as processed.
        session.execute(
            update(tv_channel_games_table)
            .where(tv_channel_games_table.c.id == game_id)
            .values(
                white_elo=cleaned_white_elo,
                black_elo=cleaned_black_elo,
                updated=True,
                is_valid=True,
                validation_errors="",
            )
        )
        total_updated += 1

        # Log progress every PAUSE_AFTER rows (or adjust as needed).
        if (total_deleted + total_updated) % 30 == 0:
            logger.info(f"Processed {total_deleted + total_updated}/{total_rows} rows.")
        time.sleep(THROTTLE_DELAY)

    session.commit()
    logger.info(
        f"Validation complete. Total updated: {total_updated}, Total deleted: {total_deleted}"
    )


if __name__ == "__main__":
    validate_and_clean()
