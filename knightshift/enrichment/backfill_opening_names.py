#!/usr/bin/env python3
"""
backfill_opening_names.py
──────────────────────────
Fetch opening names and ECO codes from Lichess for games in the table that
don't have these fields populated.

The script:
1. Collects game IDs where `val_opening_name` or `val_opening_eco_code` is **NULL** or "?".
2. Pulls the game data from Lichess API based on the `gameId`.
3. Extracts the opening name and ECO code from the API response.
4. Updates the corresponding rows in the database with the fetched opening information.

Runtime limits, throttling, and batch pauses are controlled via constants in **Config**.
"""

# ───────────────────────────────────────────────────────────────────────────────
# Standard library imports
# ───────────────────────────────────────────────────────────────────────────────
import logging
import sys
import time
from pathlib import Path
from typing import Set, Tuple
from datetime import datetime

# ───────────────────────────────────────────────────────────────────────────────
# Third-party imports
# ───────────────────────────────────────────────────────────────────────────────
import requests
from dotenv import load_dotenv
from sqlalchemy import MetaData, String, Column, create_engine, select, Table, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from requests.exceptions import HTTPError

# ───────────────────────────────────────────────────────────────────────────────
# Local project imports (KnightShift-specific modules)
# ───────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # idempotent

from knightshift.utils.db_utils import load_db_credentials, get_database_url
from knightshift.utils.logging_utils import setup_logger
from knightshift.db.game_upsert import upsert_game  # Import the upsert helper

# ───────────────────────────────────────────────────────────────────────────────
# Environment and DB Setup
# ───────────────────────────────────────────────────────────────────────────────
load_dotenv(PROJECT_ROOT / "infra" / "compose" / ".env")

# Setup logger using the logging_utils.py for consistent logging across the project
LOGGER = setup_logger("backfill_opening_names", level=logging.DEBUG)

# Fetch DB credentials securely from AWS Secrets Manager
db_credentials = load_db_credentials()
DATABASE_URL = get_database_url(db_credentials)

# Setup database connection
ENGINE = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=10, max_overflow=20)
SESSION = sessionmaker(bind=ENGINE)  # sessionmaker object, not callable
METADATA = MetaData()

# ───────────────────────────────────────────────────────────────────────────────
# Table Models (Minimal Columns)
# ───────────────────────────────────────────────────────────────────────────────
GAMES_TABLE = Table(
    "tv_channel_games",
    METADATA,
    Column("id_game", String, primary_key=True),
    Column("val_opening_name", String, nullable=True),
    Column("val_opening_eco_code", String, nullable=True),
    Column("val_elo_white", String, nullable=True),  # Add val_elo_white column here
    Column("val_elo_black", String, nullable=True),  # Add val_elo_black column here
    Column("tm_validated", String, nullable=True),  # Add tm_validated column here
)

# ───────────────────────────────────────────────────────────────────────────────
# Configuration Constants
# ───────────────────────────────────────────────────────────────────────────────
TIME_PER_GAME = 0.5  # seconds between individual API calls
BATCH_SIZE = 3_000  # games processed before a long pause
BATCH_PAUSE = 15 * 60  # seconds to pause after each big batch
PROGRESS_INTERVAL = 30  # seconds between progress log lines
SCRIPT_TIME_LIMIT = 30  # hard stop (seconds) – keeps CI tests fast

# ───────────────────────────────────────────────────────────────────────────────
# Shared HTTP Session for API Calls
# ───────────────────────────────────────────────────────────────────────────────
HTTP = requests.Session()
HTTP.headers.update({"Content-Type": "application/x-www-form-urlencoded"})

# ═════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═════════════════════════════════════════════════════════════════════════


def _collect_unprofiled_games() -> Set[str]:
    """Return all distinct game IDs where opening info needs to be updated."""
    query = select(GAMES_TABLE.c.id_game).where(
        (GAMES_TABLE.c.val_opening_name.is_(None))
        | (GAMES_TABLE.c.val_opening_name == "?")
        | (GAMES_TABLE.c.val_opening_eco_code.is_(None))
        | (
            GAMES_TABLE.c.val_opening_eco_code == "?"
        )  # Handle both fields with "?" or NULL
        | (GAMES_TABLE.c.val_elo_white.is_(None))  # Handle missing elo_white
        | (GAMES_TABLE.c.val_elo_black.is_(None))  # Handle missing elo_black
    )
    LOGGER.debug("[backfill_opening_names] Query to fetch unprofiled games: %s", query)

    try:
        with SESSION() as session:
            rows = session.execute(query).fetchall()
            game_ids = {row[0] for row in rows}
            if not game_ids:
                LOGGER.info("[backfill_opening_names] No games need updating.")
            else:
                LOGGER.info(
                    f"[backfill_opening_names] Found {len(game_ids)} games to update."
                )
            session.commit()
        return game_ids
    except Exception as e:
        LOGGER.error(f"[backfill_opening_names] Error during database query: {e}")
        return set()


