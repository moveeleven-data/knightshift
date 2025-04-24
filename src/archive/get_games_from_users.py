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
from sqlalchemy import (
    create_engine,
    Table,
    Column,
    Integer,
    String,
    BigInteger,
    Boolean,
    MetaData,
    select,
    update,
    text,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from src.utils.db_utils import load_db_credentials, get_database_url, get_lichess_token


# Load environment variables
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env.local")

creds = load_db_credentials()
print("LOADED DB CREDS:", creds)
DATABASE_URL = get_database_url(creds)

# Create SQLAlchemy engine using QueuePool
engine = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=10, max_overflow=20)
metadata = MetaData()

# Define the chess_games table
chess_games_table = Table(
    "chess_games",
    metadata,
    Column("id", String, primary_key=True),
    Column("rated", Boolean),
    Column("variant", String),
    Column("speed", String),
    Column("perf", String),
    Column("created_at", BigInteger),
    Column("status", Integer),
    Column("status_name", String),
    Column("clock_initial", Integer),
    Column("clock_increment", Integer),
    Column("clock_total_time", Integer),
    Column("white_user_id", String),
    Column("white_rating", Integer),
    Column("black_user_id", String),
    Column("black_rating", Integer),
)

Session = sessionmaker(bind=engine)
session = Session()

# authenticate with Lichess via token using environment variable
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": f"Bearer {get_lichess_token()}",
}

url = "https://lichess.org/api/stream/games-by-users"


def process_game_event(line):
    game = json.loads(line)
    clock = game.get("clock", {})
    game_data = {
        "id": game["id"],
        "rated": game["rated"],
        "variant": game["variant"],
        "speed": game["speed"],
        "perf": game["perf"],
        "created_at": game["createdAt"],
        "status": game["status"],
        "status_name": game["statusName"],
        "clock_initial": clock.get("initial", 0),
        "clock_increment": clock.get("increment", 0),
        "clock_total_time": clock.get("totalTime", 0),
        "white_user_id": game["players"]["white"]["userId"],
        "white_rating": game["players"]["white"]["rating"],
        "black_user_id": game["players"]["black"]["userId"],
        "black_rating": game["players"]["black"]["rating"],
    }

    # Check if the game already exists
    existing_game = session.execute(
        select(chess_games_table).where(chess_games_table.c.id == game["id"])
    ).fetchone()

    if existing_game is None:
        session.execute(chess_games_table.insert().values(game_data))
        session.commit()
        print(f"Game with id {game['id']} added to the table.")
    else:
        session.execute(
            update(chess_games_table)
            .where(chess_games_table.c.id == game["id"])
            .values(game_data)
        )
        session.commit()
        print(f"Game with id {game['id']} updated in the table.")


def stream_games(user_ids, with_current_games):
    data = ",".join(user_ids)
    params = {"withCurrentGames": str(with_current_games).lower()}

    response = requests.post(
        url, headers=headers, params=params, data=data, stream=True
    )

    if response.status_code == 200:
        print("Connected to the Lichess game stream.")
        for line in response.iter_lines(decode_unicode=True):
            if line.strip():
                try:
                    process_game_event(line)
                except json.JSONDecodeError:
                    print(f"Failed to decode JSON: {line}")
    else:
        print(f"Failed to connect: {response.status_code}, {response.text}")


if __name__ == "__main__":
    user_ids = [
        "LANCELOT_06",
        "Rat_variant",
        "admin_chernishsquad",
        "SavvaVetokhin2009",
        "Golubovsky_Max",
        "Saqochess",
        "Marek_Religa",
        "alfredogto",
        "Capivaramestre92",
        "Chessknock",
        "RazyyBlitzz",
        "iCe_eNerGyTeaM",
        "strawberry11",
        "Salvatore911",
        "KaaliaOfTheVast",
        "semislavpracticer",
        "Chess_Salehard",
        "Yoseqpuedo",
        "Megatronus27",
        "RosaValle",
        "Zaplya",
        "DrHerbst",
        "desperado64",
        "jhedigm",
        "medine2007",
        "El_Papi_Joshe",
        "GrunFail",
        "MrSuccess",
        "hoba_is_back",
        "Outofmyleague",
        "Isco95",
        "Aktinia22",
        "JelenaZ",
        "AbasnavatMiAra",
        "mboldysh",
        "Cryptochess",
        "master05",
        "Gertrude_Weichsel",
        "Edgar_Karagyozyan",
        "DorMaxKnight",
        "leonkiller77",
        "blindcrocodile",
        "Gagarinec",
        "ianina",
        "Holyheinz",
        "mowilli",
        "OreWa",
        "Nouali_Mohamed",
        "Wotgenie",
        "sleepheaddefence",
        "azaraas",
        "NikolaSubicZrinski",
        "ricardosar",
        "jheremiasc",
        "lanturn17",
        "pbkttc",
        "catse21",
        "Ascenso",
        "napolopan",
        "Defendiendome",
        "Ahmad-wien",
        "kormoran_HG",
        "Kola1231",
        "orstaythesame",
        "Dhmayer",
        "pangarezao",
        "tilenbaev",
        "DL-44",
        "Trionalterium",
        "ALATAKKE",
        "Calculus6",
        "T-MUTHUKUMAR",
        "Malemute_Kid_95",
        "neverplayf6againstus",
        "STS62",
        "MeisterPatzer",
        "Permata",
        "xamaycan_senpai",
        "atinyu",
        "jablay36",
        "criquet84",
        "flebo03",
        "aiko12",
        "Lisfisher1",
        "myownwhitestyle",
        "amir01235",
        "Paul_Bishop",
        "Cazamediocres",
        "kepler3",
        "gabitablet83",
        "Anonymous_Beast",
        "chipmunknau",
        "Olvidaloo",
        "carlos-santana",
        "ElGranFreezer03",
        "BassoSiSposaUnUomo",
        "IncredibleFast",
        "Mwamba1409",
        "baneneba",
        "Subhayan_1",
        "yripak",
    ]

    stream_games(user_ids, with_current_games=True)
