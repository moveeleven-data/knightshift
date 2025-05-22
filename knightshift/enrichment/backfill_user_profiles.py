#!/usr/bin/env python3
"""
backfill_user_profiles.py
─────────────────────────
Fetch public profiles from **Lichess** for any player that appears in
`tv_channel_games` but has not yet been enriched.
The script:
1. collects unique user‑names whose `profile_updated` flag is **False** (unless revalidation is forced);
2. pulls their profile JSON from Lichess REST API;
3. inserts the data into `lichess_users` (or skips if it already exists);
4. flips `profile_updated = TRUE` for every processed game row.

Runtime limits, throttling, and batch pauses are controlled via the
constants in **Config**.
"""

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

# ──────────────────────────────────────────────────────────────────────────
# Local imports  (add project root to PYTHONPATH first)
# ──────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]  # project root (knightshift/)
sys.path.insert(0, str(ROOT))

from knightshift.utils.db_utils import (
    get_database_url,
    get_lichess_token,
    load_db_credentials,
)
from knightshift.utils.logging_utils import setup_logger

# ──────────────────────────────────────────────────────────────────────────
# Env & DB initialisation
# ──────────────────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────────────────
# Table models  (minimal columns only)
# ──────────────────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────
TIME_PER_USER = 0.5  # seconds between individual API calls
BATCH_SIZE = 3_000  # users processed before a long pause
BATCH_PAUSE = 15 * 60  # seconds to pause after each big batch
PROGRESS_INTERVAL = 30  # seconds between progress log lines
SCRIPT_TIME_LIMIT = 5  # hard stop (seconds) – keeps CI tests fast

# Toggle for re-validating all rows
FORCE_REVALIDATE = True  # Set to False to skip re-validation of already processed rows

