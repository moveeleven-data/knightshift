import sys
from pathlib import Path
from datetime import date, time

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db.game_upsert import build_game_data, parse_rating

def test_parse_rating_valid():
    assert parse_rating("1500") == 1500


def test_parse_rating_invalid():
    assert parse_rating("abc") is None
    assert parse_rating("") is None
    assert parse_rating(None) is None


def test_build_game_data_minimal():
    game = {
        "site": "https://lichess.org/abc123",
        "event": "Casual",
        "date": "2025.01.01",
        "utcdate": "2025.01.01",
        "utctime": "12:00:00",
        "white": "player1",
        "black": "player2",
        "result": "1-0",
        "whiteelo": "2100",
        "blackelo": "2200",
        "whitetitle": "GM",
        "blacktitle": "IM",
        "variant": "standard",
        "timecontrol": "600+0",
        "eco": "C20",
        "termination": "Normal",
        "moves": "1. e4 e5",
    }

    game_data = build_game_data(game)

    assert game_data["id"] == "abc123"
    assert game_data["event"] == "Casual"
    assert game_data["white"] == "player1"
    assert game_data["black_elo"] == 2200
    assert game_data["date"] == date(2025, 1, 1)
    assert game_data["utc_time"] == time(12, 0, 0)
    assert game_data["white_title"] == "GM"
    assert game_data["termination"] == "Normal"
    assert "moves" in game_data
