#!/usr/bin/env python3
"""
backfill_user_profiles.py

Further refactored to:
  - Separate logic into smaller, self-contained functions
  - Centralize constants/time intervals
  - Reduce repetition in the main loop
  - Improve code readability

Usage:
  python backfill_user_profiles.py
"""

import sys
import time
import requests
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from requests.exceptions import HTTPError
from sqlalchemy import (
    create_engine,
    Table,
    Column,
    String,
    MetaData,
    update,
    select,
    Boolean,
    Integer,
    BigInteger,
    Text,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# -------------------------------------------------------------------
# Ensure Project Root is in sys.path to fix ModuleNotFoundError
# -------------------------------------------------------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[
    2
]  # go 2 levels up from ingestion/ → src → project root
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# -------------------------------------------------------------------
# Now we can safely import from src.*
# -------------------------------------------------------------------
from src.utils.db_utils import load_db_credentials, get_database_url, get_lichess_token
from src.utils.logging_utils import setup_logger

# -------------------------------------------------------------------
# Environment and Database Setup
# -------------------------------------------------------------------
load_dotenv(PROJECT_ROOT / "config" / ".env.local")  # Adjust if your .env path differs

logger = setup_logger(name="backfill_user_profiles", level=logging.INFO)

creds = load_db_credentials()
DATABASE_URL = get_database_url(creds)

engine = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=10, max_overflow=20)
metadata = MetaData()
Session = sessionmaker(bind=engine)
session = Session()

