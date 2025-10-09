#!/usr/bin/env python3
# ==============================================================================
# backfill_user_profiles.py
# ------------------------------------------------------------------------------
# Fetches Lichess profiles for players in `tv_channel_games` whose profiles
# have not been enriched.
#
# Workflow:
#   1. Collect unprofiled users from tv_channel_games
#   2. Fetch profile data via the Lichess API
#   3. Insert new profiles into lichess_users (if missing)
#   4. Mark tv_channel_games rows as updated
#   5. Run until SCRIPT_TIME_LIMIT or all users are processed
# ==============================================================================

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Optional, Set

import requests
from dotenv import load_dotenv
from requests.exceptions import HTTPError
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
    update,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

# ------------------------------------------------------------------------------
# Path & Imports
# ------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from knightshift.utils.db_utils import (
    get_database_url,
    get_lichess_token,
    load_db_credentials,
)
from knightshift.utils.logging_utils import setup_logger

# ------------------------------------------------------------------------------
# Environment & Database
# ------------------------------------------------------------------------------

load_dotenv(ROOT / "infra" / "compose" / ".env")

LOGGER = setup_logger("backfill_user_profiles", level=logging.INFO)

ENGINE = create_engine(
    get_database_url(load_db_credentials()),
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
)
SESSION: Session = sessionmaker(bind=ENGINE)()
METADATA = MetaData()

# ------------------------------------------------------------------------------
# Table Models
# ------------------------------------------------------------------------------

TV_GAMES = Table(
    "tv_channel_games",
    METADATA,
    Column("id_game", String, primary_key=True),
    Column("id_user_white", String),
    Column("id_user_black", String),
    Column("ind_profile_updated", Boolean, default=False),
)

LICHESS_USERS = Table(
    "lichess_users",
    METADATA,
    Column("id_user", String(50), primary_key=True),
    Column("val_username", String(50)),
    Column("val_title", String(10)),
    Column("val_url", Text),
    Column("val_real_name", Text),
    Column("val_location", Text),
    Column("val_bio", Text),
    Column("val_rating_fide", Integer),
    Column("val_rating_uscf", Integer),
    Column("val_rating_bullet", Integer),
    Column("val_rating_blitz", Integer),
    Column("val_rating_classical", Integer),
    Column("val_rating_rapid", Integer),
    Column("val_rating_chess960", Integer),
    Column("val_rating_ultra_bullet", Integer),
    Column("val_country_code", String(20)),
    Column("tm_created", BigInteger),
    Column("tm_seen", BigInteger),
    Column("n_playtime_total", Integer),
    Column("n_playtime_tv", Integer),
    Column("n_games_all", Integer),
    Column("n_games_rated", Integer),
    Column("n_games_win", Integer),
    Column("n_games_loss", Integer),
    Column("n_games_draw", Integer),
    Column("ind_patron", Boolean),
    Column("ind_streaming", Boolean),
)

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------

TIME_PER_USER = 0.5
BATCH_SIZE = 3_000
BATCH_PAUSE = 15 * 60
PROGRESS_INTERVAL = 30
SCRIPT_TIME_LIMIT = 5
FORCE_REVALIDATE = True

# ------------------------------------------------------------------------------
# HTTP Session
# ------------------------------------------------------------------------------

