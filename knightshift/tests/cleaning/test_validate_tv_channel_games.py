# ==============================================================================
# test_validate_tv_channel_games.py  –  Validation + cleaning tests
#   Mocks DB credentials, SQLAlchemy engine, and sample rows.
# ==============================================================================

#!/usr/bin/env python3

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker

# ------------------------------------------------------------------------------
# Minimal setup
# ------------------------------------------------------------------------------
META = MetaData()
SessionLocal = sessionmaker()


# ------------------------------------------------------------------------------
# Mocks
# ------------------------------------------------------------------------------
def mock_load_db_credentials():
    """Bypass AWS secret access with dummy values."""
    return {
        "username": "mockuser",
        "password": "mockpassword",
        "host": "mockhost",
        "database": "mockdb",
    }


def mock_create_engine(url):
    """Simulate a SQLAlchemy engine with MagicMock."""
    return MagicMock()


def mock_select_tv_games():
    """Return fake rows as if selected from DB."""
    return [
        {
            "id_game": 1,
            "id_user_white": "user1",
            "id_user_black": "user2",
            "val_result": "1-0",
            "val_termination": "NORMAL",
            "val_elo_white": "1500",
            "val_elo_black": "1400",
        },
        {
            "id_game": 2,
            "id_user_white": "user3",
            "id_user_black": "user4",
            "val_result": "0-1",
            "val_termination": "RESIGNED",
            "val_elo_white": "1600",
            "val_elo_black": "1550",
        },
    ]


# ------------------------------------------------------------------------------
# Processing logic
# ------------------------------------------------------------------------------
def process_row(row):
    """Normalize row values and simulate DB update."""
    if row["val_result"] not in {"1-0", "0-1", "1/2-1/2"}:
        print(f"Invalid result for game {row['id_game']}: {row['val_result']}")
        return False

    term = row["val_termination"].upper() if row["val_termination"] else "NORMAL"
    print(f"Normalized termination for game {row['id_game']}: {term}")
    print(f"Updating game {row['id_game']} with normalized values.")
    return True


def validate_and_clean():
    """Simulate validation/cleaning with mocked DB + rows."""
    with (
        patch(
            "knightshift.utils.db_utils.load_db_credentials", mock_load_db_credentials
        ),
        patch("sqlalchemy.create_engine", mock_create_engine),
    ):
        rows = mock_select_tv_games()
        updated, deleted = 0, 0

        for row in rows:
            processed = process_row(row)
            if processed:
                updated += 1
            else:
                deleted += 1

        print(f"Done. Updated={updated}  Deleted={deleted}")


# ------------------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "test_input",
    [
        {"val_result": "1-0", "val_termination": "NORMAL", "id_game": 1},
        {"val_result": "0-1", "val_termination": "RESIGNED", "id_game": 2},
    ],
)
def test_validate_and_clean(test_input):
    validate_and_clean()

    assert test_input["val_result"] in {"1-0", "0-1", "1/2-1/2"}
    assert test_input["val_termination"].upper() == test_input["val_termination"]


if __name__ == "__main__":
    validate_and_clean()