def _fetch_opening_info(game_id: str) -> Tuple[str, str, str, str]:
    """Fetch opening information (ECO and name), and Elo ratings for both players for a game using Lichess API."""
    url = f"https://lichess.org/game/export/{game_id}"
    params = {"moves": "true", "opening": "true"}  # Request opening and moves data
    LOGGER.debug(
        f"[backfill_opening_names] Fetching opening info for game {game_id}..."
    )

    try:
        response = HTTP.get(url, params=params)
        response.raise_for_status()  # Check for HTTP errors

        # Log the full response for debugging
        LOGGER.debug(
            f"[backfill_opening_names] Response for game {game_id}: {response.text}"
        )

        eco_code, opening_name = None, None
        elo_white, elo_black = None, None

        # Parse the opening information and Elo ratings from the response
        for line in response.text.splitlines():
            if line.startswith("[ECO "):
                eco_code = line.split('"')[1]
            elif line.startswith("[Opening "):
                opening_name = line.split('"')[1]
            elif line.startswith("[WhiteElo "):
                elo_white = line.split('"')[1]
            elif line.startswith("[BlackElo "):
                elo_black = line.split('"')[1]

        # Log extracted data for debugging
        LOGGER.debug(
            f"[backfill_opening_names] Extracted for game {game_id}: eco_code={eco_code}, opening_name={opening_name}, elo_white={elo_white}, elo_black={elo_black}"
        )

        return eco_code, opening_name, elo_white, elo_black

    except HTTPError as e:
        LOGGER.warning(
            f"[backfill_opening_names] Error fetching data for game {game_id}: {e}"
        )
    except Exception as e:
        LOGGER.warning(
            f"[backfill_opening_names] Error fetching opening info for game {game_id}: {e}"
        )
    return None, None, None, None


def _update_opening_info(
    game_id: str, eco_code: str, opening_name: str, elo_white: str, elo_black: str
) -> None:
    """Update the opening info for the game in the database using the upsert helper."""
    game_data = {
        "id_game": game_id,
        "val_opening_name": opening_name,
        "val_opening_eco_code": eco_code,
        "val_elo_white": elo_white,  # Add Elo rating for white player
        "val_elo_black": elo_black,  # Add Elo rating for black player
        "tm_validated": datetime.utcnow().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),  # Add timestamp when validated
    }

    try:
        with SESSION() as session:
            if eco_code and opening_name:
                updated = upsert_game(session, GAMES_TABLE, game_data)
                if updated:
                    LOGGER.info(
                        f"[backfill_opening_names] Updated game {game_id} with opening info."
                    )
                else:
                    LOGGER.warning(
                        f"[backfill_opening_names] Failed to update game {game_id}."
                    )
            else:
                LOGGER.warning(
                    f"[backfill_opening_names] No opening info for game {game_id}."
                )
            session.commit()  # Commit the transaction after the upsert
    except Exception as e:
        LOGGER.error(
            f"[backfill_opening_names] Error during database update for game {game_id}: {e}"
        )


# ═════════════════════════════════════════════════════════════════════════
# Main Processing Loop
# ═════════════════════════════════════════════════════════════════════════


def _process(game_ids: Set[str]) -> None:
    total = len(game_ids)
    LOGGER.info(
        f"[backfill_opening_names] Need to update {total} games (ETA {total * TIME_PER_GAME} seconds)."
    )

    start_time = last_log = time.time()
    processed = 0

    for game_id in game_ids:
        # Hard stop for CI / unit tests
        if time.time() - start_time > SCRIPT_TIME_LIMIT:
            LOGGER.warning(
                f"[backfill_opening_names] Time-limit reached – stopping early."
            )
            break

        eco_code, opening_name, elo_white, elo_black = _fetch_opening_info(game_id)
        if eco_code and opening_name:
            _update_opening_info(game_id, eco_code, opening_name, elo_white, elo_black)
            processed += 1

        # Periodic status report
        if time.time() - last_log > PROGRESS_INTERVAL:
            LOGGER.info(
                f"[backfill_opening_names] Progress {processed}/{total} (remaining {total - processed})"
            )
            last_log = time.time()

        # Rate-limiting and batch pauses
        time.sleep(TIME_PER_GAME)
        if processed % BATCH_SIZE == 0:
            LOGGER.info(
                f"[backfill_opening_names] Processed {processed} games – cooling off for {BATCH_PAUSE // 60} min."
            )
            time.sleep(BATCH_PAUSE)

    LOGGER.info(f"[backfill_opening_names] Finished processing {processed} games.")


# ═════════════════════════════════════════════════════════════════════════
# Entry-Point


def run_backfill_opening_names() -> None:
    """Entry point to start the backfill process."""
    game_ids = _collect_unprofiled_games()

    if not game_ids:
        LOGGER.info(
            f"[backfill_opening_names] All opening info is up-to-date – nothing to do."
        )
        return

    _process(game_ids)


if __name__ == "__main__":
    run_backfill_opening_names()
