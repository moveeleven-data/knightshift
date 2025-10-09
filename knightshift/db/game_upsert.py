# ==============================================================================
# game_upsert.py  –  Idempotent upsert helper for tv_channel_games
# ------------------------------------------------------------------------------
# Responsibilities:
#   • Normalise raw PGN metadata → dictionary ready for SQLAlchemy
#   • Insert a new row if id not present, otherwise update it
#   • Return True on update, False on insert or failure
# ==============================================================================

from __future__ import annotations

from datetime import datetime, date, time
from typing import Any, Dict, Optional

from sqlalchemy import Table, select, update
from sqlalchemy.orm import Session

from knightshift.utils.logging_utils import setup_logger

LOGGER = setup_logger("game_upsert")

# ------------------------------------------------------------------------------
# Parsing helpers
# ------------------------------------------------------------------------------


def _parse_int(value: Any) -> Optional[int]:
    """
    Safely cast a value to int, or return None if invalid.

    Handles:
      • Integers (1500)
      • Numeric strings ("2400")
      • Empty strings, nulls, "?" → None
    """
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_date(value: str | None, fmt: str = "%Y.%m.%d") -> Optional[date]:
    """Parse a YYYY.MM.DD string to date, else None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, fmt).date()
    except ValueError:
        LOGGER.debug("Bad date %s – stored NULL", value)
        return None


def _parse_time(value: str | None, fmt: str = "%H:%M:%S") -> Optional[time]:
    """Parse an HH:MM:SS string to time, else None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, fmt).time()
    except ValueError:
        LOGGER.debug("Bad time %s – stored NULL", value)
        return None


# ------------------------------------------------------------------------------
# Public helpers
# ------------------------------------------------------------------------------


def build_game_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise raw PGN dict into DB-ready column → value mapping."""
    return {
        "id_game": raw.get("site", "").split("/")[-1],
        "val_event_name": raw.get("event", ""),
        "val_site_url": raw.get("site", ""),
        "dt_game": _parse_date(raw.get("date")),
        "id_user_white": raw.get("white", ""),
        "id_user_black": raw.get("black", ""),
        "val_result": raw.get("result", ""),
        "dt_game_utc": _parse_date(raw.get("utcdate")),
        "tm_game_utc": _parse_time(raw.get("utctime")),
        "val_elo_white": _parse_int(raw.get("whiteelo")),
        "val_elo_black": _parse_int(raw.get("blackelo")),
        "val_title_white": raw.get("whitetitle", ""),
        "val_title_black": raw.get("blacktitle", ""),
        "val_variant": raw.get("variant", ""),
        "val_time_control": raw.get("timecontrol", ""),
        "val_opening_eco_code": raw.get("eco", ""),
        "val_termination": raw.get("termination", ""),
        "val_moves_pgn": raw.get("moves", ""),
        "val_opening_name": raw.get("opening", ""),
        "tm_ingested": datetime.utcnow(),
    }


def upsert_game(session: Session, table: Table, game: Dict[str, Any]) -> bool:
    """
    Insert or update a single game row.

    Returns
    -------
    bool
        True if an existing row was updated,
        False on insert or error.
    """
    game_id = game.get("id_game")
    if not game_id:
        LOGGER.warning("Missing game ID – skipping row.")
        return False

    try:
        with session.begin():
            exists = session.execute(
                select(table.c.id_game).where(table.c.id_game == game_id)
            ).first()

            if exists:
                session.execute(
                    update(table).where(table.c.id_game == game_id).values(game)
                )
                LOGGER.info("Updated game %s", game_id)
                return True
            else:
                session.execute(table.insert().values(game))
                LOGGER.info("Inserted new game %s", game_id)
                return False

    except Exception as exc:  # pragma: no cover
        LOGGER.error("Error upserting game %s – %s", game_id, exc)
        session.rollback()
        return False
