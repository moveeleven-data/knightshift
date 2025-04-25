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
├── logs/
├── backups/
├── docs/
├── airflow/
│   ├── logs/
│   ├── plugins/
│   ├── dags/
│   │   └── knightshift_dag.py
├── docs/
│   ├── CHANGELOG.md
│   ├── README.md
│   ├── failures.md
│   ├── tech_stack.md
│   ├── assumptions.md
│   ├── data_dictionary.md
│   ├── lifecycle_diagram.md
│   ├── data_architecture.md
│   ├── knightshift_overview.md
│   └── schema_reference.md
├── explorations/
│   ├── vector_embeddings/        # Vector DBs (Pinecone, FAISS) – Similarity search
│   ├── graph_queries/            # Graph DBs (Neo4j, Gremlin) – Relationship modeling
│   ├── document_storage/         # Document DBs (MongoDB, Couchbase) – Semi-structured JSON
│   ├── timeseries/               # Time-Series DBs (InfluxDB, TimescaleDB) – Game frequency, ELO over time
│   ├── columnar_vs_row/          # OLAP vs OLTP, analytics workloads
│   ├── key_value_store/          # Redis, DynamoDB-style storage
│   └── README.md
├── src/
│   ├── db/   
│   ├── README.md
│   └── game_upsert.py
│   ├── pipeline/    
│   │   ├── README.md
│   │   ├── run_cleaning.py
│   │   ├── run_enrichment.py
│   │   └── run_ingestion.py
│   ├── ingestion/
│   │   ├── README.md
│   │   └── get_games_from_tv.py
│   ├── cleaning/
│   │   ├── README.md
│   │   └── validate_tv_channel_games.py
│   ├── enrichment/
│   │   ├── README.md
│   │   └── backfill_user_profiles.py
│   ├── utils/
│   │   ├── README.md
│   │   ├── logging_utils.py
│   │   ├── pgn_parser.py
│   │   ├── db_utils.py
│   │   └── init__.py
│   ├── legacy/
│   │   ├── check_urls_of_games.py
│   │   ├── update_all_games.py
│   │   └── get_games_from_users.py
│   ├── __init__.py
│   └── main.py
├── tests/
│   ├── README.md
│   ├── test_pgn_parser.py
│   ├── test_db_utils.py
│   ├── test_get_games_from_tv.py
│   └── test_validation_logic.py
├── schemas/
│   ├── README.md
│   ├── CHANGELOG.md
│   ├── lichess_users.sql
│   └── tv_channel_games.sql
├── .env                 # Renamed .env.docker to .env
├── .gitignore
├── Dockerfile
├── Dockerfile.airflow
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
├── run_knightshift.bat
├── strip_comments.py    # Strips comments from all files and save clean versions
└── run.sh
```

---

## Secrets Management

Credentials are securely pulled from AWS Secrets Manager.

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

To run on Docker:

Run dos2unix on run.sh to ensure it has Unix-style line endings. You can
install it on your system if needed.

If you're on Windows, run dos2unix using Git Bash or other terminal tools.
If dos2unix is not installed, run the following command:

bash
Copy
Edit
dos2unix run.sh
To build the Docker image (make sure you're in the project directory where the
Dockerfile is):

bash
Copy
Edit
docker build -t knightshift-pipeline .
Run the Docker container with logs:

bash
Copy
Edit
docker run -it --env-file .env.docker knightshift-pipeline

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
