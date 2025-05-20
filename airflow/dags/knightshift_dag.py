from __future__ import annotations

import os
import subprocess
import psycopg2
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


# --------------------------------------------------------------------------- #
#   Database health check (runs every time)
# --------------------------------------------------------------------------- #
def check_database_health() -> None:
    """
    Simple check to see if the database is up and if `tv_channel_games` contains records.
    """
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname="knightshift",
            user="postgres",
            password=os.getenv("PGPASSWORD"),
            host="db",  # Match this with your Docker service name (db)
            port="5432",
        )
        cursor = conn.cursor()

        # Check if the table exists and has records
        cursor.execute("SELECT COUNT(*) FROM tv_channel_games;")
        record_count = cursor.fetchone()[0]

        if record_count > 0:
            print(f"Database is UP, {record_count} records found.")
        else:
            raise ValueError("Database is DOWN or table is empty.")

        cursor.close()
        conn.close()

    except Exception as e:
        raise ValueError(f"Database health check failed: {e}")


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
    schedule_interval="0 */2 * * *",  # every 2 hours at HH:00
    start_date=datetime(2025, 4, 16),
    catchup=False,
    max_active_runs=1,
    tags=["knightshift", "chess"],
) as dag:
    # ── 1) Database Health Check ─────────────────────────────────────────── #
    database_health_check = PythonOperator(
        task_id="check_database_health", python_callable=check_database_health
    )

    # ── 2) Ingest  ────────────────────────────────────────────────────────── #
    ingest_tv_games = _make_task("ingest_tv_games", "run_ingestion.py")

    # ── 3) Clean   ────────────────────────────────────────────────────────── #
    clean_invalid_games = _make_task("clean_invalid_games", "run_cleaning.py")

    # ── 4) Enrich  ────────────────────────────────────────────────────────── #
    enrich_game_data = _make_task("enrich_game_data", "run_enrichment.py")

    # Task‑ordering (database check → ingest → clean → enrich)
    # If `check_database_health` fails, it will stop the rest of the pipeline
    database_health_check >> ingest_tv_games >> clean_invalid_games >> enrich_game_data
