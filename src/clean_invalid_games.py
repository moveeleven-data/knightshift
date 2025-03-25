import os
import time
import json
from pathlib import Path


import requests
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Table,
    Column,
    String,
    MetaData,
    select,
    delete,
    update,
    text,
    Boolean,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from db_utils import load_db_credentials, get_database_url

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env.local")

creds = load_db_credentials()
print("LOADED DB CREDS:", creds)
DATABASE_URL = get_database_url(creds)

# --- SQLAlchemy Setup ---
engine = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=10, max_overflow=20)
metadata = MetaData()
tv_channel_games_table = Table(
    "tv_channel_games",
    metadata,
    Column("id", String, primary_key=True),
    Column("site", String),
    Column("moves", String),
    # New column: url_valid (Boolean)
    Column("url_valid", Boolean, nullable=True),
)
Session = sessionmaker(bind=engine)
session = Session()

# --- URL Checking Function ---
def is_url_invalid(url):
    response = requests.get(url)
    time.sleep(1)  # Fixed pause of 1 second per request
    return response.status_code == 404

# --- Main Cleaning Operation ---
def run_cleaning_pass():
    print("Starting invalid game cleaning operation...")
    games = session.execute(
        select(tv_channel_games_table).where(
            tv_channel_games_table.c.url_valid.is_(None)
        )
    ).fetchall()
    total_unchecked = len(games)

    # Calculate an estimated processing time:
    # - Each URL check takes about 1 second.
    # - Every 2500 checks will incur an extra 900 seconds (15 minutes) pause.
    estimated_time_seconds = total_unchecked + ((total_unchecked // 2500) * 900)
    estimated_time_minutes = estimated_time_seconds / 60
    print(f"Found {total_unchecked} games to check. "
          f"Estimated time to complete: ~{estimated_time_minutes:.2f} minutes.")

    total_checked = 0
    total_deleted = 0
    start_time = time.time()
    last_summary_time = start_time

    for game in games:
        game_id = game.id
        url = game.site
        total_checked += 1

        if is_url_invalid(url):
            session.execute(
                delete(tv_channel_games_table).where(
                    tv_channel_games_table.c.id == game_id
                )
            )
            session.commit()
            total_deleted += 1
        else:
            session.execute(
                update(tv_channel_games_table)
                .where(tv_channel_games_table.c.id == game_id)
                .values(url_valid=True)
            )
            session.commit()

        if total_checked != 0 and total_checked % 2500 == 0:
            print(f"Checked {total_checked} URLs so far. Pausing for 15 minutes...")
            time.sleep(900)  # 900 seconds = 15 minutes

        # Print a summary every 30 seconds
        if time.time() - last_summary_time >= 30:
            print(
                f"Checked: {total_checked}/{total_unchecked}, Deleted: {total_deleted}"
            )
            last_summary_time = time.time()

    print(
        f"Cleaning complete. Total checked: {total_checked}, Total deleted: {total_deleted}"
    )

if __name__ == "__main__":
    run_cleaning_pass()
