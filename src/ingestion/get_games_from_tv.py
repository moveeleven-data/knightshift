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
    select,
    update,
)
from sqlalchemy.orm import sessionmaker

# -------------------------------------------------------------------
# Add the project root (knightshift/) to the Python path.
# -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# -------------------------------------------------------------------
# Imports from src.utils
# -------------------------------------------------------------------
from src.utils.db_utils import load_db_credentials, get_database_url, get_lichess_token
from src.utils.logging_utils import setup_logger
from src.utils.pgn_parser import parse_pgn_lines

# -------------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------------
logger = setup_logger(name="get_games_from_tv", level=logging.INFO)

# -------------------------------------------------------------------
# Environment & Configuration
# -------------------------------------------------------------------
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env.local")
creds = load_db_credentials()
logger.info("Loaded DB credentials successfully.")

DATABASE_URL = get_database_url(creds)
engine = create_engine(DATABASE_URL)
metadata = MetaData()

TIME_LIMIT = int(os.getenv("TIME_LIMIT", 60))
SLEEP_INTERVAL = int(os.getenv("SLEEP_INTERVAL", 40))
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
# Utility / Helper Functions
# -------------------------------------------------------------------
def parse_rating(rating_value: str) -> int | None:
    """
    Safely parse a rating string into an int. Returns None on failure.
    """
    try:
        return int(rating_value)
    except (ValueError, TypeError):
        return None


def build_game_data(game: dict) -> dict:
    """
    Convert parsed PGN dictionary into a data structure suitable for DB insertion.
    """
    return {
        "id": game.get("site", "").split("/")[-1],
        "event": game.get("event", ""),
        "site": game.get("site", ""),
        "date": (
            datetime.strptime(game.get("date", "1970.01.01"), "%Y.%m.%d").date()
            if game.get("date")
            else None
        ),
        "white": game.get("white", ""),
        "black": game.get("black", ""),
        "result": game.get("result", ""),
        "utc_date": (
            datetime.strptime(game.get("utcdate", "1970.01.01"), "%Y.%m.%d").date()
            if game.get("utcdate")
            else None
        ),
        "utc_time": (
            datetime.strptime(game.get("utctime", "00:00:00"), "%H:%M:%S").time()
            if game.get("utctime")
            else None
        ),
        "white_elo": parse_rating(game.get("whiteelo")),
        "black_elo": parse_rating(game.get("blackelo")),
        "white_title": game.get("whitetitle", ""),
        "black_title": game.get("blacktitle", ""),
        "variant": game.get("variant", ""),
        "time_control": game.get("timecontrol", ""),
        "eco": game.get("eco", ""),
        "termination": game.get("termination", ""),
        "moves": game.get("moves", ""),
    }


def upsert_game(game_data: dict) -> bool:
    """
    Upsert (insert or update) a game record into tv_channel_games.
    Return:
        True if record was updated,
        False if inserted or if no valid game_id is found.
    """
    game_id = game_data.get("id")
    if not game_id:
        logger.warning("No valid game ID found; skipping row.")
        return False

    existing_game = session.execute(
        select(tv_channel_games_table).where(tv_channel_games_table.c.id == game_id)
    ).fetchone()

    if existing_game is None:
        session.execute(tv_channel_games_table.insert().values(game_data))
        session.commit()
        logger.info(f"Inserted new game {game_id}.")
        return False  # Means inserted
    else:
        session.execute(
            update(tv_channel_games_table)
            .where(tv_channel_games_table.c.id == game_id)
            .values(game_data)
        )
        session.commit()
        logger.info(f"Updated existing game {game_id}.")
        return True  # Means updated


def process_pgn_block(
    pgn_lines: list[bytes], updated_games: list[str], added_games: list[str]
):
    """
    Parse a block of PGN lines, build the game data, and upsert into DB.
    Collect IDs of updated vs. added games in provided lists.
    """
    game_dict = parse_pgn_lines(pgn_lines)
    if "site" in game_dict:
        data_for_db = build_game_data(game_dict)
        was_updated = upsert_game(data_for_db)
        game_id = data_for_db["id"]
        if was_updated:
            updated_games.append(game_id)
        else:
            added_games.append(game_id)


# -------------------------------------------------------------------
# Core Ingestion Functions
# -------------------------------------------------------------------
def fetch_ongoing_games(
    channel: str, updated_games: list[str], added_games: list[str], max_retries=3
):
    """
    Fetch ongoing games from Lichess TV for a specific channel and upsert them.
    Retries on non-429 errors, streams PGN data line by line.
    """
    url = f"https://lichess.org/api/tv/{channel}"
    params = {"clocks": False, "opening": False}
    for attempt in range(1, max_retries + 1):
        response = http_session.get(url, params=params, stream=True)
        if response.status_code == 429:
            logger.error(
                f"Rate limit encountered on channel '{channel}'. Exiting pipeline."
            )
            sys.exit(1)
        if response.status_code == 200:
            # Successful response, proceed
            break
        else:
            logger.warning(
                f"Channel '{channel}' request failed with {response.status_code}. "
                f"Retry {attempt}/{max_retries}."
            )
            time.sleep(5)
    else:
        logger.error(
            f"Failed to connect to channel '{channel}' after {max_retries} retries."
        )
        return  # Stop this channel

    if response.status_code == 200:
        parse_and_upsert_response(response, updated_games, added_games)
    else:
        logger.error(
            f"Failed to connect to channel '{channel}': {response.status_code}, {response.text}"
        )


def parse_and_upsert_response(
    response, updated_games: list[str], added_games: list[str]
):
    """
    Given a streaming response from Lichess TV,
    parse PGN blocks and upsert them into the DB.
    """
    pgn_lines = []
    for line in response.iter_lines():
        if line.strip():
            pgn_lines.append(line)
        else:
            # Blank line => one complete PGN block
            if pgn_lines:
                process_pgn_block(pgn_lines, updated_games, added_games)
                pgn_lines = []


def run_tv_ingestion():
    """
    Main loop over Lichess TV channels. Continues ingesting until TIME_LIMIT is reached or
    MAX_GAMES is fetched (triggering a RATE_LIMIT_PAUSE).
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
        updated_games: list[str] = []
        added_games: list[str] = []

        # Fetch games for each channel
        for channel in channels:
            fetch_ongoing_games(channel, updated_games, added_games)
            # Optional channel-specific logging
            if channel in {"rapid", "horde", "kingOfTheHill"}:
                logger.info(f"Fetching '{channel}' games...")

        # Summarize batch
        logger.info(
            f"Batch complete: {len(updated_games)} updated, {len(added_games)} added."
        )
        total_games_count += len(updated_games) + len(added_games)

        # Check if we've hit the max limit
        if total_games_count >= MAX_GAMES:
            logger.info(f"Fetched {MAX_GAMES} games. Pausing for 15 minutes...")
            time.sleep(RATE_LIMIT_PAUSE)
            total_games_count = 0  # Reset counter

        # Slight delay before next loop
        logger.info("Still connected and fetching next batch of games...")
        time.sleep(SLEEP_INTERVAL)

    logger.info("Time limit reached. Stopping ingestion.")


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    run_tv_ingestion()