HTTP = requests.Session()
HTTP.headers.update(
    {
        "Authorization": f"Bearer {get_lichess_token()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
)

# ==============================================================================
# Helpers
# ==============================================================================


def _collect_unprofiled_users() -> Set[str]:
    """Fetch unprofiled users from tv_channel_games."""
    query = select(TV_GAMES.c.id_user_white, TV_GAMES.c.id_user_black)
    if not FORCE_REVALIDATE:
        query = query.where(TV_GAMES.c.ind_profile_updated.is_(False))

    rows = SESSION.execute(query).fetchall()
    users = {user for row in rows for user in row if user}
    LOGGER.info("Found %d unprofiled users.", len(users))
    return users


def _fetch_profile(username: str) -> Optional[dict]:
    """Fetch a single Lichess profile via API."""
    url = f"https://lichess.org/api/user/{username}"
    try:
        resp = HTTP.get(url, params={"trophies": "false"})
        resp.raise_for_status()
        LOGGER.info("Fetched profile for '%s'", username)
        return resp.json()
    except HTTPError as e:
        LOGGER.warning("HTTP %s for user '%s': %s", resp.status_code, username, e)
    except Exception as e:
        LOGGER.warning("Error fetching '%s': %s", username, e)
    return None


def _clean_value(value: Optional[str], value_type: str) -> Optional:
    """Normalize values (null, int, bool, or trimmed string)."""
    if value is None or str(value).strip().lower() in {"<null>", "null", "none", ""}:
        return None
    if value_type == "integer":
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    if value_type == "boolean":
        return str(value).lower() in {"true", "1"}
    return value.strip() if isinstance(value, str) else value


def _profile_exists(user_id: str) -> bool:
    """Check if a user profile already exists in lichess_users."""
    return (
        SESSION.execute(
            select(LICHESS_USERS.c.id_user).where(LICHESS_USERS.c.id_user == user_id)
        ).first()
        is not None
    )


def _insert_profile(data: dict) -> None:
    """Insert a new user profile into lichess_users if it doesn't exist."""
    try:
        username, user_id = data.get("username"), data.get("id")
        LOGGER.info("Inserting profile for '%s' (id=%s).", username, user_id)

        profile = data.get("profile", {})
        perfs = data.get("perfs", {})
        play_time = data.get("playTime", {})
        cnt = data.get("count", {})

        row = {
            "id_user": user_id,
            "val_username": username,
            "val_title": _clean_value(profile.get("title"), "string"),
            "val_url": _clean_value(profile.get("url"), "string"),
            "val_real_name": _clean_value(profile.get("realName"), "string"),
            "val_location": _clean_value(profile.get("location"), "string"),
            "val_bio": _clean_value(profile.get("bio"), "string"),
            "val_rating_fide": _clean_value(profile.get("fideRating"), "integer"),
            "val_rating_uscf": _clean_value(profile.get("uscfRating"), "integer"),
            "val_rating_bullet": _clean_value(
                perfs.get("bullet", {}).get("rating"), "integer"
            ),
            "val_rating_blitz": _clean_value(
                perfs.get("blitz", {}).get("rating"), "integer"
            ),
            "val_rating_classical": _clean_value(
                perfs.get("classical", {}).get("rating"), "integer"
            ),
            "val_rating_rapid": _clean_value(
                perfs.get("rapid", {}).get("rating"), "integer"
            ),
            "val_rating_chess960": _clean_value(
                perfs.get("chess960", {}).get("rating"), "integer"
            ),
            "val_rating_ultra_bullet": _clean_value(
                perfs.get("ultraBullet", {}).get("rating"), "integer"
            ),
            "val_country_code": _clean_value(profile.get("flag"), "string"),
            "tm_created": data.get("createdAt"),
            "tm_seen": data.get("seenAt"),
            "n_playtime_total": _clean_value(play_time.get("total"), "integer"),
            "n_playtime_tv": _clean_value(play_time.get("tv"), "integer"),
            "n_games_all": _clean_value(cnt.get("all"), "integer"),
            "n_games_rated": _clean_value(cnt.get("rated"), "integer"),
            "n_games_win": _clean_value(cnt.get("win"), "integer"),
            "n_games_loss": _clean_value(cnt.get("loss"), "integer"),
            "n_games_draw": _clean_value(cnt.get("draw"), "integer"),
            "ind_patron": _clean_value(data.get("patron"), "boolean"),
            "ind_streaming": _clean_value(data.get("streaming"), "boolean"),
        }

        if not _profile_exists(user_id):
            SESSION.execute(LICHESS_USERS.insert().values(**row))
            SESSION.commit()
            LOGGER.info("Inserted profile for '%s'.", username)
    except Exception as e:
        LOGGER.error("Insert error for '%s': %s", data.get("username"), e)
        SESSION.rollback()


def _mark_profile_done(username: str) -> None:
    """Mark tv_channel_games rows as profile-updated for a user."""
    try:
        SESSION.execute(
            update(TV_GAMES)
            .where(
                (TV_GAMES.c.id_user_white == username)
                | (TV_GAMES.c.id_user_black == username)
            )
            .values(ind_profile_updated=True)
        )
        SESSION.commit()
    except Exception as e:
        LOGGER.error("Failed to mark '%s' as updated: %s", username, e)
        SESSION.rollback()


def _handle_user(username: str) -> bool:
    """Fetch, insert, and mark profile for one user."""
    data = _fetch_profile(username)
    if not data or not data.get("id"):
        return False
    if FORCE_REVALIDATE:
        _insert_profile(data)
    _mark_profile_done(username)
    return True


def _eta(total: int, per_item: float) -> str:
    """Rough ETA string from total items and average time per item."""
    m, s = divmod(int(total * per_item), 60)
    return f"~{m} min {s} s" if m else f"~{s} s"


def _process(users: Set[str]) -> None:
    """Process all unprofiled users with progress logs and rate limiting."""
    total = len(users)
    LOGGER.info("Enriching %d users (ETA: %s)", total, _eta(total, TIME_PER_USER))

    start = last_log = time.time()
    processed = 0

    for username in users:
        if time.time() - start > SCRIPT_TIME_LIMIT:
            LOGGER.warning("Time limit reached – stopping.")
            break

        try:
            if _handle_user(username):
                processed += 1
        except Exception as e:
            LOGGER.error("Unhandled error for user '%s': %s", username, e)

        if time.time() - last_log > PROGRESS_INTERVAL:
            LOGGER.info("Progress %d/%d", processed, total)
            last_log = time.time()

        time.sleep(TIME_PER_USER)

        if processed and processed % BATCH_SIZE == 0:
            LOGGER.info(
                "Processed %d users – pausing %d min.", processed, BATCH_PAUSE // 60
            )
            time.sleep(BATCH_PAUSE)

    LOGGER.info("Done. %d profiles processed.", processed)


def run_backfill_user_profiles() -> None:
    LOGGER.info("Starting backfill.")
    users = _collect_unprofiled_users()
    if not users:
        LOGGER.info("All profiles up-to-date.")
        return
    _process(users)
    LOGGER.info("Backfill complete.")


if __name__ == "__main__":
    run_backfill_user_profiles()
