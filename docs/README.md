# KnightShift: Lichess Data Pipeline

KnightShift is a production-style chess data pipeline that ingests real-time
Lichess TV games, parses PGN data, and stores structured game records in a
PostgreSQL database.

This project simulates real-world data engineering practices—secure
secrets management, stream-style ingestion, schema-aware transformation,
and upsert logic.

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
  "PGPASSWORD": "your-password"
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

## Future Expansion: Chess Analytics Pipeline (Multi-Source)

This project will evolve into a full **Chess Analytics Pipeline** with:

### Multiple Data Sources

- **Lichess (Real-Time):** PGN from TV stream and export API
- **Kaggle Archive:** Millions of historical games
- **FIDE Ratings:** Public CSVs with official player data

### Architecture Components

- **Staging in RDS (PostgreSQL)**
- **Raw Data in S3 Buckets**
- **Transformation Jobs via AWS Glue or Python**
- **Partitioned Tables & Concurrency Controls**
- **Analytics Layer in Redshift or a second Postgres**
- **Dashboards with AWS QuickSight**

### Planned Expansion by Month

**Month 1:**

- Refactor ingestion scripts
- Local Docker + Postgres setup
- Create first working Dockerfile

**Month 2:**

- Automate ingestion via cron or Airflow (locally)
- Add simple data validation (e.g. ELO range checks)

**Month 3:**

- Partition Postgres by date
- Add concurrency safety (transactions or row locks)
- Add full PGN enrichment via Lichess export API

**Month 4:**

- Deploy ingestion & enrichment in Kubernetes (Minikube/Kind)
- Run Airflow inside K8s cluster

**Month 5:**

- Add Great Expectations for data quality
- Monitor jobs with Prometheus & Grafana

**Month 6:**

- Load to Redshift or warehouse instance
- Create aggregated views (fact/dimension tables)
- Build public dashboards with QuickSight

---

## Final Goal

Build a robust, multi-source chess data pipeline capable of:

- Continuous real-time ingestion
- Historical + official data merging
- Schema evolution
- Analytics-ready warehousing
- Production-grade monitoring
- BI dashboards

---

## Built By

[Matthew Tripodi](https://github.com/okv627)

Let me know if you’d like to see the public dashboard or learn more about
the architecture behind KnightShift.
