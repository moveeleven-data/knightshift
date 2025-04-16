from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
import subprocess
import os

print("🤖 DAG CWD:", os.getcwd())
print("📁 DAG FILES:", os.listdir())

load_dotenv(dotenv_path=Path("/app/config/.env.local"))  # or wherever your env lives

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="knightshift_pipeline",
    default_args=default_args,
    description="Ingests, cleans, and enriches Lichess data",
    schedule_interval=None,  # Manual trigger for now
    start_date=datetime(2025, 4, 16),
    catchup=False,
    tags=["knightshift", "chess"],
) as dag:

    def ingest_tv_games():
        print("Airflow CWD:", os.getcwd())
        print("Listing files:", os.listdir())
        subprocess.run(["python", "/app/src/pipeline/run_ingestion.py"], check=True)


    def clean_invalid_games():
        subprocess.run(["python", "/app/src/pipeline/run_cleaning.py"], check=True)

    def enrich_game_data():
        subprocess.run(["python", "/app/src/pipeline/run_enrichment.py"], check=True)

    t1 = PythonOperator(
        task_id="ingest_tv_games",
        python_callable=ingest_tv_games,
    )

    t2 = PythonOperator(
        task_id="clean_invalid_games",
        python_callable=clean_invalid_games,
    )

    t3 = PythonOperator(
        task_id="enrich_game_data",
        python_callable=enrich_game_data,
    )

    t1 >> t2 >> t3
