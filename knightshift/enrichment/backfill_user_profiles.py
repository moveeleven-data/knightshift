#!/usr/bin/env python3
"""
backfill_user_profiles.py
─────────────────────────
Fetch public profiles from **Lichess** for any player that appears in
`tv_channel_games` but has not yet been enriched.
The script

1. collects unique user‑names whose `profile_updated` flag is **False**;
2. pulls their profile JSON from the Lichess REST API;
3. inserts the data into `lichess_users` (or skips if it already exists);
4. flips `profile_updated = TRUE` for every processed game row.

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
#   Local imports  (add project root to PYTHONPATH first)
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
#   Env & DB initialisation
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
#   Table models  (minimal columns only)
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
#   Config
# ──────────────────────────────────────────────────────────────────────────
TIME_PER_USER = 0.5  # seconds between individual API calls
BATCH_SIZE = 3_000  # users processed before a long pause
BATCH_PAUSE = 15 * 60  # seconds to pause after each big batch
PROGRESS_INTERVAL = 30  # seconds between progress log lines
SCRIPT_TIME_LIMIT = 5  # hard stop (seconds) – keeps CI tests fast

# ──────────────────────────────────────────────────────────────────────────
#   Shared HTTP session
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
    return users


def _fetch_profile(username: str) -> Optional[dict]:
    """Fetch player JSON; handle 429 / network errors gracefully."""
    url = f"https://lichess.org/api/user/{username}"
    try:
        resp = HTTP.get(url, params={"trophies": "false"})
        if resp.status_code == 429:
            LOGGER.error("Rate‑limit hit on '%s'; stopping backfill.", username)
            sys.exit(1)
        resp.raise_for_status()
        return resp.json()
    except HTTPError as e:  # 4xx/5xx
        LOGGER.warning("HTTP %s for user '%s': %s", resp.status_code, username, e)
    except Exception as e:
        LOGGER.warning("Error fetching '%s': %s", username, e)
    return None


def _profile_exists(user_id: str) -> bool:
    return (
        SESSION.execute(
            select(LICHESS_USERS.c.id_user).where(LICHESS_USERS.c.id_user == user_id)
        ).first()
        is not None
    )


def _insert_profile(data: dict) -> None:
    """Insert a new row into `lichess_users` (rollback on failure)."""
    profile = data.get("profile", {})
    perfs = data.get("perfs", {})
    play_time = data.get("playTime", {})
    cnt = data.get("count", {})

    # Normalize and clean the title field
    title_raw = data.get("title")
    if not title_raw or not title_raw.strip():
        title = "None"
    else:
        title = title_raw.strip().upper()

    row = {
        # identifiers
        "id_user": data.get("id"),
        "val_username": data.get("username"),
        "val_title": title,
        "val_url": data.get("url"),
        # free‑text
        "val_real_name": profile.get("realName"),
        "val_location": profile.get("location"),
        "val_bio": profile.get("bio"),
        # ratings
        "val_rating_fide": profile.get("fideRating"),
        "val_rating_uscf": profile.get("uscfRating"),
        "val_rating_bullet": perfs.get("bullet", {}).get("rating"),
        "val_rating_blitz": perfs.get("blitz", {}).get("rating"),
        "val_rating_classical": perfs.get("classical", {}).get("rating"),
        "val_rating_rapid": perfs.get("rapid", {}).get("rating"),
        "val_rating_chess960": perfs.get("chess960", {}).get("rating"),
        "val_rating_ultra_bullet": perfs.get("ultraBullet", {}).get("rating"),
        # misc
        "val_country_code": profile.get("flag"),
        "tm_created": data.get("createdAt"),
        "tm_seen": data.get("seenAt"),
        "n_playtime_total": play_time.get("total"),
        "n_playtime_tv": play_time.get("tv"),
        "n_games_all": cnt.get("all"),
        "n_games_rated": cnt.get("rated"),
        "n_games_win": cnt.get("win"),
        "n_games_loss": cnt.get("loss"),
        "n_games_draw": cnt.get("draw"),
        "ind_patron": data.get("patron"),
        "ind_streaming": data.get("streaming"),
    }

    SESSION.execute(LICHESS_USERS.insert().values(**row))
    SESSION.commit()


def _mark_profile_done(username: str) -> None:
    """Set profile_updated=TRUE for all games where the user appears."""
    SESSION.execute(
        update(TV_GAMES)
        .where(
            (TV_GAMES.c.id_user_white == username)
            | (TV_GAMES.c.id_user_black == username)
        )
        .values(ind_profile_updated=True)
    )
    SESSION.commit()


def _handle_user(username: str) -> bool:
    """Fetch, insert (if new), and flag games; return True on any success."""
    data = _fetch_profile(username)
    if not data or not (user_id := data.get("id")):
        return False

    if _profile_exists(user_id):
        LOGGER.info("User '%s' already present – skipping insert.", username)
    else:
        try:
            _insert_profile(data)
            LOGGER.info("Inserted profile for '%s' (id=%s).", username, user_id)
        except Exception as e:
            LOGGER.error("Insert failed for '%s': %s – rolling back", username, e)
            SESSION.rollback()
            return False

    _mark_profile_done(username)
    return True


def _eta(total: int, seconds_per_user: float) -> str:
    minutes, seconds = divmod(int(total * seconds_per_user), 60)
    return f"~{minutes} min {seconds} s" if minutes else f"~{seconds} s"


# ═════════════════════════════════════════════════════════════════════════
# Main processing loop
# ═════════════════════════════════════════════════════════════════════════


def _process(users: Set[str]) -> None:
    total = len(users)
    LOGGER.info(
        "Need to enrich %d unique users (ETA %s).", total, _eta(total, TIME_PER_USER)
    )

    start = last_log = time.time()
    processed = 0

    for username in users:
        # hard stop for CI / unit‑tests
        if time.time() - start > SCRIPT_TIME_LIMIT:
            LOGGER.warning(
                "Time‑limit (%s s) reached – stopping early.", SCRIPT_TIME_LIMIT
            )
            break

        if _handle_user(username):
            processed += 1

        # periodic status report
        if time.time() - last_log > PROGRESS_INTERVAL:
            LOGGER.info(
                "Progress %d/%d (remaining %d)…", processed, total, total - processed
            )
            last_log = time.time()

        # rate‑limit protection
        time.sleep(TIME_PER_USER)

        # long cool‑down after big batch
        if processed and processed % BATCH_SIZE == 0:
            LOGGER.info(
                "Processed %d users – cooling‑off %d min.", processed, BATCH_PAUSE // 60
            )
            time.sleep(BATCH_PAUSE)

    LOGGER.info("Finished: %d user profiles processed.", processed)


# ═════════════════════════════════════════════════════════════════════════
# Entry‑point
# ═════════════════════════════════════════════════════════════════════════
def run_backfill_user_profiles() -> None:
    users = _collect_unprofiled_users()
    if not users:
        LOGGER.info("All profiles up‑to‑date – nothing to do.")
        return
    _process(users)


if __name__ == "__main__":
    run_backfill_user_profiles()
