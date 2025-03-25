from db_utils import load_db_credentials, get_database_url, get_lichess_token
import time
import json
import os
from datetime import datetime
from pathlib import Path

import requests
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Table,
    Column,
    Integer,
    String,
    Date,
    Time,
    MetaData,
    select,
    update,
)
from sqlalchemy.orm import sessionmaker

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env.local")

creds = load_db_credentials()
print("LOADED DB CREDS:", creds)
DATABASE_URL = get_database_url(creds)

# Fire up the SQLAlchemy engine to connect to the db
# metadata just holds table definitions.
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# authenticate with Lichess via token using environment variable
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": f"Bearer {get_lichess_token()}",
}

# this is how we describe our tv_channel_games table to SQLAlchemy:
tv_channel_games_table = Table(
    'tv_channel_games', metadata,
    Column('id', String, primary_key=True),
    Column('event', String),
    Column('site', String),
    Column('date', Date),
    Column('white', String),
    Column('black', String),
    Column('result', String),
    Column('utc_date', Date),
    Column('utc_time', Time),
    Column('white_elo', Integer),
    Column('black_elo', Integer),
    Column('white_title', String),
    Column('black_title', String),
    Column('variant', String),
    Column('time_control', String),
    Column('eco', String),
    Column('termination', String),
    Column('moves', String)
)

# set up a session to handle reads and writes
Session = sessionmaker(bind=engine)
session = Session()

def parse_pgn(pgn_lines):
    """
    takes a list of lines (from Lichess TV streaming response)
    and builds a 'game_data' dict containing PGN headers and moves
    """

    game_data = {}
    moves = []
    for line in pgn_lines:
        # decode and strip each line
        line = line.decode('utf-8').strip()

        # If a line starts with '[', it's a PGN tag like [White "someUser"].
        if line.startswith('['):
            key, value = line[1:-1].split(" ", 1)
            game_data[key.lower()] = value.strip('"')
        else:
            # not a tag line — just a chunk of move text, so add it.
            moves.append(line)

    # join the moves into a single string
    game_data['moves'] = ' '.join(moves)
    return game_data

def process_game_event(game):
    """
    translates a single parsed PGN dict into a record for our db.
    if the game ID is new, we insert it; if we've seen it before, we update.
    returns True if it was an update, False if it was a new insert.
    """

    # parse ELO rating (sometimes it's missing or not a valid number)
    def parse_rating(rating):
        try:
            return int(rating)
        except (ValueError, TypeError):
            return 0

    # build the dictionary that matches our table schema
    # we do some date/time parsing to turn strings into date/time objects
    game_data = {
        'id': game.get('site', '').split('/')[-1],
        'event': game.get('event', ''),
        'site': game.get('site', ''),

        'date': datetime.strptime(
            game.get('date', '1970.01.01'), '%Y.%m.%d'
        ).date() if game.get('date') else None,

        'white': game.get('white', ''),
        'black': game.get('black', ''),
        'result': game.get('result', ''),

        'utc_date': datetime.strptime(
            game.get('utcdate', '1970.01.01'), '%Y.%m.%d'
        ).date() if game.get('utcdate') else None,

        'utc_time': datetime.strptime(
            game.get('utctime', '00:00:00'), '%H:%M:%S'
        ).time() if game.get('utctime') else None,

        'white_elo': parse_rating(game.get('whiteelo')),
        'black_elo': parse_rating(game.get('blackelo')),
        'white_title': game.get('whitetitle', ''),
        'black_title': game.get('blacktitle', ''),
        'variant': game.get('variant', ''),
        'time_control': game.get('timecontrol', ''),
        'eco': game.get('eco', ''),
        'termination': game.get('termination', ''),
        'moves': game.get('moves', '')
    }

    # if for some reason we didn't get a valid ID, let's just bail
    if not game_data['id']:
        return False

    # check if this game already exists in the db
    existing_game = session.execute(
    select(tv_channel_games_table).where(
        tv_channel_games_table.c.id == game_data['id']
    )
    ).fetchone()

    # if the game is brand new, insert it
    if existing_game is None:
        session.execute(tv_channel_games_table.insert().values(game_data))
        session.commit()
        return False  # means "we added a new record"
    else:
        # otherwise, we update the existing row with any fresh data
        session.execute(
            update(tv_channel_games_table)
            .where(tv_channel_games_table.c.id == game_data['id'])
            .values(game_data)
        )
        session.commit()
        return True  # means "we updated an existing record"

def fetch_ongoing_games(channel, updated_games, added_games):
    """
    hits Lichess endpoint for a given channel i.e. "blitz" or "rapid",
    parses the PGN stream, and updates db with each game found.
    Add game IDs to the right list to show whether game was new or updated
    """

    url = f"https://lichess.org/api/tv/{channel}"
    params = {
        "clocks": False,
        "opening": False
    }
    response = requests.get(url, headers=headers, params=params, stream=True)

    if response.status_code == 200:
        # Lichess sends a stream of PGN lines
        # with an empty line between games
        pgn_lines = []
        for line in response.iter_lines():
            # if it’s not an empty line, add it to the current game
            if line.strip():
                pgn_lines.append(line)
            else:
                # empty line means we’ve reached the end of one game
                if pgn_lines:
                    game = parse_pgn(pgn_lines)
                    # we need the 'site' field to extract the game ID
                    if 'site' in game:
                        # update if it exists, insert if new.
                        if process_game_event(game):
                            updated_games.append(game['site'].split('/')[-1])
                        else:
                            added_games.append(game['site'].split('/')[-1])
                    pgn_lines = []
    else:
        print(f"Failed to connect to channel {channel}: "
              f"{response.status_code}, {response.text}")

def run_tv_ingestion():
    # define the Lichess TV channels to pull from
    channels = [
        "bullet", "blitz", "classical", "rapid", "chess960", "antichess",
        "atomic", "horde", "crazyhouse", "bot", "computer", "kingOfTheHill",
        "threeCheck", "ultraBullet", "racingKings"
    ]

    # track how long the script's been running — time.time() uses seconds,
    # so we set the limit as 10 minutes in seconds
    start_time = time.time()
    time_limit = 600  # 10 minutes × 60 seconds
    total_games_count = 0

    # loop until time runs out or the script is stopped
    while time.time() - start_time < time_limit:
        updated_games = []
        added_games = []

        # fetch from each channel in turn, collect stats on how many
        # records were updated vs. newly added.
        for channel in channels:
            fetch_ongoing_games(channel, updated_games, added_games)
            if channel == "rapid":
                print("Fetching rapid games...")
            if channel == "horde":
                print("Fetching horde games...")
            if channel == "kingOfTheHill":
                print("Fetching kingOfTheHill games...")
        print(f"Batch complete. {len(updated_games)} games updated, "
              f"{len(added_games)} games added.")
        print("Still connected and fetching games...")

        # Update counter with the number of games processed in this batch
        total_games_count += len(updated_games) + len(added_games)
        
        if total_games_count >= 5000:
            print("Fetched 5000 games. Pausing for 15 minutes...")
            time.sleep(900)  # Pause for 15 minutes (900 seconds)
            total_games_count = 0  # Reset the counter after the pause

        # sleep for 40s before we do another round
        # this avoids spamming Lichess too much
        time.sleep(40)

if __name__ == "__main__":
    run_tv_ingestion() 
