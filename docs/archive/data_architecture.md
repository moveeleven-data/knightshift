# KnightShift Data Architecture

This document outlines the architectural decisions and system layout behind the KnightShift chess data pipeline.

---

## Overview

KnightShift is a modular ETL pipeline that ingests live Lichess TV games, transforms and validates them, and stores structured records in PostgreSQL. It runs in both local and Dockerized environments and is built with a production-mirroring mindset to support eventual cloud orchestration and monitoring.

---

## Storage: PostgreSQL via Docker Compose

KnightShift uses a containerized Postgres instance orchestrated through `docker-compose`.

### Features:
- **Image:** `postgres:17`
- **Volume:** `knightshift_pg_data` (persists database across container restarts)
- **Schema Initialization:** SQL scripts from `./schemas/` are mounted into `/docker-entrypoint-initdb.d`, enabling auto-init at container startup.

```yaml
volumes:
  - ./schemas:/docker-entrypoint-initdb.d
Volume Persistence:
Docker volume: pg_data

Filesystem location varies by OS but can be inspected via Docker Desktop or docker volume inspect pg_data.



Pipeline Components

Phase	      Script	                      Description
Ingestion	  get_games_from_tv.py	          Streams PGN data from live Lichess TV endpoints
Cleaning	  validate_tv_channel_games.py	  Applies rules to remove invalid or malformed records
Enrichment	  backfill_user_profiles.py	      Fetches and stores profile-level metadata from the Lichess API

Each module runs independently and is orchestrated via main.py or modular scripts under src/pipeline/. This allows for future Airflow-based orchestration or cron scheduling.



Multi-Environment Resilience

KnightShift supports local and Dockerized contexts through .env.local and .env.docker.
Scripts adapt to their runtime environment using the RUNNING_IN_DOCKER flag and smart hostname overrides.

Context	Env File	               Host	                    Secrets Name
Local	         .env.local	       127.0.0.1:55432	        LichessDBCreds_Docker
Docker Container .env.docker	   db (service name)	    LichessDBCreds_Docker

Inside db_utils.py, PGHOST is overridden when inside Docker to handle internal networking:

if creds["PGHOST"] == "host.docker.internal" and os.getenv("RUNNING_IN_DOCKER"):
    creds["PGHOST"] = "192.168.65.254"


Schema Initialization

tv_channel_games.sql: Main game metadata table, validated and indexed.

lichess_users.sql: Stores enriched player profiles fetched via Lichess API.

These files are version-controlled and mounted into the Postgres container on first boot.



DevOps & Logging

All scripts log to both console and logs/pipeline.log.

Logs include timestamps, script names, and clear debug/error messages.

main.py orchestrates the pipeline and redirects stdout/stderr to ensure centralized observability.

docker-compose.yml maps the logs folder into the container for transparency.



Design Principles

Loosely Coupled Scripts: Each stage is a stand-alone unit, enhancing maintainability and testability.

Separation of Concerns: Ingestion, cleaning, and enrichment logic are kept distinct.

Plan for Failure: The system logs all errors, exits cleanly on rate limits or DB failure, and can resume from the last valid state.

Volume Persistence: Database volumes preserve schema and data across container restarts.

Environment Flexibility: Configuration files (.env.*) and runtime detection support seamless switching between dev and Docker.



Next Steps (Planned Enhancements)

Partition tables by ingestion date to support long-term scalability.

Add backup snapshots from the Postgres volume into backups/.

Simulate raw data staging by storing pre-ingested PGNs in /raw_dumps/ (for eventual S3 sync).

Add automated data quality checks via Great Expectations.

Orchestrate the pipeline using Airflow or Dagster for DAG-based control.



References

Secrets Management: AWS Secrets Manager → db_utils.py

Environment Logic: RUNNING_IN_DOCKER + .env.docker vs .env.local

Volume Mapping: Defined in docker-compose.yml

Lifecycle Flow: See docs/lifecycle_diagram.md