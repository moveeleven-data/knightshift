#!/usr/bin/env python3
"""
update_all_games.py

This script enriches and updates game records in the tv_channel_games table.
It fetches full PGN data from Lichess for finished games that have not yet been updated,
parses the PGN to extract moves and metadata, and then updates the corresponding
database records. Structured logging is used for production-grade traceability.
"""

import sys
from pathlib import Path
import os
import time
import logging
import re
from datetime import datetime
from typing import Tuple, Optional, Dict

from dotenv import load_dotenv
import requests
from requests.exceptions import HTTPError
from sqlalchemy import (
    create_engine,
    Table,
    Column,
    String,
    MetaData,
    update,
    select,
    Boolean,
    Integer,
    Date,
    Time,
    text,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# --- Add Project Root to Python Path ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# --- Import Shared Utilities ---
from src.utils.db_utils import load_db_credentials, get_database_url, get_lichess_token
from src.utils.logging_utils import setup_logger
from src.utils.pgn_parser import parse_game_data_from_pgn, extract_moves_from_pgn

# --- Logging Setup ---
logger = setup_logger(name="update_all_games", level=logging.INFO)

# --- Environment & Configuration ---
load_dotenv(dotenv_path=Path(__file__).resolve().parent / "config" / ".env.local")
creds = load_db_credentials()
logger.info("Loaded DB credentials successfully.")
DATABASE_URL = get_database_url(creds)
engine = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=10, max_overflow=20)
metadata = MetaData()

# --- Table Definition ---
tv_channel_games_table = Table(
    "tv_channel_games",
    metadata,
    Column("id", String, primary_key=True),
    Column("moves", String),
    Column("updated", Boolean, default=False),
    Column("result", String),
    Column("termination", String),
    Column("utc_date", Date),
    Column("utc_time", Time),
    Column("white_elo", Integer),
    Column("black_elo", Integer),
    Column("variant", String),
    Column("time_control", String),
    Column("eco", String),
    Column("opening", String),
)
Session = sessionmaker(bind=engine)
session = Session()

# --- HTTP Session Setup ---
http_session = requests.Session()
http_session.headers.update(
    {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {get_lichess_token()}",
    }
)


def safe_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def fetch_game_moves(game_id: str) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    url = f"https://lichess.org/game/export/{game_id}"
    response = http_session.get(url, stream=True)
    if response.status_code == 200:
        pgn_text = response.text
        game_data = parse_game_data_from_pgn(pgn_text)
        moves = extract_moves_from_pgn(pgn_text)
        return moves, game_data
    elif response.status_code == 401:
        logger.error(f"Unauthorized (401) for game {game_id}. Skipping.")
    elif response.status_code == 429:
        logger.error(f"Rate limit hit. Exiting.")
        sys.exit(1)
    else:
        logger.error(
            f"Failed to fetch game {game_id}: {response.status_code}, {response.text}"
        )
    return None, None


def update_game_record(game_id: str, moves: str, game_data: Dict[str, str]) -> None:
    white_elo = safe_int(game_data.get("white_elo"))
    black_elo = safe_int(game_data.get("black_elo"))
    finished = (
        game_data.get("result") != "*"
        and game_data.get("termination") != "Unterminated"
    )
    update_values = {
        "moves": moves,
        "result": game_data.get("result"),
        "termination": game_data.get("termination"),
        "utc_date": game_data.get("utc_date"),
        "utc_time": game_data.get("utc_time"),
        "white_elo": white_elo,
        "black_elo": black_elo,
        "variant": game_data.get("variant"),
        "time_control": game_data.get("time_control"),
        "eco": game_data.get("eco"),
        "opening": game_data.get("opening"),
        "updated": finished,
    }
    session.execute(
        update(tv_channel_games_table)
        .where(tv_channel_games_table.c.id == game_id)
        .values(update_values)
    )
    session.commit()
    logger.info(f"Updated game record {game_id} (finished: {finished}).")


def run_update_pass() -> None:
    batch_size = 1000
    total_updated = 0
    total_failed = 0
    start_time = time.time()

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM tv_channel_games WHERE updated = FALSE;")
        )
        total_to_update = result.scalar()

    logger.info(f"Total games to update: {total_to_update}")

    while True:
        games = session.execute(
            select(tv_channel_games_table)
            .where(tv_channel_games_table.c.updated == False)
            .limit(batch_size)
        ).fetchall()

        if not games:
            break

        for game in games:
            game_id = game.id
            moves, game_data = fetch_game_moves(game_id)
            if moves and game_data:
                update_game_record(game_id, moves, game_data)
                total_updated += 1
            else:
                total_failed += 1

            time.sleep(0.5)

            if (total_updated + total_failed) % 50 == 0:
                elapsed = time.time() - start_time
                pct = (
                    ((total_updated + total_failed) / total_to_update) * 100
                    if total_to_update > 0
                    else 0
                )
                eta_sec = (
                    (
                        (elapsed / (total_updated + total_failed))
                        * (total_to_update - (total_updated + total_failed))
                    )
                    if (total_updated + total_failed) > 0 and total_to_update > 0
                    else 0
                )
                logger.info(
                    f"Processed: {total_updated + total_failed}, Updated: {total_updated}, Failed: {total_failed}, "
                    f"Progress: {pct:.2f}%, ETA: {eta_sec / 60:.2f} min"
                )

    elapsed = time.time() - start_time
    completion_pct = (
        (total_updated / (total_updated + total_failed)) * 100
        if (total_updated + total_failed) > 0
        else 0
    )
    logger.info(
        f"Update complete. Updated: {total_updated}, Failed: {total_failed}, "
        f"Completion: {completion_pct:.2f}%, Time: {elapsed:.2f} sec"
    )


if __name__ == "__main__":
    run_update_pass()
