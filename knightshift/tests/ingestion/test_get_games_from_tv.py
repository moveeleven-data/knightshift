# ==============================================================================
# test_get_games_from_tv.py  –  Tests for TV ingestion
#   Uses mocks to simulate API responses and timing loops.
# ==============================================================================

import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ------------------------------------------------------------------------------
# Path setup (ensure project root on sys.path)
# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ------------------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------------------
@pytest.fixture(scope="function")
def mock_load_db_credentials(monkeypatch):
    """Replace DB secrets lookup with mock credentials."""

    def _mocked():
        return {
            "PGUSER": "testuser",
            "PGPASSWORD": "testpassword",
            "PGHOST": "localhost",
            "PGPORT": "5432",
            "PGDATABASE": "knightshift_test",
        }

    monkeypatch.setattr(
        "knightshift.utils.db_utils.load_db_credentials",
        _mocked,
    )


# ------------------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------------------
def test_run_tv_ingestion(mock_load_db_credentials):
    logging.basicConfig(level=logging.CRITICAL)
    logger = logging.getLogger("test_run_tv_ingestion")

    # Fake time values: simulate 1 second passing after first loop
    start_time = 100000.0
    times = [start_time, start_time + 0.1, start_time + 1.1]

    def fake_time():
        return times.pop(0) if times else start_time + 100

    with (
        patch(
            "knightshift.ingestion.get_games_from_tv.time.time", side_effect=fake_time
        ),
        patch("knightshift.ingestion.get_games_from_tv.CHANNELS", ["racingKings"]),
        patch("knightshift.ingestion.get_games_from_tv._stream_channel") as mock_stream,
        patch("knightshift.ingestion.get_games_from_tv.time.sleep") as mock_sleep,
        patch("knightshift.ingestion.get_games_from_tv.requests.get") as mock_get,
    ):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_stream.return_value = None
        mock_sleep.return_value = None

        from knightshift.ingestion.get_games_from_tv import run_tv_ingestion

        run_tv_ingestion()

        assert mock_stream.call_count == 1
        mock_sleep.assert_any_call(5)
        assert mock_sleep.call_count == 1
