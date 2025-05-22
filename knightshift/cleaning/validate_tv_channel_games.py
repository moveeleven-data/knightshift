#!/usr/bin/env python3
"""
validate_tv_channel_games.py
────────────────────────────
• Cleans / normalizes rows in **tv_channel_games**
• Patches NULL / blank fields in **lichess_users**

"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from sqlalchemy import (
    MetaData,
    Table,
    and_,
    create_engine,
    delete,
    or_,
    select,
    update,
)
from sqlalchemy.orm import Session, sessionmaker

# ────────────────────────────────
# Project bootstrap
# ────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]  # knightshift/
import sys as _sys

_sys.path.insert(0, str(ROOT))  # noqa: E702

from knightshift.utils.db_utils import get_database_url, load_db_credentials
from knightshift.utils.logging_utils import setup_logger

# ────────────────────────────────
# Environment / DB
# ────────────────────────────────
load_dotenv(ROOT / "config" / ".env.local")

LOGGER = setup_logger("validate_tv_channel_games")

ENGINE = create_engine(get_database_url(load_db_credentials()))
META = MetaData()
TV_GAMES: Table = Table("tv_channel_games", META, autoload_with=ENGINE)
LICHESS_USERS: Table = Table("lichess_users", META, autoload_with=ENGINE)
SessionLocal = sessionmaker(bind=ENGINE)

# ────────────────────────────────
# Static configuration
# ────────────────────────────────
REQUIRED_FIELDS: Tuple[str, ...] = (
    "id_user_white",
    "id_user_black",
    "val_moves_pgn",
    "val_result",
)
VALID_RESULTS: set[str] = {"1-0", "0-1", "1/2-1/2"}
CANON_TERM: set[str] = {"NORMAL", "TIME_FORFEIT", "RESIGNED", "ABANDONED"}
THROTTLE_DELAY: float = 0  # seconds between rows

# Defaults to back-fill in *lichess_users*
DEFAULT_TEXT: Dict[str, str] = {
    "val_title": "None",
    "val_real_name": "Not Provided",
    "val_location": "Not Provided",
    "val_bio": "Not Provided",
    "val_country_code": "Unknown",
}
DEFAULT_BOOL: Dict[str, bool] = {
    "ind_patron": False,
    "ind_streaming": False,
}


# ────────────────────────────────
# Utility helpers
# ────────────────────────────────
def _to_int(v: Any) -> int | None:
    """Cast to int – None on failure / None input."""
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _validate_required(row) -> Tuple[bool, str]:
    missing = next((f for f in REQUIRED_FIELDS if not getattr(row, f, None)), None)
    return (False, f"Missing field: {missing}") if missing else (True, "")


def _validate_result(row) -> Tuple[bool, str]:
    return (
        (False, f"Invalid result: {row.val_result}")
        if row.val_result not in VALID_RESULTS
        else (True, "")
    )


def _clean_title(raw: str | None) -> str:
    """Keep 'None', upper-case everything else; map 'Unranked' → 'None'."""
    return (
        "None"
        if not raw or raw.strip().lower() in {"none", "unranked"}
        else raw.strip().upper()
    )


def _needs_tv_fix(row) -> bool:
    """True ⇢ row still violates at least one rule."""
    return (
        not row.ind_validated
        or (row.val_opening_eco_code and "?" in row.val_opening_eco_code)
        or (row.val_termination not in CANON_TERM)
    )


# ────────────────────────────────
#  lichess_users patch
# ────────────────────────────────
def _patch_user(session: Session, user_id: str) -> None:
    """Fill NULL / blank profile fields for *user_id* (idempotent)."""
    if not user_id:
        return

    text_conds = [
        or_(
            LICHESS_USERS.c[col].is_(None),
            LICHESS_USERS.c[col] == "",
            LICHESS_USERS.c[col].ilike("unranked") if col == "val_title" else False,
        )
        for col in DEFAULT_TEXT
    ]
    bool_conds = [LICHESS_USERS.c[col].is_(None) for col in DEFAULT_BOOL]

    session.execute(
        update(LICHESS_USERS)
        .where(and_(LICHESS_USERS.c.id_user == user_id, or_(*text_conds, *bool_conds)))
        .values(**DEFAULT_TEXT, **DEFAULT_BOOL)
    )


# ────────────────────────────────
#  Row processor
# ────────────────────────────────
def _process_row(session: Session, row) -> Tuple[bool, bool]:
    """
    Normalise a single *tv_channel_games* record.

    Returns
    -------
    processed : bool
        Always True (function does work for every call).
    was_deleted : bool
        True if the row failed hard validation and was removed.
    """
    notes: List[str] = []

    # ── titles
    title_white = _clean_title(row.val_title_white)
    title_black = _clean_title(row.val_title_black)

    # ── hard validation (may delete row)
    for check in (_validate_required, _validate_result):
        ok, msg = check(row)
        if not ok:
            notes.append(msg)
            session.execute(delete(TV_GAMES).where(TV_GAMES.c.id_game == row.id_game))
            return True, True

    # ── rating casts
    elo_white = _to_int(row.val_elo_white)
    elo_black = _to_int(row.val_elo_black)
    if row.val_elo_white is not None and elo_white is None:
        notes.append("Invalid val_elo_white")
    if row.val_elo_black is not None and elo_black is None:
        notes.append("Invalid val_elo_black")

    # ── ECO “?” → NULL
    eco = (
        None
        if (row.val_opening_eco_code or "").strip() == "?"
        else row.val_opening_eco_code
    )
    if eco is None:
        notes.append("Set val_opening_eco_code to NULL")

    # ── termination mapping
    term_key = (row.val_termination or "").strip().upper()
    term = {
        "TIME FORFEIT": "TIME_FORFEIT",
        "UNTERMINATED": "NORMAL",
        **{t: t for t in CANON_TERM},
    }.get(term_key, "NORMAL")
    if term_key != term:
        notes.append(f"Normalized termination: {row.val_termination} → {term}")

    # ── write back
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
            tm_validated=datetime.utcnow(),  # Set the current timestamp when validated
            val_validation_notes=", ".join(notes) if notes else "Valid",
        )
    )

    # ── patch linked users
    for uid in (row.id_user_white, row.id_user_black):
        _patch_user(session, uid)

    return True, False


# ────────────────────────────────
#  Controller
# ────────────────────────────────
def validate_and_clean() -> None:
    """Entry controller: fetch rows, process, commit."""
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
            except Exception as exc:  # pragma: no cover
                LOGGER.error("Error %s: %s – rolling back", row.id_game, exc)
                session.rollback()

            if idx % 30 == 0:
                LOGGER.info("Processed %d/%d…", idx, len(rows))
            time.sleep(THROTTLE_DELAY)

        session.commit()
        LOGGER.info("Done. Updated=%d  Deleted=%d", updated, deleted)


# ────────────────────────────────
#  CLI
# ────────────────────────────────
if __name__ == "__main__":
    validate_and_clean()
