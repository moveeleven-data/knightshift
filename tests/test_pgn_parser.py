import sys
import pytest
from pathlib import Path
from utils.pgn_parser import parse_pgn_lines

# Add the 'src' folder to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

def test_parse_pgn_lines_basic():
    # Example PGN lines
    pgn_lines = [
        b'[Event "TestEvent"]',
        b'[Site "https://lichess.org/abc123"]',
        b'[Date "2025.04.01"]',
        b"",
        b"1. e4 e5 2. Nf3 Nc6",
    ]

    # Parse the PGN lines
    game_data = parse_pgn_lines(pgn_lines)

    # Check that headers were extracted
    assert game_data["event"] == "TestEvent"
    assert game_data["site"] == "https://lichess.org/abc123"
    # Moves field should contain the move sequence
    assert "e4 e5" in game_data["moves"]


def test_parse_pgn_lines_no_headers():
    # If no headers are provided, 'moves' should still be parsed
    pgn_lines = [b"1. d4 d5 2. c4 c6 3. Nf3 Nf6"]

    game_data = parse_pgn_lines(pgn_lines)
    # No "event" or "site" keys because no bracketed headers
    assert "event" not in game_data
    assert "site" not in game_data
    assert "d4 d5" in game_data["moves"]


def test_parse_pgn_lines_empty_input():
    # Parsing empty lines should yield an empty dict with "moves" : ""
    pgn_lines = []
    game_data = parse_pgn_lines(pgn_lines)
    # We expect at least a "moves" key but empty
    assert "moves" in game_data
    assert game_data["moves"] == ""
