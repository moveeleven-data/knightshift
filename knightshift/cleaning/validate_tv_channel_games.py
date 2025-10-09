# ==============================================================================
# validate_tv_channel_games.py
# ------------------------------------------------------------------------------
# Cleans and normalises rows in tv_channel_games.
#
# Steps:
#   • Validate required fields and result values
#   • Normalise titles, Elo ratings, opening ECO codes
#   • Canonicalise termination values
#   • Mark rows validated or delete invalid ones
# ==============================================================================

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, delete, select, update
from sqlalchemy.orm import Session, sessionmaker

# ------------------------------------------------------------------------------
# Path & Imports
# ------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from knightshift.utils.db_utils import get_database_url, load_db_credentials
from knightshift.utils.logging_utils import setup_logger

# ------------------------------------------------------------------------------
# Environment & Database
# ------------------------------------------------------------------------------

load_dotenv(ROOT / "config" / ".env.local")
LOGGER = setup_logger("validate_tv_channel_games")

ENGINE = create_engine(get_database_url(load_db_credentials()))
META = MetaData()
TV_GAMES: Table = Table("tv_channel_games", META, autoload_with=ENGINE)
SessionLocal = sessionmaker(bind=ENGINE)

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------

REQUIRED_FIELDS = ("id_user_white", "id_user_black", "val_moves_pgn", "val_result")
VALID_RESULTS = {"1-0", "0-1", "1/2-1/2"}
CANON_TERM = {"NORMAL", "TIME_FORFEIT", "RESIGNED", "ABANDONED"}
THROTTLE_DELAY = 0
FORCE_REVALIDATE = True

# ------------------------------------------------------------------------------
# Validators & Helpers
# ------------------------------------------------------------------------------


def _to_int(v) -> int | None:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _validate_required(row) -> Tuple[bool, str]:
    """Ensure all required fields are present."""
    missing = next((f for f in REQUIRED_FIELDS if not getattr(row, f, None)), None)
    return (False, f"Missing field: {missing}") if missing else (True, "")


def _validate_result(row) -> Tuple[bool, str]:
    """Ensure game result is one of the valid values."""
    return (
        (False, f"Invalid result: {row.val_result}")
        if row.val_result not in VALID_RESULTS
        else (True, "")
    )


def _clean_title(raw: str | None) -> str:
    """Normalise player title string (None/unranked → 'None')."""
    return (
        "None"
        if not raw or raw.strip().lower() in {"none", "unranked"}
        else raw.strip().upper()
    )


def _needs_tv_fix(row) -> bool:
    """Decide if a row requires validation or correction."""
    return (
        True
        if FORCE_REVALIDATE
        else (
            not row.ind_validated
            or (row.val_opening_eco_code and "?" in row.val_opening_eco_code)
            or (row.val_termination not in CANON_TERM)
        )
    )


# ------------------------------------------------------------------------------
# Row Processor
# ------------------------------------------------------------------------------


def _process_row(session: Session, row) -> Tuple[bool, bool]:
    """
    Validate and normalise a single row.

    Returns
    -------
    Tuple[bool, bool]
        (processed, was_deleted)
    """
    notes: List[str] = []

    title_white = _clean_title(row.val_title_white)
    title_black = _clean_title(row.val_title_black)

    # Run validations
    for check in (_validate_required, _validate_result):
        ok, msg = check(row)
        if not ok:
            notes.append(msg)
            session.execute(delete(TV_GAMES).where(TV_GAMES.c.id_game == row.id_game))
            return True, True

    # Clean Elo ratings
    elo_white = _to_int(row.val_elo_white)
    elo_black = _to_int(row.val_elo_black)
    if row.val_elo_white is not None and elo_white is None:
        notes.append("Invalid val_elo_white")
    if row.val_elo_black is not None and elo_black is None:
        notes.append("Invalid val_elo_black")

    # Clean ECO code
    eco = (
        None
        if (row.val_opening_eco_code or "").strip() == "?"
        else row.val_opening_eco_code
    )
    if eco is None:
        notes.append("Set val_opening_eco_code to NULL")

    # Canonicalise termination
    term_key = (row.val_termination or "").strip().upper()
    term = {
        "TIME FORFEIT": "TIME_FORFEIT",
        "UNTERMINATED": "NORMAL",
        **{t: t for t in CANON_TERM},
    }.get(term_key, "NORMAL")
    if term_key != term:
        notes.append(f"Normalized termination: {row.val_termination} → {term}")

    # Apply updates
    session.execute(
        update(TV_GAMES)
        .where(TV_GAMES.c.id_game == row.id_game)
        .values(
            val_title_white=title_white,
            val_title_black=title_black,
            val_elo_white=elo_white,
            val_elo_black=elo_black,
            val_opening_eco_code=eco,
            val_termination=term,
            ind_validated=True,
            tm_validated=datetime.utcnow(),
            val_validation_notes=", ".join(notes) if notes else "Valid",
        )
    )

    return True, False


# ------------------------------------------------------------------------------
# Controller
# ------------------------------------------------------------------------------


def validate_and_clean() -> None:
    """Validate and clean all rows in tv_channel_games."""
    with SessionLocal() as session:
        raw_rows = session.execute(select(TV_GAMES)).fetchall()
        rows = [r for r in raw_rows if _needs_tv_fix(r)]

        LOGGER.info("Validating %d row(s)…", len(rows))
        updated = deleted = 0

        for idx, row in enumerate(rows, 1):
            try:
                processed, was_deleted = _process_row(session, row)
                if processed:
                    updated += not was_deleted
                    deleted += was_deleted
            except Exception as exc:
                LOGGER.error("Error %s: %s – rolling back", row.id_game, exc)
                session.rollback()

            if idx % 30 == 0:
                LOGGER.info("Processed %d/%d…", idx, len(rows))

            time.sleep(THROTTLE_DELAY)

        session.commit()
        LOGGER.info("Done. Updated=%d  Deleted=%d", updated, deleted)


if __name__ == "__main__":
    validate_and_clean()
