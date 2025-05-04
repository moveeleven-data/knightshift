"""
knightshift_dag.py
~~~~~~~~~~~~~~~~~~
Airflow DAG that orchestrates the **KnightShift** pipeline:

    1. Ingestion   `run_ingestion.py`
    2. Cleaning    `run_cleaning.py`
    3. Enrichment  `run_enrichment.py`

The Python scripts already live inside the *pipeline* container’s image
at **/app/src/pipeline/**, so we simply invoke them with `subprocess.run`.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final

from airflow import DAG
from airflow.operators.python import PythonOperator
from dotenv import load_dotenv

# --------------------------------------------------------------------------- #
# Environment
# --------------------------------------------------------------------------- #
ENV_FILE: Final[Path] = Path("/app/config/.env.local")  # same path in all containers
load_dotenv(ENV_FILE, override=True)

# Optional diagnostics during DAG‑parse (shown once when scheduler parses file)
print("  DAG parse ‑ cwd:", os.getcwd())
print("  DAG parse ‑ dir :", os.listdir())


# --------------------------------------------------------------------------- #
#   Generic helper to call a pipeline script
# --------------------------------------------------------------------------- #
def _run_script(script_path: str) -> None:
    """
    Wrapper that executes `python <script_path>` and fails the task
    if the underlying process returns a non‑zero exit code.
    """
    subprocess.run(["python", script_path], check=True)


def _make_task(task_id: str, script_rel_path: str) -> PythonOperator:
    """
    DRY helper that returns a `PythonOperator` which calls the given script.
    """
    script_abs = f"/app/knightshift/pipeline/{script_rel_path}"
    return PythonOperator(
        task_id=task_id, python_callable=_run_script, op_args=[script_abs]
    )


# --------------------------------------------------------------------------- #
#   DAG definition
# --------------------------------------------------------------------------- #
DEFAULT_ARGS: Final[dict] = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="knightshift_pipeline",
    description="Ingest → Clean → Enrich Lichess TV data",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */2 * * *",  # every 2 hours at HH:00
    start_date=datetime(2025, 4, 16),
    catchup=False,
    max_active_runs=1,
    tags=["knightshift", "chess"],
) as dag:
    # ── 1) Ingest  ────────────────────────────────────────────────────────── #
    ingest_tv_games = _make_task("ingest_tv_games", "run_ingestion.py")

    # ── 2) Clean   ────────────────────────────────────────────────────────── #
    clean_invalid_games = _make_task("clean_invalid_games", "run_cleaning.py")

    # ── 3) Enrich  ────────────────────────────────────────────────────────── #
    enrich_game_data = _make_task("enrich_game_data", "run_enrichment.py")

    # Task‑ordering (T1 → T2 → T3)
    ingest_tv_games >> clean_invalid_games >> enrich_game_data
