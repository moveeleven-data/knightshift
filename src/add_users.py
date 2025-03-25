#!/usr/bin/env python3
import os
import time
import requests
from pathlib import Path

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
    or_,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from db_utils import load_db_credentials, get_database_url, get_lichess_token

# -------------------------------------------------------------------
# Environment and Database Setup
# -------------------------------------------------------------------

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env.local")
creds = load_db_credentials()
DATABASE_URL = get_database_url(creds)

engine = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=10, max_overflow=20)
metadata = MetaData()
Session = sessionmaker(bind=engine)
session = Session()

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
# API & Database Helper Methods
# -------------------------------------------------------------------


def get_user_data_from_api(username: str):
    """Fetch user public data from Lichess."""
    url = f"https://lichess.org/api/user/{username}"
    params = {"trophies": "false"}
    headers = {
        "Authorization": f"Bearer {get_lichess_token()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()

    print(
        f"Failed to fetch user data for {username}: {response.status_code} - {response.text}"
    )
    return None


def insert_user_data(user_json):
    """Insert user data into lichess_users based on the Lichess API JSON."""
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


def user_exists_in_lichess_users(user_id: str) -> bool:
    """Check if there's already a row in lichess_users for the given user ID."""
    row = session.execute(
        select(lichess_users_table.c.id).where(lichess_users_table.c.id == user_id)
    ).fetchone()
    return row is not None


def mark_profile_updated_for_username(username: str):
    """
    Update tv_channel_games.profile_updated = true
    for every row that has this user as white or black.
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


# -------------------------------------------------------------------
# Main Process with Progress Reporting
# -------------------------------------------------------------------


def main():
    # Gather all rows where profile_updated is false.
    rows = session.execute(
        select(tv_channel_games_table.c.white, tv_channel_games_table.c.black).where(
            tv_channel_games_table.c.profile_updated == False
        )
    ).fetchall()

    # Collect unique usernames
    users_to_process = set()
    for row in rows:
        if row.white:
            users_to_process.add(row.white)
        if row.black:
            users_to_process.add(row.black)

    total_users = len(users_to_process)
    print(f"Found {total_users} unique usernames to process.")

    # -------------- Estimated Time & Print --------------
    estimated_time_sec = total_users * 0.5  # 0.5 seconds per user
    estimated_minutes = int(estimated_time_sec // 60)
    estimated_seconds = int(estimated_time_sec % 60)

    if estimated_minutes == 0:
        print(f"Estimated time to process: ~{estimated_seconds} seconds.")
    else:
        print(
            f"Estimated time to process: ~{estimated_minutes} min {estimated_seconds} sec."
        )

    last_report_time = time.time()
    processed_count = 0

    # -------------- Process Each User --------------
    for username in users_to_process:
        user_json = get_user_data_from_api(username)
        if not user_json:
            # no data, skip
            processed_count += 1
            continue

        # user_json["id"] is the unique lichess ID
        if user_exists_in_lichess_users(user_json["id"]):
            print(
                f"User {username} (lichess ID: {user_json['id']}) already in DB. Skipping."
            )
            mark_profile_updated_for_username(username)
            processed_count += 1
        else:
            try:
                insert_user_data(user_json)
                mark_profile_updated_for_username(username)
                processed_count += 1
            except Exception as e:
                print(
                    f"Error inserting user {username} (lichess ID: {user_json['id']}): {e}"
                )
                session.rollback()  # rollback so future inserts won't fail

        # Periodic progress update every 30 seconds
        if (time.time() - last_report_time) >= 30:
            remaining = total_users - processed_count
            print(f"Processed {processed_count}/{total_users}. Remaining: {remaining}.")
            last_report_time = time.time()

        # Sleep for rate limiting
        time.sleep(0.5)

    # -------------- Completion --------------
    print(
        "Finished processing users. tv_channel_games rows now updated for each username."
    )


if __name__ == "__main__":
    main()
