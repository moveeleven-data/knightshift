import logging
from get_games_from_tv import run_tv_ingestion
from update_all_games import run_update_pass
from clean_invalid_games import run_cleaning_pass

logging.basicConfig(
    filename="pipeline.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

def log_and_run(msg, func):
    print(f"Starting: {msg}")
    logging.info(f"Starting: {msg}")
    func()
    print(f"Finished: {msg}")
    logging.info(f"Finished: {msg}")

if __name__ == "__main__":
    log_and_run("TV Ingestion", run_tv_ingestion)
    log_and_run("Cleaning Invalid Games", run_cleaning_pass)
    log_and_run("Game Update", run_update_pass)
