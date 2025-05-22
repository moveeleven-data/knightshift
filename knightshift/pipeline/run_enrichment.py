#!/usr/bin/env python3
"""
run_enrichment.py

Entry point for user profile enrichment. Runs backfill_user_profiles.main
and backfill_opening_names.main.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load env vars from .env.local
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / "config" / ".env.local")

# Add project root (knightshift/) to sys.path
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import enrichment logic
from knightshift.enrichment.backfill_user_profiles import run_backfill_user_profiles
from knightshift.enrichment.backfill_opening_names import run_backfill_opening_names


def run_enrichment_pipeline():
    run_backfill_user_profiles()  # existing backfill user profiles
    run_backfill_opening_names()  # new backfill opening names logic


if __name__ == "__main__":
    run_enrichment_pipeline()
