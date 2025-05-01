import sys
from pathlib import Path

# Add the src folder to sys.path for importing modules
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from cleaning.validate_tv_channel_games import (
    parse_elo,
    is_valid_url,
    should_keep_row,
)


# --- Test parse_elo --- #
@pytest.mark.parametrize(
    "input_val,expected",
    [
        ("1200", 1200),
        ("2500", 2500),
        ("", None),
        (None, None),
        ("abc", None),
    ],
)
def test_parse_elo(input_val, expected):
    assert parse_elo(input_val) == expected


# --- Test is_valid_url --- #
@pytest.mark.parametrize(
    "site,expected",
    [
        ("https://lichess.org/abc123", True),
        ("https://lichess.org/xyz", True),
        ("http://lichess.org/abc", False),
        ("https://chess.com/abc", False),
        (None, False),
        ("", False),
    ],
)
def test_is_valid_url(site, expected):
    assert is_valid_url(site) == expected


# --- Test should_keep_row --- #
def test_should_keep_row_good():
    class FakeRow:
        white = "playerA"
        black = "playerB"
        moves = "1. e4 e5"
        result = "1-0"

    valid, msg = should_keep_row(FakeRow)
    assert valid is True
    assert msg == ""


def test_should_keep_row_missing_moves():
    class FakeRow:
        white = "playerA"
        black = "playerB"
        moves = None
        result = "1-0"

    valid, msg = should_keep_row(FakeRow)
    assert valid is False
    assert "Missing required field: moves" in msg


def test_should_keep_row_invalid_result():
    class FakeRow:
        white = "A"
        black = "B"
        moves = "1. e4 e5"
        result = "2-0"

    valid, msg = should_keep_row(FakeRow)
    assert valid is False
    assert "Invalid result" in msg
