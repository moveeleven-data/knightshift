#!/usr/bin/env python3
"""
run_enrichment.py

Entry point for user profile enrichment. Runs backfill_user_profiles.main.
"""

import sys
from pathlib import Path

# Add project root (knightshift/) to sys.path
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Now import your enrichment logic
from src.enrichment.backfill_user_profiles import main

if __name__ == "__main__":
    main()
