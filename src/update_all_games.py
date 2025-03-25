import os
import re
import sys
import time
import json
from pathlib import Path

import requests
import boto3
from botocore.exceptions import ClientError
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
    text,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from db_utils import load_db_credentials, get_database_url, get_lichess_token


load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env.local")

creds = load_db_credentials()
print("LOADED DB CREDS:", creds)
DATABASE_URL = get_database_url(creds)

engine = create_engine(DATABASE_URL, poolclass=QueuePool,
                       pool_size=10, max_overflow=20)
metadata = MetaData()

tv_channel_games_table = Table(
    'tv_channel_games', metadata,
    Column('id', String, primary_key=True),
    Column('moves', String),
    Column('updated', Boolean, default=False)  # Add updated column
)

Session = sessionmaker(bind=engine)
session = Session()

def fetch_game_moves(game_id):
    url = f"https://lichess.org/game/export/{game_id}"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        # retrieve token from env variables
        "Authorization": f"Bearer {get_lichess_token()}",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        pgn_text = response.text
        moves = extract_moves_from_pgn(pgn_text)
        return moves
    else:
        print(f"Failed to fetch moves for game {game_id}: {response.status_code}, {response.text}")
        return None

def extract_moves_from_pgn(pgn_text):
    moves_section = False
    moves = []
    for line in pgn_text.splitlines():
        if not line.startswith('[') and line.strip():
            moves_section = True
        if moves_section:
            # Remove %clk annotations
            line = re.sub(r'\{[^}]*\}', '', line).strip()
            moves.append(line)
    return ' '.join(moves)

def update_game_record(game_id, moves):
    session.execute(
        update(tv_channel_games_table)
        .where(tv_channel_games_table.c.id == game_id)
        .values(moves=moves, updated=True)  # Set updated to True
    )
    session.commit()


def run_update_pass():
    batch_size = 1000
    total_updated = 0
    total_failed = 0
    start_time = time.time()

    print("Starting the update operation...")

    # Count how many rows need updating
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM tv_channel_games WHERE updated = FALSE;")
        )
    total_to_update = result.scalar()

    print(f"Total games that need updating: {total_to_update}")

    # Check if the index is being used
    with engine.connect() as conn:
        result = conn.execute(text("EXPLAIN SELECT *"
        "FROM tv_channel_games WHERE updated = FALSE LIMIT 1;"))
        for row in result:
            print(row)

    while True:
        games = session.execute(
            select(tv_channel_games_table).where(tv_channel_games_table.c.updated == False).limit(batch_size)
        ).fetchall()

        if not games:
            break

        for game in games:
            game_id = game.id
            try:
                moves = fetch_game_moves(game_id)
                if moves:
                    update_game_record(game_id, moves)
                    total_updated += 1
                else:
                    total_failed += 1
            except HTTPError as e:
                if e.response.status_code == 429:
                    print("Rate limit hit. Exiting program.")
                    sys.exit(1)
                else:
                    raise

            # Minimal pause to avoid hitting rate limits
            time.sleep(0.5)

            # Print periodic summary every 50 rows
            if (total_updated + total_failed) % 50 == 0:
                elapsed_time = time.time() - start_time
                percentage_complete = (
                    ((total_updated + total_failed) / total_to_update) * 100
                    if total_to_update > 0 else 0  # Avoid division by zero
                )
                eta_seconds = (
                    (elapsed_time / (total_updated + total_failed))
                    * (total_to_update - (total_updated + total_failed))
                    if (total_updated + total_failed) > 0 and total_to_update > 0
                    else 0  # Avoid division by zero
                )
                print(
                    f"Total rows processed: {total_updated + total_failed}, "
                    f"Elapsed time: {elapsed_time:.2f} seconds, "
                    f"Progress: {percentage_complete:.2f}%, "
                    f"Estimated time remaining: {eta_seconds / 60:.2f} minutes"
                )

    # Final summary
    elapsed_time = time.time() - start_time
    percentage_complete = (total_updated / (total_updated + total_failed)) * 100 if (total_updated + total_failed) > 0 else 0
    print(f"Update complete. Total games updated: {total_updated}, Total games failed: {total_failed}, "
          f"Percentage complete: {percentage_complete:.2f}%, Elapsed time: {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    run_update_pass()
