#!/usr/bin/env python3
# ==============================================================================
# backfill_user_profiles.py
# ------------------------------------------------------------------------------
# Fetches Lichess profiles for players in `tv_channel_games` whose profiles
# have not been enriched.
# ==============================================================================

import sys
import time
from pathlib import Path

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
from sqlalchemy.orm import sessionmaker
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

LOGGER = setup_logger("backfill_user_profiles")

ENGINE = create_engine(
    get_database_url(load_db_credentials()),
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
)
SESSION = sessionmaker(bind=ENGINE)()
METADATA = MetaData()

# ------------------------------------------------------------------------------
# Tables
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
# HTTP
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

def _collect_unprofiled_users():
    query = select(TV_GAMES.c.id_user_white, TV_GAMES.c.id_user_black)
    if not FORCE_REVALIDATE:
        query = query.where(TV_GAMES.c.ind_profile_updated.is_(False))

    rows = SESSION.execute(query).fetchall()
    return {user for row in rows for user in row if user}


def _fetch_profile(username):
    url = f"https://lichess.org/api/user/{username}"
    try:
        resp = HTTP.get(url, params={"trophies": "false"})
        resp.raise_for_status()
        return resp.json()
    except HTTPError:
        return None
    except Exception:
        return None


def _clean_value(value, value_type):
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


def _profile_exists(user_id):
    return (
        SESSION.execute(
            select(LICHESS_USERS.c.id_user).where(LICHESS_USERS.c.id_user == user_id)
        ).first()
        is not None
    )


def _insert_profile(data):
    try:
        user_id = data.get("id")
        profile = data.get("profile", {})
        perfs = data.get("perfs", {})
        play_time = data.get("playTime", {})
        cnt = data.get("count", {})

        row = {
            "id_user": user_id,
            "val_username": data.get("username"),
            "val_title": _clean_value(profile.get("title"), "string"),
            "val_url": _clean_value(profile.get("url"), "string"),
            "val_real_name": _clean_value(profile.get("realName"), "string"),
            "val_location": _clean_value(profile.get("location"), "string"),
            "val_bio": _clean_value(profile.get("bio"), "string"),
            "val_rating_fide": _clean_value(profile.get("fideRating"), "integer"),
            "val_rating_uscf": _clean_value(profile.get("uscfRating"), "integer"),
            "val_rating_bullet": _clean_value(perfs.get("bullet", {}).get("rating"), "integer"),
            "val_rating_blitz": _clean_value(perfs.get("blitz", {}).get("rating"), "integer"),
            "val_rating_classical": _clean_value(perfs.get("classical", {}).get("rating"), "integer"),
            "val_rating_rapid": _clean_value(perfs.get("rapid", {}).get("rating"), "integer"),
            "val_rating_chess960": _clean_value(perfs.get("chess960", {}).get("rating"), "integer"),
            "val_rating_ultra_bullet": _clean_value(perfs.get("ultraBullet", {}).get("rating"), "integer"),
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
    except Exception:
        SESSION.rollback()


def _mark_profile_done(username):
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
    except Exception:
        SESSION.rollback()


def _handle_user(username):
    data = _fetch_profile(username)
    if not data or not data.get("id"):
        return False
    if FORCE_REVALIDATE:
        _insert_profile(data)
    _mark_profile_done(username)
    return True


def _process(users):
    total = len(users)
    start = time.time()
    processed = 0

    for username in users:
        if time.time() - start > SCRIPT_TIME_LIMIT:
            break
        try:
            if _handle_user(username):
                processed += 1
        except Exception:
            pass
        time.sleep(TIME_PER_USER)
        if processed and processed % BATCH_SIZE == 0:
            time.sleep(BATCH_PAUSE)


def run_backfill_user_profiles():
    users = _collect_unprofiled_users()
    if not users:
        return
    _process(users)


if __name__ == "__main__":
    run_backfill_user_profiles()
