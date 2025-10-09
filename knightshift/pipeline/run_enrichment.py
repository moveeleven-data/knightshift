#!/usr/bin/env python3
# ==============================================================================
# run_enrichment.py  –  Entry point for enrichment
#   Calls:
#     • knightshift.enrichment.backfill_user_profiles.run_backfill_user_profiles
#     • knightshift.enrichment.backfill_opening_names.run_backfill_opening_names
# ==============================================================================

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / "config" / ".env.local")

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from knightshift.enrichment.backfill_user_profiles import run_backfill_user_profiles
from knightshift.enrichment.backfill_opening_names import run_backfill_opening_names


def run_enrichment_pipeline():
    """Run all enrichment stages in sequence."""
    run_backfill_user_profiles()
    run_backfill_opening_names()


if __name__ == "__main__":
    run_enrichment_pipeline()
