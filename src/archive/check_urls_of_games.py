#!/usr/bin/env python3
"""
validate_tv_channel_games.py

This script validates and cleans rows in the tv_channel_games table.
It checks that each row has the minimum required fields (white, black, moves, result),
validates URL format, cleans Elo values, and then updates or drops rows accordingly.
Logs are written to both the console and a timestamped file for production-grade traceability.
"""

import sys
from pathlib import Path

# Add the project root (knightshift/) to the Python path so that 'src' is importable.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# --- Import Shared Utilities ---
from utils.db_utils import load_db_credentials, get_database_url
from utils.logging_utils import setup_logger

import os
import re
import time
import logging
from datetime import datetime
import requests
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

# --- Logging Setup using our centralized utility ---
logger = setup_logger(name="validate_tv_channel_games", level=logging.INFO)

# --- Environment and DB Setup ---
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env.local")
creds = load_db_credentials()
logger.info(
    "Loaded DB credentials successfully."
)  # In production, mask sensitive details.
DATABASE_URL = get_database_url(creds)
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Use autoload to read the current schema (which includes any recent changes)
tv_channel_games_table = Table("tv_channel_games", metadata, autoload_with=engine)

Session = sessionmaker(bind=engine)
session = Session()

# --- Utility Functions ---


def parse_elo(value):
    """Convert an Elo value to integer; return None if conversion fails."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def is_valid_url(site):
    """
    Validate the Lichess game URL.
    Expected format: "https://lichess.org/<alphanumeric>"
    """
    pattern = r"^https://lichess\.org/[a-zA-Z0-9]+$"
    return re.match(pattern, site or "") is not None


def should_keep_row(row):
    """
    Determine if a row has the minimum required fields:
      white, black, moves, and result.
    Returns:
        tuple: (bool, str) where bool is True if valid, and str contains an error message if not.
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


def validate_and_clean():
    """
    Validate and clean rows in tv_channel_games that have not been updated.
    - Drop rows missing required fields.
    - Validate URL format and update accordingly.
    - Clean Elo values and mark the row as updated.
    Logs progress and final statistics.
    """
    rows = session.execute(
        select(tv_channel_games_table).where(tv_channel_games_table.c.updated == False)
    ).fetchall()
    total_rows = len(rows)
    logger.info(f"Starting validation on {total_rows} rows from tv_channel_games.")

    total_deleted = 0
    total_updated = 0

    for row in rows:
        game_id = row.id
        valid, reason = should_keep_row(row)
        if not valid:
            logger.info(f"Game {game_id}: Dropping row due to: {reason}")
            session.execute(
                delete(tv_channel_games_table).where(
                    tv_channel_games_table.c.id == game_id
                )
            )
            total_deleted += 1
            continue

        # Validate URL
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

        # Clean Elo values
        cleaned_white_elo = parse_elo(row.white_elo)
        cleaned_black_elo = parse_elo(row.black_elo)

        # Update the row with cleaned values and mark as updated.
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

        # Log progress every 30 rows.
        if (total_deleted + total_updated) % 30 == 0:
            logger.info(f"Processed {total_deleted + total_updated}/{total_rows} rows.")
        time.sleep(0.5)  # Throttle processing

    session.commit()
    logger.info(
        f"Validation complete. Total updated: {total_updated}, Total deleted: {total_deleted}"
    )


if __name__ == "__main__":
    validate_and_clean()
