# src/db/game_upsert.py

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Table, select, update
from sqlalchemy.orm import Session
from src.utils.logging_utils import setup_logger

logger = setup_logger(name="game_upsert", level="INFO")


def parse_rating(rating_value: str) -> Optional[int]:
    try:
        return int(rating_value)
    except (ValueError, TypeError):
        return None


def build_game_data(game: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": game.get("site", "").split("/")[-1],
        "event": game.get("event", ""),
        "site": game.get("site", ""),
        "date": (
            datetime.strptime(game.get("date", "1970.01.01"), "%Y.%m.%d").date()
            if game.get("date")
            else None
        ),
        "white": game.get("white", ""),
        "black": game.get("black", ""),
        "result": game.get("result", ""),
        "utc_date": (
            datetime.strptime(game.get("utcdate", "1970.01.01"), "%Y.%m.%d").date()
            if game.get("utcdate")
            else None
        ),
        "utc_time": (
            datetime.strptime(game.get("utctime", "00:00:00"), "%H:%M:%S").time()
            if game.get("utctime")
            else None
        ),
        "white_elo": parse_rating(game.get("whiteelo")),
        "black_elo": parse_rating(game.get("blackelo")),
        "white_title": game.get("whitetitle", ""),
        "black_title": game.get("blacktitle", ""),
        "variant": game.get("variant", ""),
        "time_control": game.get("timecontrol", ""),
        "eco": game.get("eco", ""),
        "termination": game.get("termination", ""),
        "moves": game.get("moves", ""),
        "opening": game.get("opening", ""),
        "ingested_at": datetime.utcnow(),
    }


def upsert_game(session: Session, table: Table, game_data: Dict[str, Any]) -> bool:
    game_id = game_data.get("id")
    if not game_id:
        logger.warning("No valid game ID found; skipping row.")
        return False

    try:
        with session.begin():
            existing_game = session.execute(
                select(table).where(table.c.id == game_id)
            ).fetchone()

            if existing_game is None:
                session.execute(table.insert().values(game_data))
                logger.info(f"Inserted new game {game_id}.")
                return False
            else:
                session.execute(
                    update(table).where(table.c.id == game_id).values(game_data)
                )
                logger.info(f"Updated existing game {game_id}.")
                return True

    except Exception as e:
        logger.error(f"Error upserting game {game_id}: {e}")
        session.rollback()
        return False