http_session = requests.Session()  # shared session for HTTP requests
http_session.headers.update(
    {
        "Authorization": f"Bearer {get_lichess_token()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
)

# -------------------------------------------------------------------
# Constants / Config
# -------------------------------------------------------------------
TIME_PER_USER = 0.5  # seconds between each user request
BATCH_SIZE = 3000  # how many users to process before a long pause
BATCH_PAUSE = 15 * 60  # pause duration after hitting batch size (in seconds)
PROGRESS_INTERVAL = 30  # seconds between progress log updates
TIME_LIMIT = 3  # in seconds (to avoid rate limiting)

# -------------------------------------------------------------------
# Table Definitions
# -------------------------------------------------------------------
tv_channel_games_table = Table(
    "tv_channel_games",
    metadata,
    Column("id", String, primary_key=True),
    Column("white", String),
    Column("black", String),
    Column("profile_updated", Boolean, default=False),
)

lichess_users_table = Table(
    "lichess_users",
    metadata,
    Column("id", String(50), primary_key=True),
    Column("username", String(50)),
    Column("title", String(10)),
    Column("url", Text),
    Column("real_name", Text),
    Column("location", Text),
    Column("bio", Text),
    Column("fide_rating", Integer),
    Column("uscf_rating", Integer),
    Column("bullet_rating", Integer),
    Column("blitz_rating", Integer),
    Column("classical_rating", Integer),
    Column("rapid_rating", Integer),
    Column("chess960_rating", Integer),
    Column("ultra_bullet_rating", Integer),
    Column("country_code", String(5)),
    Column("created_at", BigInteger),
    Column("seen_at", BigInteger),
    Column("playtime_total", Integer),
    Column("playtime_tv", Integer),
    Column("games_all", Integer),
    Column("games_rated", Integer),
    Column("games_win", Integer),
    Column("games_loss", Integer),
    Column("games_draw", Integer),
    Column("patron", Boolean),
    Column("streaming", Boolean),
)


# -------------------------------------------------------------------
# Helper Methods
# -------------------------------------------------------------------
def get_unprofiled_usernames() -> set[str]:
    """
    Gather usernames from rows in tv_channel_games where profile_updated = False.
    Returns a set of unique usernames (white or black).
    """
    rows = session.execute(
        select(tv_channel_games_table.c.white, tv_channel_games_table.c.black).where(
            tv_channel_games_table.c.profile_updated == False
        )
    ).fetchall()

    users_to_process = set()
    for row in rows:
        if row.white:
            users_to_process.add(row.white)
        if row.black:
            users_to_process.add(row.black)
    return users_to_process


def get_user_data_from_api(username: str) -> Optional[dict]:
    """
    Fetch user public data from Lichess via http_session.
    - If a rate limit error (429) is encountered, exit immediately.
    """
    url = f"https://lichess.org/api/user/{username}"
    try:
        response = http_session.get(url, params={"trophies": "false"})
        if response.status_code == 429:
            logger.error(f"Rate limit encountered for '{username}'. Stopping pipeline.")
            sys.exit(1)  # or handle differently if you prefer
        response.raise_for_status()
        return response.json()
    except HTTPError as http_err:
        logger.warning(f"HTTP error for '{username}': {http_err}")
    except Exception as err:
        logger.warning(f"Error fetching user data for '{username}': {err}")
    return None


def user_exists_in_lichess_users(user_id: str) -> bool:
    """
    Check if a user row already exists in lichess_users by its unique ID.
    """
    row = session.execute(
        select(lichess_users_table.c.id).where(lichess_users_table.c.id == user_id)
    ).fetchone()
    return row is not None


def insert_user_data(user_json: dict) -> None:
    """
    Insert user data into lichess_users based on the Lichess API JSON.
    Rolls back session on error.
    """
    profile = user_json.get("profile", {})
    perfs = user_json.get("perfs", {})
    play_time = user_json.get("playTime", {})
    count = user_json.get("count", {})

    data = {
        "id": user_json.get("id"),
        "username": user_json.get("username"),
        "title": user_json.get("title"),
        "url": user_json.get("url"),
        "real_name": profile.get("realName"),
        "location": profile.get("location"),
        "bio": profile.get("bio"),
        "fide_rating": profile.get("fideRating"),
        "uscf_rating": profile.get("uscfRating"),
        "bullet_rating": perfs.get("bullet", {}).get("rating"),
        "blitz_rating": perfs.get("blitz", {}).get("rating"),
        "classical_rating": perfs.get("classical", {}).get("rating"),
        "rapid_rating": perfs.get("rapid", {}).get("rating"),
        "chess960_rating": perfs.get("chess960", {}).get("rating"),
        "ultra_bullet_rating": perfs.get("ultraBullet", {}).get("rating"),
        "country_code": profile.get("flag"),
        "created_at": user_json.get("createdAt"),
        "seen_at": user_json.get("seenAt"),
        "playtime_total": play_time.get("total"),
        "playtime_tv": play_time.get("tv"),
        "games_all": count.get("all"),
        "games_rated": count.get("rated"),
        "games_win": count.get("win"),
        "games_loss": count.get("loss"),
        "games_draw": count.get("draw"),
        "patron": user_json.get("patron"),
        "streaming": user_json.get("streaming"),
    }

    session.execute(lichess_users_table.insert().values(**data))
    session.commit()


def mark_profile_updated_for_username(username: str) -> None:
    """
    Update tv_channel_games.profile_updated = True where the user is 'white' or 'black'.
    """
    session.execute(
        update(tv_channel_games_table)
        .where(
            (tv_channel_games_table.c.white == username)
            | (tv_channel_games_table.c.black == username)
        )
        .values(profile_updated=True)
    )
    session.commit()


def update_or_insert_user(username: str) -> bool:
    """
    1) Fetch user JSON from Lichess
    2) Check if user already exists
       - if yes, skip insert
       - if no, insert user data
    3) Mark tv_channel_games.profile_updated for the user
    Returns True if user was successfully processed; False otherwise.
    """
    user_json = get_user_data_from_api(username)
    if not user_json:
        return False  # No data fetched or error

    user_id = user_json.get("id")
    if not user_id:
        return False  # Malformed data from API

    if user_exists_in_lichess_users(user_id):
        logger.info(
            f"User '{username}' (ID: {user_id}) already in DB. Skipping insert."
        )
        mark_profile_updated_for_username(username)
        return True

    # Insert new user
    try:
        insert_user_data(user_json)
        mark_profile_updated_for_username(username)
        logger.info(f"Inserted new user '{username}' (ID: {user_id}).")
        return True
    except Exception as e:
        logger.error(f"Error inserting user '{username}' (ID: {user_id}): {e}")
        session.rollback()
        return False


def estimate_processing_time(num_users: int, seconds_per_user: float) -> str:
    """
    Compute estimated total processing time, return as a readable string.
    """
    total_sec = int(num_users * seconds_per_user)
    est_minutes, est_seconds = divmod(total_sec, 60)
    if est_minutes == 0:
        return f"~{est_seconds} second(s)"
    else:
        return f"~{est_minutes} min {est_seconds} sec"


def process_usernames(users: set[str]) -> None:
    """
    Iterate over each username, update or insert user data,
    throttle requests, log progress, and handle batch pauses.
    Terminates early if TIME_LIMIT seconds are exceeded.
    """
    start_time = time.time()  # <-- track when we start
    total_users = len(users)
    logger.info(f"Found {total_users} unique usernames requiring enrichment.")
    logger.info(
        "Estimated time to process: "
        + estimate_processing_time(total_users, TIME_PER_USER)
    )

    last_report_time = start_time
    processed_count = 0

    for username in users:
        # 🕒 Check if we've passed the time limit
        elapsed = time.time() - start_time
        if elapsed >= TIME_LIMIT:
            logger.warning(
                f"Time limit of {TIME_LIMIT} seconds reached. Stopping early after {processed_count} user(s)."
            )
            break

        # Attempt to update/insert user
        success = update_or_insert_user(username)
        if success:
            processed_count += 1

        # Periodic progress update
        if (time.time() - last_report_time) >= PROGRESS_INTERVAL:
            remaining = total_users - processed_count
            logger.info(
                f"Processed {processed_count}/{total_users}. Remaining: {remaining}."
            )
            last_report_time = time.time()

        # Throttle to avoid rate limits
        time.sleep(TIME_PER_USER)

        # Optional: big batch pause
        if processed_count > 0 and processed_count % BATCH_SIZE == 0:
            logger.info(
                f"Processed {processed_count} users. Pausing for {BATCH_PAUSE//60} min..."
            )
            time.sleep(BATCH_PAUSE)

    logger.info(f"Stopped after processing {processed_count} user(s).")
    logger.info("tv_channel_games rows updated where user profiles fetched.")


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
def main():
    users_to_process = get_unprofiled_usernames()
    if not users_to_process:
        logger.info("No users to process. All profiles appear up-to-date.")
        return

    process_usernames(users_to_process)


if __name__ == "__main__":
    main()
