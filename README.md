# KnightShift: Lichess Data Pipeline

KnightShift is a production-style chess data pipeline that ingests real-time
Lichess TV games, parses PGN data, and stores structured game records in a
PostgreSQL database.

This project simulates real-world data engineering practices—secure
secrets management, stream-style ingestion, schema-aware transformation,
and upsert logic.

---

### 🎥 Demo: KnightShift in Action

[![Watch the demo](docs/KnightShift.jpg)](https://youtu.be/CAupEMTL6uY)  
Click the thumbnail to watch a short video demo of the KnightShift data pipeline in action.

---

## What It Does

- Streams live chess games from multiple Lichess TV channels (e.g. blitz, rapid, horde).
- Parses PGN-formatted chess data into structured records.
- Transforms raw PGN into a clean schema: player names, ratings, results, time control, etc.
- Performs upserts into PostgreSQL using SQLAlchemy Core.
- Uses AWS Secrets Manager to securely load DB credentials.

---

## Tech Stack

- **Python 3.10+**
- **PostgreSQL**
- **SQLAlchemy Core**
- **AWS Secrets Manager** (`boto3`)
- **Requests** (API interaction)

---

## Project Structure

```
knightshift/
├── airflow/
│   ├── dags/                   # Airflow DAGs
│   ├── logs/                   # Task and execution logs
│   ├── plugins/                # Airflow custom plugins
├── annotations/                # Annotations and exploration docs
├── backups/                    # Backup logs and files
├── config/                     # Configuration files
├── docs/                       # Documentation (e.g., changelogs, architecture)
├── explorations/               # Exploration of data models (e.g., NoSQL, Graph)
├── infra/                      # Infrastructure configuration (Docker, Compose)
├── knightshift/                # Core pipeline scripts (ingestion, cleaning, enrichment)
├── logs/                       # Pipeline logs
├── schemas/                    # Database schemas and migrations
└── scripts/                    # Utility scripts (e.g., run scripts)
```

---

## Secrets Management

The KnightShift pipeline securely pulls database credentials from **AWS Secrets Manager** or a local **`.env`** file, depending on the environment.

Expected secret format:

```json
{
  "PGHOST": "your-db-host",
  "PGPORT": "5432",
  "PGDATABASE": "your-db-name",
  "PGUSER": "your-username",
  "PGPASSWORD": "your-password"    <!-- pragma: allowlist secret -->
}
```

Expected .env file (local development)**

A sample template is provided at `config/.env.template`.

# create your personal copy in the project root
cp config/.env.template .env
# then edit .env and add your real credentials / API keys

---

## How to Run

1. Create a Postgres database and store credentials in AWS Secrets Manager.

2. Install Python dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Run the pipeline:

   ```
   python main.py
   ```

The pipeline fetches Lichess games every 40 seconds for 5 hours, 
processes them, and stores them in your Postgres database.

---

## How to Run with Docker Compose (Airflow + Pipeline)

KnightShift now runs via Docker Compose, orchestrating Postgres, Airflow, and the ingestion worker together.

### Steps

1. Ensure `.env` exists in the project root (copied from the template).

2. (Windows only) Fix line endings in `run.sh`:

dos2unix run.sh

Build and start all services:

docker compose up --build

This will automatically:
- Spin up a local Postgres container
- Launch Airflow (Scheduler, Webserver, Worker)
- Register and schedule the KnightShift ingestion DAG
- Begin streaming games and writing them to Postgres

Access Airflow UI
Open your browser and go to:
http://localhost:8080
Username: admin
Password: admin
      
---

Secrets Detection:

This project uses detect-secrets to prevent committing sensitive data. Known secrets are tracked in .secrets.baseline, which suppresses repeat alerts. If secrets are rotated or removed, regenerate the baseline using detect-secrets scan > .secrets.baseline. This helps maintain security without adding noise to the commit process.
 
---

Restoring Grafana Dashboard from Backup

If you’ve torn down the stack or lost your Grafana dashboard, restore it with the backup located at:

/backups/grafana/grafana_backup_2025-05-03.tar.gz
       

To restore:

Stop any running containers:
docker compose down
        

Restore the Grafana data volume:
docker run --rm \
-v compose_grafana_data:/volume \
-v $(pwd)/backups/grafana:/backup \
alpine \
sh -c "rm -rf /volume/* && tar xzf /backup/grafana_backup_2025-05-03.tar.gz -C /volume"
           

Rebuild and launch the stack:
docker compose up --build

---

## Built By

[Matthew Tripodi](https://github.com/okv627)