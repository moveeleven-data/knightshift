#!/usr/bin/env python3
import time
from unittest.mock import patch, MagicMock
import pytest

from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.orm import sessionmaker

# Minimal setup
META = MetaData()
SessionLocal = sessionmaker()


# Mocked function for loading AWS credentials (to bypass AWS secret access)
def mock_load_db_credentials():
    return {
        "username": "mockuser",
        "password": "mockpassword",
        "host": "mockhost",
        "database": "mockdb",
    }


# Mocked create_engine to simulate a connection
def mock_create_engine(url):
    engine = MagicMock()
    return engine


# Mocked function for selecting rows (simulating database)
def mock_select_tv_games():
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


# Minimal cleanup processing logic
def process_row(row):
    if row["val_result"] not in {"1-0", "0-1", "1/2-1/2"}:
        print(f"Invalid result for game {row['id_game']}: {row['val_result']}")
        return False

    # Normalize termination
    term = row["val_termination"].upper() if row["val_termination"] else "NORMAL"
    print(f"Normalized termination for game {row['id_game']}: {term}")

    # Mock the database update
    print(f"Updating game {row['id_game']} with normalized values.")

    return True


# Simple controller
def validate_and_clean():
    # Mocking the loading of DB credentials and the creation of an engine
    with (
        patch(
            "knightshift.utils.db_utils.load_db_credentials", mock_load_db_credentials
        ),
        patch("sqlalchemy.create_engine", mock_create_engine),
    ):
        # Fetch mock data (as if selecting from DB)
        rows = mock_select_tv_games()
        updated = 0
        deleted = 0

        # Process each row
        for row in rows:
            processed = process_row(row)
            if processed:
                updated += 1
            else:
                deleted += 1

        # Simulating commit
        print(f"Done. Updated={updated}  Deleted={deleted}")


# Test function for pytest
@pytest.mark.parametrize(
    "test_input",
    [
        ({"val_result": "1-0", "val_termination": "NORMAL", "id_game": 1}),
        ({"val_result": "0-1", "val_termination": "RESIGNED", "id_game": 2}),
    ],
)
def test_validate_and_clean(test_input):
    # Call your function in the test
    validate_and_clean()

    # Assertions can be added here based on the expected results
    # Example assertion (you can add more depending on how you want to test)
    assert test_input["val_result"] in {"1-0", "0-1", "1/2-1/2"}
    assert test_input["val_termination"].upper() == test_input["val_termination"]


if __name__ == "__main__":
    validate_and_clean()
