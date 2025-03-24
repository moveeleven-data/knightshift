import logging

from get_games_from_tv import run_tv_ingestion
from update_all_games import run_update_pass
from clean_invalid_games import run_cleaning_pass

logging.basicConfig(
    filename="pipeline.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

if __name__ == "__main__":
    run_tv_ingestion()
    run_update_pass()
    run_cleaning_pass()
