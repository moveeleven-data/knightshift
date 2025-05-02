import sys
from pathlib import Path
import pytest
from unittest.mock import patch
import logging

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Fixture for mocking db credentials
@pytest.fixture(scope="function")
def mock_load_db_credentials(monkeypatch):
    def mock_load_db_credentials_function():
        return {
            "PGUSER": "testuser",
            "PGPASSWORD": "testpassword",
            "PGHOST": "localhost",
            "PGPORT": "5432",
            "PGDATABASE": "knightshift_test",
        }

    monkeypatch.setattr(
        "knightshift.utils.db_utils.load_db_credentials",
        mock_load_db_credentials_function,
    )


def test_run_tv_ingestion(mock_load_db_credentials):
    logging.basicConfig(level=logging.CRITICAL)
    logger = logging.getLogger("test_run_tv_ingestion")

    # Patch time.time to simulate 1 second passing after the first loop
    start_time = 100000.0
    times = [start_time, start_time + 0.1, start_time + 1.1]

    def fake_time():
        return times.pop(0) if times else start_time + 100  # End after 3 iterations

    with (
        patch(
            "knightshift.ingestion.get_games_from_tv.time.time", side_effect=fake_time
        ),
        patch("knightshift.ingestion.get_games_from_tv.CHANNELS", ["racingKings"]),
        patch(
            "knightshift.ingestion.get_games_from_tv._stream_channel"
        ) as mock_stream_channel,
        patch("knightshift.ingestion.get_games_from_tv.time.sleep") as mock_sleep,
        patch("knightshift.ingestion.get_games_from_tv.requests.get") as mock_get,
    ):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_stream_channel.return_value = None
        mock_sleep.return_value = None

        from knightshift.ingestion.get_games_from_tv import run_tv_ingestion

        run_tv_ingestion()

        assert mock_stream_channel.call_count == 1
        mock_sleep.assert_any_call(5)
        assert mock_sleep.call_count == 1
