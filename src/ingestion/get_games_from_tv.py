#!/usr/bin/env python3
"""
get_games_from_tv.py

Streams live chess games from Lichess TV channels,
parses PGN data (via pgn_parser), and upserts records into PostgreSQL.
"""

import sys
import logging
import os
import time
from pathlib import Path
from datetime import datetime
from typing import List

import requests
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Table,
    Column,
    Integer,
    String,
    Date,
    Time,
    MetaData,
    DateTime,
)
from sqlalchemy.orm import sessionmaker

# -------------------------------------------------------------------
# Add the project root (knightshift/) to the Python path.
# -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# -------------------------------------------------------------------
# Imports from src.utils and src.db
# -------------------------------------------------------------------
from src.utils.db_utils import load_db_credentials, get_database_url, get_lichess_token
from src.utils.logging_utils import setup_logger
from src.utils.pgn_parser import parse_pgn_lines
from src.db.game_upsert import build_game_data, upsert_game

# -------------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------------
logger = setup_logger(name="get_games_from_tv", level=logging.INFO)

# -------------------------------------------------------------------
# Environment & Configuration
# -------------------------------------------------------------------
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / "config" / ".env.local")
creds = load_db_credentials()
print("Loaded PGHOST =", os.getenv("PGHOST"))
print("RUNNING_IN_DOCKER =", os.getenv("RUNNING_IN_DOCKER"))
logger.info("Loaded DB credentials successfully.")

DATABASE_URL = get_database_url(creds)
engine = create_engine(DATABASE_URL)
metadata = MetaData()

TIME_LIMIT = int(os.getenv("TIME_LIMIT", 30))
SLEEP_INTERVAL = int(os.getenv("SLEEP_INTERVAL", 5))
RATE_LIMIT_PAUSE = int(os.getenv("RATE_LIMIT_PAUSE", 900))
MAX_GAMES = int(os.getenv("MAX_GAMES", 5000))

# -------------------------------------------------------------------
# Table Schema Definition
# -------------------------------------------------------------------
tv_channel_games_table = Table(
    "tv_channel_games",
    metadata,
    Column("id", String, primary_key=True),
    Column("event", String),
    Column("site", String),
    Column("date", Date),
    Column("white", String),
    Column("black", String),
    Column("result", String),
    Column("utc_date", Date),
    Column("utc_time", Time),
    Column("white_elo", Integer),
    Column("black_elo", Integer),
    Column("white_title", String),
    Column("black_title", String),
    Column("variant", String),
    Column("time_control", String),
    Column("eco", String),
    Column("termination", String),
    Column("moves", String),
    Column("opening", String),
    Column("ingested_at", DateTime),
)

Session = sessionmaker(bind=engine)
session = Session()

# -------------------------------------------------------------------
# HTTP Session Setup
# -------------------------------------------------------------------
http_session = requests.Session()
http_session.headers.update(
    {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {get_lichess_token()}",
    }
)


# -------------------------------------------------------------------
# Core Ingestion Functions
# -------------------------------------------------------------------
def process_pgn_block(
    pgn_lines: List[bytes], updated_games: List[str], added_games: List[str]
) -> None:
    """
    Parse a block of PGN lines, build the game data, and upsert into DB.
    Collect IDs of updated vs. added games in provided lists.
    """
    game_dict = parse_pgn_lines(pgn_lines)

    if "site" in game_dict:
        data_for_db = build_game_data(game_dict)
        was_updated = upsert_game(session, tv_channel_games_table, data_for_db)
        game_id = data_for_db["id"]
        if was_updated:
            updated_games.append(game_id)
        else:
            added_games.append(game_id)


def fetch_ongoing_games(
    channel: str, updated_games: List[str], added_games: List[str], max_retries: int = 3
) -> None:
    """
    Fetch ongoing games from the Lichess TV API for a specific channel and upsert them.
    Retries on non-429 errors, streams PGN data line by line.
    """
    url = f"https://lichess.org/api/tv/{channel}"
    params = {"clocks": False, "opening": True}
    for attempt in range(1, max_retries + 1):
        response = http_session.get(url, params=params, stream=True)
        if response.status_code == 429:
            logger.error(
                f"Rate limit encountered on channel '{channel}'. Exiting pipeline."
            )
            sys.exit(1)
        if response.status_code == 200:
            break
        else:
            logger.warning(
                f"Channel '{channel}' request failed with {response.status_code}. Retry {attempt}/{max_retries}."
            )
            time.sleep(5)
    else:
        logger.error(
            f"Failed to connect to channel '{channel}' after {max_retries} retries."
        )
        return

    if response.status_code == 200:
        parse_and_upsert_response(response, updated_games, added_games)
    else:
        logger.error(
            f"Failed to connect to channel '{channel}': {response.status_code}, {response.text}"
        )


def parse_and_upsert_response(
    response, updated_games: List[str], added_games: List[str]
) -> None:
    """
    Parses PGN blocks and upserts them to DB.
    A full game = header lines + 1 move line.
    """
    pgn_block = []

    for line in response.iter_lines():
        if not line:
            continue

        decoded = line.decode("utf-8").strip()
        logger.debug(f"PGN LINE: {decoded}")
        pgn_block.append(line)

        if decoded.startswith("1. "):  # move line = end of current game block
            process_pgn_block(pgn_block, updated_games, added_games)
            pgn_block = []  # reset for next game


def run_tv_ingestion() -> None:
    """
    Main loop over Lichess TV channels.
    Continues ingesting until TIME_LIMIT is reached or MAX_GAMES is fetched.
    """
    channels = [
        "bullet",
        "blitz",
        "classical",
        "rapid",
        "chess960",
        "antichess",
        "atomic",
        "horde",
        "crazyhouse",
        "bot",
        "computer",
        "kingOfTheHill",
        "threeCheck",
        "ultraBullet",
        "racingKings",
    ]
    start_time = time.time()
    total_games_count = 0

    while time.time() - start_time < TIME_LIMIT:
        updated_games: List[str] = []
        added_games: List[str] = []

        for channel in channels:
            logger.info(f"Fetching '{channel}' games...")
            fetch_ongoing_games(channel, updated_games, added_games)

        logger.info(
            f"Batch complete: {len(updated_games)} updated, {len(added_games)} added."
        )
        total_games_count += len(updated_games) + len(added_games)

        if total_games_count >= MAX_GAMES:
            logger.info(f"Fetched {MAX_GAMES} games. Pausing for 15 minutes...")
            time.sleep(RATE_LIMIT_PAUSE)
            total_games_count = 0

        logger.info("Still connected and fetching next batch of games...")
        time.sleep(SLEEP_INTERVAL)

    logger.info("Time limit reached. Stopping ingestion.")


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    run_tv_ingestion()
