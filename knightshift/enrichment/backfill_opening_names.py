#!/usr/bin/env python3
# ==============================================================================
# backfill_opening_names.py
# ------------------------------------------------------------------------------
# Fetches opening names and ECO codes from Lichess for games missing this data.
#
# Workflow:
#   1. Collect games missing opening/eco/elo fields
#   2. Call Lichess API /game/export/{id} with opening=true
#   3. Parse ECO code, opening name, Elo ratings
#   4. Upsert updates into tv_channel_games
# ==============================================================================

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Set, Tuple

import requests
from dotenv import load_dotenv
from requests.exceptions import HTTPError
from sqlalchemy import Column, MetaData, String, Table, create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# ------------------------------------------------------------------------------
# Path & Imports
# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knightshift.utils.db_utils import load_db_credentials, get_database_url
from knightshift.utils.logging_utils import setup_logger
from knightshift.db.game_upsert import upsert_game

# ------------------------------------------------------------------------------
# Environment & Logger
# ------------------------------------------------------------------------------

load_dotenv(PROJECT_ROOT / "infra" / "compose" / ".env")
LOGGER = setup_logger("backfill_opening_names")

# ------------------------------------------------------------------------------
# Database Setup
# ------------------------------------------------------------------------------

ENGINE = create_engine(
    get_database_url(load_db_credentials()),
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
)
SESSION = sessionmaker(bind=ENGINE)
METADATA = MetaData()

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

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------

TIME_PER_GAME = 0.5  # seconds per game
BATCH_SIZE = 3_000
BATCH_PAUSE = 15 * 60  # seconds
PROGRESS_INTERVAL = 30  # seconds
SCRIPT_TIME_LIMIT = 30  # seconds

# ------------------------------------------------------------------------------
# HTTP Session
# ------------------------------------------------------------------------------

HTTP = requests.Session()
HTTP.headers.update({"Content-Type": "application/x-www-form-urlencoded"})

# ==============================================================================
# Helpers
# ==============================================================================


def _collect_unprofiled_games() -> Set[str]:
    """Return set of game IDs missing opening/eco/elo information."""
    query = select(GAMES_TABLE.c.id_game).where(
        (GAMES_TABLE.c.val_opening_name.is_(None))
        | (GAMES_TABLE.c.val_opening_name == "?")
        | (GAMES_TABLE.c.val_opening_eco_code.is_(None))
        | (GAMES_TABLE.c.val_opening_eco_code == "?")
        | (GAMES_TABLE.c.val_elo_white.is_(None))
        | (GAMES_TABLE.c.val_elo_black.is_(None))
    )
    LOGGER.debug("Unprofiled games query: %s", query)

    try:
        with SESSION() as session:
            rows = session.execute(query).fetchall()
            game_ids = {row[0] for row in rows}
            if game_ids:
                LOGGER.info("Found %d games to update.", len(game_ids))
            else:
                LOGGER.info("No games need updating.")
            return game_ids
    except Exception as exc:
        LOGGER.error("Error fetching unprofiled games: %s", exc)
        return set()


def _fetch_opening_info(game_id: str) -> Tuple[str, str, str, str]:
    """Fetch ECO code, opening name, and Elo ratings for one game via Lichess API."""
    url = f"https://lichess.org/game/export/{game_id}"
    params = {"moves": "true", "opening": "true"}
    LOGGER.debug("Fetching opening info for game %s", game_id)

    try:
        resp = HTTP.get(url, params=params)
        resp.raise_for_status()
        LOGGER.debug("Response for game %s: %s", game_id, resp.text)

        eco_code = opening_name = elo_white = elo_black = None
        for line in resp.text.splitlines():
            if line.startswith("[ECO "):
                eco_code = line.split('"')[1]
            elif line.startswith("[Opening "):
                opening_name = line.split('"')[1]
            elif line.startswith("[WhiteElo "):
                elo_white = line.split('"')[1]
            elif line.startswith("[BlackElo "):
                elo_black = line.split('"')[1]

        return eco_code, opening_name, elo_white, elo_black

    except HTTPError as exc:
        LOGGER.warning("HTTP error for game %s: %s", game_id, exc)
    except Exception as exc:
        LOGGER.warning("Fetch error for game %s: %s", game_id, exc)
    return None, None, None, None


def _update_opening_info(
    game_id: str, eco_code: str, opening_name: str, elo_white: str, elo_black: str
) -> None:
    """Upsert ECO/opening/elo info for a game."""
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
                    LOGGER.info("Updated game %s", game_id)
                else:
                    LOGGER.warning("No changes applied for game %s", game_id)
            else:
                LOGGER.warning("Missing opening info for game %s", game_id)
            session.commit()
    except Exception as exc:
        LOGGER.error("Update error for game %s: %s", game_id, exc)


def _process(game_ids: Set[str]) -> None:
    """Process all unprofiled games with rate limiting and progress logs."""
    total = len(game_ids)
    LOGGER.info("Updating %d games (ETA %.1f s)", total, total * TIME_PER_GAME)

    start, last_log = time.time(), time.time()
    processed = 0

    for game_id in game_ids:
        if time.time() - start > SCRIPT_TIME_LIMIT:
            LOGGER.warning("Script time limit reached – stopping early.")
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

        if processed and processed % BATCH_SIZE == 0:
            LOGGER.info(
                "Processed %d games – pausing %d min", processed, BATCH_PAUSE // 60
            )
            time.sleep(BATCH_PAUSE)

    LOGGER.info("Finished processing %d games", processed)


def run_backfill_opening_names() -> None:
    """Main runner for backfilling opening names."""
    game_ids = _collect_unprofiled_games()
    if not game_ids:
        LOGGER.info("All opening info is up-to-date.")
        return
    _process(game_ids)


if __name__ == "__main__":
    run_backfill_opening_names()
