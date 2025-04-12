#!/usr/bin/env python3
"""
validate_tv_channel_games.py

This script validates and cleans rows in the tv_channel_games table.
It ensures that each row has the required fields (white, black, moves, result),
cleans Elo values, and then updates or deletes the row accordingly.
Configuration parameters are read from environment variables.
Logs are written to both the console and a timestamped log file.
"""

import sys
from pathlib import Path
import os
import time
from datetime import datetime
import logging

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Table,
    MetaData,
    select,
    delete,
    update,
    Integer,
    String,
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
logger.info("Loaded DB credentials successfully.")
DATABASE_URL = get_database_url(creds)
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Configuration parameters
TIME_LIMIT = int(os.getenv("TIME_LIMIT", 60))  # Total runtime in seconds (for testing)
SLEEP_INTERVAL = int(os.getenv("SLEEP_INTERVAL", 40))  # Seconds between batches
PAUSE_AFTER = int(os.getenv("PAUSE_AFTER", 2500))  # Rows processed before pausing
PAUSE_DURATION = int(os.getenv("PAUSE_DURATION", 900))  # Pause duration in seconds
THROTTLE_DELAY = 0  # Delay (in seconds) between processing rows

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


def should_keep_row(row) -> tuple[bool, str]:
    """
    Check that a row has the minimum required fields: white, black, moves, and result.

    Returns:
        (bool, str): (True, "") if valid; otherwise, (False, error_message)
    """
    required_fields = ["white", "black", "moves", "result"]
    for field in required_fields:
        value = getattr(row, field, None)
        if not value or str(value).strip() == "":
            return False, f"Missing required field: {field}"
    valid_results = {"1-0", "0-1", "1/2-1/2"}
    if row.result not in valid_results:
        return False, f"Invalid result value: {row.result}"
    return True, ""


def process_row(row) -> tuple[bool, bool]:
    """
    Process a single row:
      - Validates required fields
      - Cleans Elo values
      - Updates or drops the row accordingly

    Returns:
        (processed, was_deleted):
            processed: True if the row was processed (updated or deleted)
            was_deleted: True if the row was deleted
    """
    game_id = row.id
    try:
        # Check required fields
        valid, error_message = should_keep_row(row)
        if not valid:
            logger.info(f"Game {game_id}: Dropping row due to: {error_message}")
            session.execute(
                delete(tv_channel_games_table).where(
                    tv_channel_games_table.c.id == game_id
                )
            )
            return True, True

        # Clean Elo values
        cleaned_white_elo = parse_elo(row.white_elo)
        cleaned_black_elo = parse_elo(row.black_elo)

        # Mark row as updated + is_valid
        session.execute(
            update(tv_channel_games_table)
            .where(tv_channel_games_table.c.id == game_id)
            .values(
                white_elo=cleaned_white_elo,
                black_elo=cleaned_black_elo,
                is_validated=True
            )
        )
        return True, False

    except Exception as e:
        logger.error(f"Error processing game {game_id}: {e}")
        session.rollback()
        return False, False


def validate_and_clean() -> None:
    """
    Validate and clean rows in tv_channel_games that have not been updated.
    Logs progress and final statistics.
    """
    rows = session.execute(
        select(tv_channel_games_table).where(tv_channel_games_table.c.is_validated == False)
    ).fetchall()
    total_rows = len(rows)
    logger.info(f"Starting validation on {total_rows} rows from tv_channel_games.")

    total_deleted = 0
    total_updated = 0

    start_time = time.time()

    for row in rows:
        try:
            processed, was_deleted = process_row(row)
            if processed:
                if was_deleted:
                    total_deleted += 1
                else:
                    total_updated += 1
        except Exception as e:
            logger.error(f"Unexpected error processing row {row.id}: {e}")
            continue

        # Log progress every 30 rows
        processed_so_far = total_deleted + total_updated
        if processed_so_far % 30 == 0:
            logger.info(f"Processed {processed_so_far}/{total_rows} rows.")
        time.sleep(THROTTLE_DELAY)

    session.commit()
    logger.info(
        f"Validation complete. Total updated: {total_updated}, Total deleted: {total_deleted}"
    )


if __name__ == "__main__":
    validate_and_clean()