# ──────────────────────────────────────────────────────────────────────────
# Shared HTTP session
# ──────────────────────────────────────────────────────────────────────────
HTTP = requests.Session()
HTTP.headers.update(
    {
        "Authorization": f"Bearer {get_lichess_token()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
)

# ═════════════════════════════════════════════════════════════════════════
# Helper functions
# ═════════════════════════════════════════════════════════════════════════


def _collect_unprofiled_users() -> Set[str]:
    """Return all distinct white/black players whose profile is not updated."""
    if FORCE_REVALIDATE:
        rows = SESSION.execute(
            select(TV_GAMES.c.id_user_white, TV_GAMES.c.id_user_black)
        ).fetchall()
    else:
        rows = SESSION.execute(
            select(TV_GAMES.c.id_user_white, TV_GAMES.c.id_user_black).where(
                TV_GAMES.c.ind_profile_updated.is_(False)
            )
        ).fetchall()

    users: set[str] = set()
    for w, b in rows:
        if w:
            users.add(w)
        if b:
            users.add(b)

    LOGGER.info("Found %d unprofiled users.", len(users))  # Log user count
    return users


def _fetch_profile(username: str) -> Optional[dict]:
    """Fetch player JSON; handle 429 / network errors gracefully."""
    url = f"https://lichess.org/api/user/{username}"
    try:
        resp = HTTP.get(url, params={"trophies": "false"})
        resp.raise_for_status()  # This will raise an exception for non-2xx status codes
        LOGGER.info(
            "Successfully fetched profile for '%s'", username
        )  # Log successful fetch
        return resp.json()
    except HTTPError as e:
        LOGGER.warning("HTTP %s for user '%s': %s", resp.status_code, username, e)
    except Exception as e:
        LOGGER.warning("Error fetching '%s': %s", username, e)
    return None


def _clean_value(value: Optional[str], value_type: str) -> Optional:
    """Cleans values based on the type (handles null-like strings and missing values)."""
    if value is None or value in {"<null>", "null", "None", ""}:
        return None
    if value_type == "integer":
        try:
            return int(value) if value not in {"", "NULL", "<null>", "None"} else None
        except ValueError:
            return None
    if value_type == "boolean":
        if value in {"true", "True", "1"}:
            return True
        return False
    return value.strip() if isinstance(value, str) else value


def _profile_exists(user_id: str) -> bool:
    """Check if the profile already exists in the lichess_users table."""
    result = SESSION.execute(
        select(LICHESS_USERS.c.id_user).where(LICHESS_USERS.c.id_user == user_id)
    ).first()
    return result is not None


def _insert_profile(data: dict) -> None:
    """Insert the profile into the database if it doesn't exist."""
    try:
        LOGGER.info(
            "Inserting profile for '%s' (id=%s).", data.get("username"), data.get("id")
        )

        # Only extract the necessary fields (exclude unwanted ones)
        profile = data.get("profile", {})
        perfs = data.get("perfs", {})
        play_time = data.get("playTime", {})
        cnt = data.get("count", {})

        # Clean up fields (apply cleaning to all fields)
        val_real_name = _clean_value(profile.get("realName", "Not Provided"), "string")
        val_location = _clean_value(profile.get("location", "Not Provided"), "string")
        val_bio = _clean_value(profile.get("bio", "Not Provided"), "string")
        val_rating_fide = _clean_value(profile.get("fideRating", None), "integer")
        val_rating_uscf = _clean_value(profile.get("uscfRating", None), "integer")
        val_title = _clean_value(profile.get("title", "None"), "string")
        ind_patron = _clean_value(data.get("patron", False), "boolean")
        ind_streaming = _clean_value(data.get("streaming", False), "boolean")

        val_country_code = _clean_value(profile.get("flag", "Not Provided"), "string")
        val_location = _clean_value(profile.get("location", "Not Provided"), "string")
        val_url = _clean_value(profile.get("url", "None"), "string")

        val_rating_bullet = _clean_value(
            perfs.get("bullet", {}).get("rating", None), "integer"
        )
        val_rating_blitz = _clean_value(
            perfs.get("blitz", {}).get("rating", None), "integer"
        )
        val_rating_classical = _clean_value(
            perfs.get("classical", {}).get("rating", None), "integer"
        )
        val_rating_rapid = _clean_value(
            perfs.get("rapid", {}).get("rating", None), "integer"
        )
        val_rating_chess960 = _clean_value(
            perfs.get("chess960", {}).get("rating", None), "integer"
        )
        val_rating_ultra_bullet = _clean_value(
            perfs.get("ultraBullet", {}).get("rating", None), "integer"
        )

        row = {
            "id_user": data.get("id"),
            "val_username": data.get("username"),
            "val_title": val_title,
            "val_real_name": val_real_name,
            "val_location": val_location,
            "val_bio": val_bio,
            "val_rating_fide": val_rating_fide,
            "val_rating_uscf": val_rating_uscf,
            "val_rating_bullet": val_rating_bullet,
            "val_rating_blitz": val_rating_blitz,
            "val_rating_classical": val_rating_classical,
            "val_rating_rapid": val_rating_rapid,
            "val_rating_chess960": val_rating_chess960,
            "val_rating_ultra_bullet": val_rating_ultra_bullet,
            "val_country_code": val_country_code,
            "tm_created": data.get("createdAt"),
            "tm_seen": data.get("seenAt"),
            "n_playtime_total": _clean_value(play_time.get("total", 0), "integer"),
            "n_playtime_tv": _clean_value(play_time.get("tv", 0), "integer"),
            "n_games_all": _clean_value(cnt.get("all", 0), "integer"),
            "n_games_rated": _clean_value(cnt.get("rated", 0), "integer"),
            "n_games_win": _clean_value(cnt.get("win", 0), "integer"),
            "n_games_loss": _clean_value(cnt.get("loss", 0), "integer"),
            "n_games_draw": _clean_value(cnt.get("draw", 0), "integer"),
            "ind_patron": ind_patron,
            "ind_streaming": ind_streaming,
            "val_url": val_url,
        }

        if not _profile_exists(data.get("id")):
            SESSION.execute(LICHESS_USERS.insert().values(**row))
            SESSION.commit()
            LOGGER.info("Successfully inserted profile for '%s'.", data.get("username"))
    except Exception as e:
        LOGGER.error("Error inserting profile for '%s': %s", data.get("username"), e)
        SESSION.rollback()


def _mark_profile_done(username: str) -> None:
    try:
        LOGGER.info("Marking profile as updated for '%s'.", username)
        SESSION.execute(
            update(TV_GAMES)
            .where(
                (TV_GAMES.c.id_user_white == username)
                | (TV_GAMES.c.id_user_black == username)
            )
            .values(ind_profile_updated=True)
        )
        SESSION.commit()
        LOGGER.info("Successfully marked profile as updated for '%s'.", username)
    except Exception as e:
        LOGGER.error("Error marking profile as updated for '%s': %s", username, e)
        SESSION.rollback()


def _handle_user(username: str) -> bool:
    """Fetch, insert (if new), and flag games; return True on any success."""
    data = _fetch_profile(username)
    if not data or not (user_id := data.get("id")):
        return False

    if FORCE_REVALIDATE:
        _insert_profile(data)
        LOGGER.info("Inserted profile for '%s' (id=%s).", username, user_id)

    _mark_profile_done(username)
    return True


def _eta(total: int, seconds_per_user: float) -> str:
    minutes, seconds = divmod(int(total * seconds_per_user), 60)
    return f"~{minutes} min {seconds} s" if minutes else f"~{seconds} s"


def _process(users: Set[str]) -> None:
    total = len(users)
    LOGGER.info(
        "Need to enrich %d unique users (ETA %s).", total, _eta(total, TIME_PER_USER)
    )

    start = last_log = time.time()
    processed = 0

    for username in users:
        if time.time() - start > SCRIPT_TIME_LIMIT:
            LOGGER.warning(
                "Time‑limit (%s s) reached – stopping early.", SCRIPT_TIME_LIMIT
            )
            break

        try:
            if _handle_user(username):
                processed += 1
        except Exception as e:
            LOGGER.error("Error processing user '%s': %s", username, e)
            continue

        if time.time() - last_log > PROGRESS_INTERVAL:
            LOGGER.info(
                "Progress %d/%d (remaining %d)…", processed, total, total - processed
            )
            last_log = time.time()

        time.sleep(TIME_PER_USER)

        if processed and processed % BATCH_SIZE == 0:
            LOGGER.info(
                "Processed %d users – cooling‑off %d min.", processed, BATCH_PAUSE // 60
            )
            time.sleep(BATCH_PAUSE)

    LOGGER.info("Finished: %d user profiles processed.", processed)


def run_backfill_user_profiles() -> None:
    LOGGER.info("Starting backfill for user profiles.")
    users = _collect_unprofiled_users()
    if not users:
        LOGGER.info("All profiles up‑to‑date – nothing to do.")
        return
    _process(users)
    LOGGER.info("Backfill for user profiles complete.")


if __name__ == "__main__":
    run_backfill_user_profiles()
