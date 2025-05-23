#!/usr/bin/env python3
"""
backfill_opening_names.py
──────────────────────────
Fetches opening names and ECO codes from Lichess for games missing this data.
"""

import logging
import sys
import time
from pathlib import Path
from typing import Set, Tuple
from datetime import datetime

import requests
from dotenv import load_dotenv
from sqlalchemy import MetaData, String, Column, create_engine, select, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from requests.exceptions import HTTPError

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knightshift.utils.db_utils import load_db_credentials, get_database_url
from knightshift.utils.logging_utils import setup_logger
from knightshift.db.game_upsert import upsert_game

# Load environment and initialize logger
load_dotenv(PROJECT_ROOT / "infra" / "compose" / ".env")
LOGGER = setup_logger("backfill_opening_names", level=logging.DEBUG)

# DB setup
db_credentials = load_db_credentials()
DATABASE_URL = get_database_url(db_credentials)
ENGINE = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=10, max_overflow=20)
SESSION = sessionmaker(bind=ENGINE)
METADATA = MetaData()

# Minimal table model
GAMES_TABLE = Table(
    "tv_channel_games",
    METADATA,
    Column("id_game", String, primary_key=True),
    Column("val_opening_name", String, nullable=True),
    Column("val_opening_eco_code", String, nullable=True),
    Column("val_elo_white", String, nullable=True),
    Column("val_elo_black", String, nullable=True),
    Column("tm_validated", String, nullable=True),
)

# Config
TIME_PER_GAME = 0.5
BATCH_SIZE = 3_000
BATCH_PAUSE = 15 * 60
PROGRESS_INTERVAL = 30
SCRIPT_TIME_LIMIT = 30

# Shared HTTP session
HTTP = requests.Session()
HTTP.headers.update({"Content-Type": "application/x-www-form-urlencoded"})


def _collect_unprofiled_games() -> Set[str]:
    query = select(GAMES_TABLE.c.id_game).where(
        (GAMES_TABLE.c.val_opening_name.is_(None))
        | (GAMES_TABLE.c.val_opening_name == "?")
        | (GAMES_TABLE.c.val_opening_eco_code.is_(None))
        | (GAMES_TABLE.c.val_opening_eco_code == "?")
        | (GAMES_TABLE.c.val_elo_white.is_(None))
        | (GAMES_TABLE.c.val_elo_black.is_(None))
    )
    LOGGER.debug("Query to fetch unprofiled games: %s", query)

    try:
        with SESSION() as session:
            rows = session.execute(query).fetchall()
            game_ids = {row[0] for row in rows}
            if game_ids:
                LOGGER.info("Found %d games to update.", len(game_ids))
            else:
                LOGGER.info("No games need updating.")
            return game_ids
    except Exception as e:
        LOGGER.error("Error during database query: %s", e)
        return set()


def _fetch_opening_info(game_id: str) -> Tuple[str, str, str, str]:
    url = f"https://lichess.org/game/export/{game_id}"
    params = {"moves": "true", "opening": "true"}
    LOGGER.debug("Fetching opening info for game %s...", game_id)

    try:
        response = HTTP.get(url, params=params)
        response.raise_for_status()
        LOGGER.debug("Response for game %s: %s", game_id, response.text)

        eco_code = opening_name = elo_white = elo_black = None
        for line in response.text.splitlines():
            if line.startswith("[ECO "):
                eco_code = line.split('"')[1]
            elif line.startswith("[Opening "):
                opening_name = line.split('"')[1]
            elif line.startswith("[WhiteElo "):
                elo_white = line.split('"')[1]
            elif line.startswith("[BlackElo "):
                elo_black = line.split('"')[1]

        LOGGER.debug(
            "Extracted for game %s: eco_code=%s, opening_name=%s, elo_white=%s, elo_black=%s",
            game_id,
            eco_code,
            opening_name,
            elo_white,
            elo_black,
        )

        return eco_code, opening_name, elo_white, elo_black

    except HTTPError as e:
        LOGGER.warning("HTTP error for game %s: %s", game_id, e)
    except Exception as e:
        LOGGER.warning("Fetch error for game %s: %s", game_id, e)
    return None, None, None, None


def _update_opening_info(
    game_id: str, eco_code: str, opening_name: str, elo_white: str, elo_black: str
) -> None:
    game_data = {
        "id_game": game_id,
        "val_opening_name": opening_name,
        "val_opening_eco_code": eco_code,
        "val_elo_white": elo_white,
        "val_elo_black": elo_black,
        "tm_validated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        with SESSION() as session:
            if eco_code and opening_name:
                updated = upsert_game(session, GAMES_TABLE, game_data)
                if updated:
                    LOGGER.info("Updated game %s.", game_id)
                else:
                    LOGGER.warning("Failed to update game %s.", game_id)
            else:
                LOGGER.warning("No opening info for game %s.", game_id)
            session.commit()
    except Exception as e:
        LOGGER.error("Update error for game %s: %s", game_id, e)


def _process(game_ids: Set[str]) -> None:
    total = len(game_ids)
    LOGGER.info(
        "Need to update %d games (ETA %.1f seconds).", total, total * TIME_PER_GAME
    )

    start_time = last_log = time.time()
    processed = 0

    for game_id in game_ids:
        if time.time() - start_time > SCRIPT_TIME_LIMIT:
            LOGGER.warning("Time-limit reached – stopping early.")
            break

        eco_code, opening_name, elo_white, elo_black = _fetch_opening_info(game_id)
        if eco_code and opening_name:
            _update_opening_info(game_id, eco_code, opening_name, elo_white, elo_black)
            processed += 1

        if time.time() - last_log > PROGRESS_INTERVAL:
            LOGGER.info(
                "Progress %d/%d (remaining %d)", processed, total, total - processed
            )
            last_log = time.time()

        time.sleep(TIME_PER_GAME)
        if processed % BATCH_SIZE == 0 and processed > 0:
            LOGGER.info(
                "Processed %d games – cooling off for %d min.",
                processed,
                BATCH_PAUSE // 60,
            )
            time.sleep(BATCH_PAUSE)

    LOGGER.info("Finished processing %d games.", processed)


def run_backfill_opening_names() -> None:
    game_ids = _collect_unprofiled_games()
    if not game_ids:
        LOGGER.info("All opening info is up-to-date – nothing to do.")
        return
    _process(game_ids)


if __name__ == "__main__":
    run_backfill_opening_names()
