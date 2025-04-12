#!/usr/bin/env python3
"""
validate_tv_channel_games.py

Validates and cleans rows in the tv_channel_games table.
Ensures required fields are present, cleans Elo values, handles ECO normalization,
and deletes or updates rows accordingly.
"""

import os
import sys
import time
from pathlib import Path
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
    Column,
    DateTime,
    Boolean,
)
from sqlalchemy.orm import sessionmaker

# --- Setup ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
from utils.db_utils import load_db_credentials, get_database_url
from utils.logging_utils import setup_logger

logger = setup_logger("validate_tv_channel_games")
load_dotenv(Path(__file__).resolve().parent / ".env.local")

# --- DB Setup ---
creds = load_db_credentials()
DATABASE_URL = get_database_url(creds)
engine = create_engine(DATABASE_URL)
metadata = MetaData()
tv_channel_games = Table("tv_channel_games", metadata, autoload_with=engine)
Session = sessionmaker(bind=engine)
session = Session()

# --- Config ---
THROTTLE_DELAY = 0


# --- Validators ---
def parse_elo(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def is_row_valid(row):
    required = ["white", "black", "moves", "result"]
    for field in required:
        if not getattr(row, field, None):
            return False, f"Missing field: {field}"
    if row.result not in {"1-0", "0-1", "1/2-1/2"}:
        return False, f"Invalid result: {row.result}"
    return True, ""


# --- Processing Logic ---
def process_row(row):
    game_id = row.id
    notes = []

    valid, msg = is_row_valid(row)
    if not valid:
        notes.append(msg)
        session.execute(
            delete(tv_channel_games).where(tv_channel_games.c.id == game_id)
        )
        return True, True

    # Elo cleaning
    white_elo = parse_elo(row.white_elo)
    black_elo = parse_elo(row.black_elo)
    if row.white_elo is not None and white_elo is None:
        notes.append("Invalid white_elo")
    if row.black_elo is not None and black_elo is None:
        notes.append("Invalid black_elo")

    # ECO normalization
    eco = None if getattr(row, "eco", None) == "?" else row.eco
    if row.eco == "?":
        notes.append("Set ECO to NULL")

    session.execute(
        update(tv_channel_games)
        .where(tv_channel_games.c.id == game_id)
        .values(
            white_elo=white_elo,
            black_elo=black_elo,
            eco=eco,
            is_validated=True,
            validation_notes=", ".join(notes) if notes else "Valid",
        )
    )
    return True, False


# --- Main Runner ---
def validate_and_clean():
    rows = session.execute(
        select(tv_channel_games).where(tv_channel_games.c.is_validated.is_(False))
    ).fetchall()

    logger.info(f"Starting validation on {len(rows)} rows.")
    total_updated = total_deleted = 0

    for i, row in enumerate(rows, start=1):
        try:
            processed, deleted = process_row(row)
            if processed:
                total_deleted += deleted
                total_updated += not deleted
        except Exception as e:
            logger.error(f"Error processing {row.id}: {e}")
            session.rollback()
        if i % 30 == 0:
            logger.info(f"Processed {i}/{len(rows)} rows.")
        time.sleep(THROTTLE_DELAY)

    session.commit()
    logger.info(
        f"Validation complete. Updated: {total_updated}, Deleted: {total_deleted}"
    )


if __name__ == "__main__":
    validate_and_clean()
