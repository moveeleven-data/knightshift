#!/usr/bin/env python3
"""
get_games_from_tv.py
~~~~~~~~~~~~~~~~~~~~
Streams live chess games from **Lichess TV**, parses each PGN with
`parse_pgn_lines`, and **upserts** the results into PostgreSQL.

Execution flow
==============
1. Build a shared SQLAlchemy engine + session (credentials come from
   `config/.env.local` or AWS Secrets Manager via `load_db_credentials`).
2. For each TV channel (bullet, blitz, …) call the Lichess streaming API.
3. Read the PGN stream line‑by‑line, detect game boundaries, and upsert:
      • new games   → INSERT
      • duplicates  → UPDATE (see `upsert_game`)
4. Repeat until the configurable `TIME_LIMIT` or `MAX_GAMES` is reached.
"""

# ────────────────────────────────────────────────────────────────────────────────
# Future imports
# ────────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

# ────────────────────────────────────────────────────────────────────────────────
# Standard library imports
# ────────────────────────────────────────────────────────────────────────────────
import logging
import os
import sys
import time
from pathlib import Path
from typing import Final, List, Sequence

# ────────────────────────────────────────────────────────────────────────────────
# Third-party imports
# ────────────────────────────────────────────────────────────────────────────────
import requests
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Time,
    create_engine,
)
from sqlalchemy.orm import Session, sessionmaker

# ────────────────────────────────────────────────────────────────────────────────
# Local project imports (KnightShift-specific modules)
# ────────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # idempotent

from knightshift.db.game_upsert import build_game_data, upsert_game
from knightshift.utils.db_utils import (
    get_database_url,
    get_lichess_token,
    load_db_credentials,
)
from knightshift.utils.logging_utils import setup_logger
from knightshift.utils.pgn_parser import parse_pgn_lines

# ──────────────────────────────────────────────────────────────────────────
#   Environment & config
# ──────────────────────────────────────────────────────────────────────────
ENV_FILE = PROJECT_ROOT / ".env.local"
load_dotenv(ENV_FILE)

LOGGER = setup_logger("get_games_from_tv", level=logging.INFO)

# numeric env‑vars with sane fall‑backs
TIME_LIMIT: Final[int] = int(os.getenv("TIME_LIMIT", 90))  # seconds
SLEEP_INTERVAL: Final[int] = int(os.getenv("SLEEP_INTERVAL", 5))  # seconds
RATE_LIMIT_PAUSE: Final[int] = int(os.getenv("RATE_LIMIT_PAUSE", 900))
MAX_GAMES: Final[int] = int(os.getenv("MAX_GAMES", 5000))

CHANNELS: Final[Sequence[str]] = (
    "bullet",
    "blitz",
    "classical",
    "rapid",
    "ultraBullet",
)

# ──────────────────────────────────────────────────────────────────────────
#   Database setup
# ──────────────────────────────────────────────────────────────────────────
CREDS = load_db_credentials()
ENGINE = create_engine(get_database_url(CREDS))
SESSION: Session = sessionmaker(bind=ENGINE)()

METADATA = MetaData()
TV_GAMES_TBL = Table(
    "tv_channel_games",
    METADATA,
    Column("id_game", String, primary_key=True),
    Column("val_event_name", String),
    Column("val_site_url", String),
    Column("dt_game", Date),
    Column("id_user_white", String),
    Column("id_user_black", String),
    Column("val_result", String),
    Column("dt_game_utc", Date),
    Column("tm_game_utc", Time),
    Column("val_elo_white", Integer),
    Column("val_elo_black", Integer),
    Column("val_title_white", String),
    Column("val_title_black", String),
    Column("val_variant", String),
    Column("val_time_control", String),
    Column("val_opening_eco_code", String),
    Column("val_termination", String),
    Column("val_moves_pgn", String),
    Column("val_opening_name", String),
    Column("tm_ingested", DateTime),
)

# ──────────────────────────────────────────────────────────────────────────
#   Lichess API session
# ──────────────────────────────────────────────────────────────────────────
HTTP = requests.Session()
HTTP.headers.update(
    {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {get_lichess_token()}",
    }
)


# ──────────────────────────────────────────────────────────────────────────
#   Helper functions
# ──────────────────────────────────────────────────────────────────────────
def _process_game_block(
    pgn_lines: List[bytes], added: List[str], updated: List[str]
) -> None:
    """Parse a single PGN block and upsert it into Postgres."""
    # Parse PGN lines into game data
    game = parse_pgn_lines(pgn_lines)

    if "site" not in game:  # sanity guard
        return

    # Build the database row from the parsed PGN data
    db_row = build_game_data(game)

    # Perform the upsert operation (insert or update)
    was_updated = upsert_game(SESSION, TV_GAMES_TBL, db_row)

    (updated if was_updated else added).append(db_row["id_game"])


def _stream_channel(channel: str, added: List[str], updated: List[str]) -> None:
    """Fetch a batch of games from one TV channel, handle retries & rate‑limits."""
    url = f"https://lichess.org/api/tv/{channel}"
    params = {"clocks": False, "opening": True}

    for attempt in range(1, 4):  # max 3 retries
        resp = HTTP.get(url, params=params, stream=True)
        if resp.status_code == 429:  # too many requests → bail out
            LOGGER.error("Rate‑limit (429) on '%s' – exiting", channel)
            sys.exit(1)
        if resp.ok:
            break

        LOGGER.warning(
            "Channel '%s' returned %s (%s/3) – retrying in 5 s",
            channel,
            resp.status_code,
            attempt,
        )
        time.sleep(5)
    else:
        LOGGER.error("Could not connect to '%s' after retries", channel)
        return

    _parse_stream(resp, added, updated)


def _parse_stream(
    resp: requests.Response, added: List[str], updated: List[str]
) -> None:
    """Detect game boundaries (blank line + move line) and upsert each game."""
    pgn_block: list[bytes] = []

    for raw in resp.iter_lines():
        if not raw:
            continue  # keep buffering until we hit a move line

        line = raw.decode().strip()
        LOGGER.debug("PGN %s", line)
        pgn_block.append(raw)

        # in Lichess streaming API the first move ("1. …") ends the header
        if line.startswith("1. "):
            _process_game_block(pgn_block, added, updated)
            pgn_block.clear()


# ──────────────────────────────────────────────────────────────────────────
#   Main ingestion loop
# ──────────────────────────────────────────────────────────────────────────
def run_tv_ingestion() -> None:
    """Continuously fetch games from all channels until the time/game limit."""
    start = time.time()
    total = 0  # how many games we have ingested so far in this session

    while time.time() - start < TIME_LIMIT:
        added, updated = [], []

        for ch in CHANNELS:
            LOGGER.info("Fetching channel '%s'…", ch)
            _stream_channel(ch, added, updated)

        LOGGER.info("Batch done – %d added, %d updated", len(added), len(updated))
        total += len(added) + len(updated)

        if total >= MAX_GAMES:
            LOGGER.info(
                "Reached %d games → cooling‑off for %d s", MAX_GAMES, RATE_LIMIT_PAUSE
            )
            time.sleep(RATE_LIMIT_PAUSE)
            total = 0

        LOGGER.info("Sleeping %d s before next batch…", SLEEP_INTERVAL)
        time.sleep(SLEEP_INTERVAL)

    LOGGER.info("TIME_LIMIT (%s s) reached – stopping ingestion", TIME_LIMIT)


# ──────────────────────────────────────────────────────────────────────────
#   CLI entry‑point
# ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_tv_ingestion()
