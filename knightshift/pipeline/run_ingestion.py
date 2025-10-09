#!/usr/bin/env python3
# ==============================================================================
# run_ingestion.py  –  Entry point for game ingestion
#   Calls: knightshift.ingestion.get_games_from_tv.run_tv_ingestion
# ==============================================================================

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / "config" / ".env.local")

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from knightshift.ingestion.get_games_from_tv import run_tv_ingestion

if __name__ == "__main__":
    run_tv_ingestion()
