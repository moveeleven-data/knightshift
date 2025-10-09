from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final

import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator
from dotenv import load_dotenv

ENV_FILE: Final[Path] = Path("/app/config/.env.local")
load_dotenv(ENV_FILE, override=True)


# =============================================================================
# Database Health Check
# =============================================================================

def check_database_health() -> None:
    """
    Ensure PostgreSQL is reachable and `tv_channel_games` has records.
    Raises ValueError if unavailable or empty.
    """
    try:
        conn = psycopg2.connect(
            dbname="knightshift",
            user="postgres",
            password=os.getenv("PGPASSWORD"),
            host="db",  # Docker service name for Postgres
            port="5432",
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tv_channel_games;")
        record_count = cursor.fetchone()[0]

        if record_count > 0:
            print(f"[DB HEALTH] OK — {record_count} records found.")
        else:
            raise ValueError("Database reachable, but table is empty.")

    except Exception as exc:
        raise ValueError(f"Database health check failed: {exc}") from exc
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals():
            conn.close()


# =============================================================================
# Helpers
# =============================================================================

def _run_script(script_path: str) -> None:
    """
    Run a Python script as a subprocess.
    Fails if the process returns non-zero.
    """
    subprocess.run(["python", script_path], check=True)


def _make_task(task_id: str, script_rel_path: str) -> PythonOperator:
    """
    Create a PythonOperator that executes a pipeline script
    located in /app/knightshift/pipeline/.
    """
    script_abs = f"/app/knightshift/pipeline/{script_rel_path}"
    return PythonOperator(
        task_id=task_id,
        python_callable=_run_script,
        op_args=[script_abs],
    )


# =============================================================================
# DAG Definition
# =============================================================================

DEFAULT_ARGS: Final[dict] = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="knightshift_pipeline",
    description="Ingest → Clean → Enrich Lichess TV data",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */2 * * *",  # every 2 hours, on the hour
    start_date=datetime(2025, 4, 16),
    catchup=False,
    max_active_runs=1,
    tags=["knightshift", "chess"],
) as dag:

    # 1) Health Check
    database_health_check = PythonOperator(
        task_id="check_database_health",
        python_callable=check_database_health,
    )

    # 2) Ingest
    ingest_tv_games = _make_task("ingest_tv_games", "run_ingestion.py")

    # 3) Clean
    clean_invalid_games = _make_task("clean_invalid_games", "run_cleaning.py")

    # 4) Enrich
    enrich_game_data = _make_task("enrich_game_data", "run_enrichment.py")

    database_health_check >> ingest_tv_games >> clean_invalid_games >> enrich_game_data
