📈 Project Progress – KnightShift

A running log of major development milestones, current state, and future plans for the KnightShift data pipeline.
              
---------------------------------

# Running & Project Snapshot

## May 4, 2025

KnightShift is a modular, Dockerized data pipeline orchestrated by Airflow, with ingestion, cleaning, enrichment, 
and validation stages. All services (Airflow, Postgres, etc.) are spun up via `docker compose up` from 
`infra/compose/`, which serves as the control hub. This starts the DAG scheduler, web UI, and pipeline 
infrastructure. This manual `cd` + `docker compose up` approach is perfectly fine for local development and 
debugging; to improve portability or automation later, wrap it in a script or use `make`. The observability stack 
(Prometheus/Grafana) lives separately in `experiments/observability_sim/` and can run independently to simulate 
metrics for UI testing or dashboard design without impacting the main pipeline.

---------------------------------
         
# Added Experiment -> Observability Sim

## May 4, 2025

This folder (root/experiments/observability_sim) contains a standalone Prometheus + Grafana simulation environment 
used to test and demonstrate observability concepts **without affecting the core KnightShift pipeline**. It runs a fake ingestion service (`prometheus_metrics.py`) that emits synthetic metrics to port `8000`, which Prometheus scrapes and Grafana visualizes. The setup is designed for local, exploratory use and is decoupled from DAG execution, live data, or batch orchestration. This allows for fast prototyping of metrics and dashboards without interfering with production containers.

As of May 4, 2025, I expanded this environment into a **fully self-contained snapshot of the entire KnightShift 
pipeline**, frozen at a major working checkpoint. I copied over the complete `knightshift/` and `airflow/` folders, 
brought in the production `docker-compose.yml` as `docker-compose.pipeline.yml`, and updated all volume paths to be 
local. I also renamed the main `.env` to `.env.pipeline` to avoid conflicts. The snapshot now runs its own isolated 
Postgres instance with a separate volume (`pg_data`), and I confirmed it does **not** share data with the main pipeline. It includes the real DAG, scripts, schema init files, and a working batch pipeline, but all decoupled from the production environment. Airflow runs on [localhost:8081](http://localhost:8081) (`admin` / `admin`), Prometheus on [localhost:9090](http://localhost:9090), and Grafana on [localhost:3000](http://localhost:3000) (`admin` / `admin`), with a custom dashboard pre-configured to show simulated ingestion metrics.

To run the full environment (including both the observability stack and the real pipeline), navigate to this folder 
and execute: docker compose up

Added `.dockerignore` to infra/docker and /observability_sim.

---------------------------------

## May 3, 2025 - Current project state

KnightShift is fully dockerized and phase-complete: Airflow orchestrates a modular DAG; **Prometheus + Grafana simulate real-time metrics and alerts**, offering a scaffolding for observability without live data connections. CI/CD runs via GitHub Actions with pytest and pre-commit hooks (black, detect-secrets). Code is structured into ingestion, cleaning, enrichment, and utils, with schema managed via versioned SQL, enforced naming, and baseline secrets tracking. The system is stable, reproducible, and runs end-to-end with simulated monitoring, backups, and minimal manual touch. Next: add Great Expectations, integrate Alembic, consider DAG scaling, and prep for cloud or data source expansion.

Note: Prometheus and Grafana are included in this project in a simulated capacity to demonstrate observability 
concepts. In get_games_from_tv.py, Prometheus counters (e.g., games_ingested_total, games_updated_total) are instrumented and incremented during actual ingestion, but no HTTP metrics endpoint is exposed via start_http_server, meaning those metrics exist only in-memory during execution and are discarded when the script exits. A separate script, prometheus_metrics.py, launches a real Prometheus server on port 8000 and simulates ingestion by emitting mock metrics such as request durations, HTTP errors, and game counts. This script is not tied to the ingestion process and exists primarily for UI and dashboard demonstration. Although Docker Compose exposes port 8000 from the pipeline container, Prometheus can only scrape if the simulation script is actively running, which is not the case during real execution. Since the pipeline is a short-lived batch process (~1–2 minutes every 2 hours), Prometheus typically finds no available metrics to scrape.

This limitation reflects a structural mismatch between Prometheus' pull-based model, which assumes long-running services, and the project’s design as a transient, Airflow-orchestrated batch pipeline. Supporting real-time observability in this context would require architectural workarounds like Prometheus Pushgateway or sidecar metric containers to persist state between runs. These solutions, while possible, introduce considerable overhead that is not warranted in this case. The existing simulated setup successfully demonstrates metric design and Grafana dashboarding without requiring full integration. It serves as a learning scaffold and can be adapted or extended in future cloud-native deployments, where observability is often handled more naturally through platform-managed monitoring tools.

--------------------------------- 

## May 2, 2025 – Simulated Grafana Dashboard and Prometheus Integration

Incorporated a **simulated Grafana dashboard** to visualize mock metrics, demonstrating how monitoring could work in production. The dashboard displays data such as games ingested over time, request duration percentiles, HTTP response counts, and simulated alerts for HTTP errors — all driven by scripted Prometheus metrics.

**Prometheus was integrated in simulation mode**, exposing metrics through a standalone script not connected to the actual ingestion pipeline. Tracked values include mocked totals and latencies for HTTP requests, and ingestion metrics like the number of games ingested, added, or updated. These serve as placeholders to model what real observability might look like in a production environment.
         
---------------------------------    

## May 1, 2025 – Test Automation and GitHub CI Integration
Enhanced the CI/CD pipeline by creating two test scripts and integrating them with GitHub Actions for continuous integration. These tests ensure key functionalities, such as game validation and user profile backfilling, work as expected, including validation of TV channel game data and backfill_user_profiles pulling from the Lichess API.

Added additional checks to the validation script to catch edge cases and data anomalies, further improving system robustness. Configured GitHub Actions to run these tests automatically on each push to the master branch, ensuring early detection of potential issues.

---------------------------------    

## April 29, 2025 – Backup Automation and Safety Infrastructure

Implemented a production-aware, beginner-friendly backup system for the KnightShift PostgreSQL database using a 
custom backup.sh script and cron. The script runs pg_dump inside the Docker container via docker exec, compresses the output, logs to backups/backup.log, and automatically cleans up files older than 7 days. It was moved to the project root, made executable, added to version control, and paired with a cron job scheduled for 2:00 AM daily. We also excluded backups/ via .gitignore and recommended ShellCheck for linting.

In parallel, we refactored the entire database schema to adopt a consistent column naming convention (e.g., white → id_user_white, result → val_result, ingested_at → tm_ingested). Scripts were updated accordingly—get_games_from_tv.py, validate_tv_channel_games.py, and backfill_user_profiles.py—with changes to metadata models and logic to reflect the new schema. The system was rebuilt from scratch (docker compose down -v && up --build), and Airflow’s full DAG pipeline passed all tasks successfully.

A versioned migration file (2025-05-01__rename_columns.sql) was added under schemas/ and enforced via a pre-commit hook. All changes were documented in docs/schema_mappings.md, and a Git tag v0.2.0-pre-refactor was created for rollback safety. Finally, PyCharm was configured to connect to the Dockerized Postgres instance for live schema inspection, completing a robust, future-ready setup for Phase 2.

---------------------------------
                          
## April 25, 2025 – Environment Configuration Standardization

Refactored environment variable management by standardizing on a single `.env` file at the project root. Added a `.
env.template` in `config/` to provide a safe, version-controlled reference for required keys. Updated `db_utils.py` 
to load environment variables properly, prioritizing container-level overrides for local and containerized runs. Cleaned up and reorganized `.gitignore` to exclude sensitive files (`.env`, `annotations/`), improving project security and hygiene. Verified that the KnightShift ingestion DAG runs cleanly after the migration.

## April 16, 2025 – Airflow Integration Complete

Successfully transitioned the KnightShift pipeline to run fully through Apache Airflow using Docker Compose. All 
scripts—ingestion, cleaning, enrichment—now run as Airflow tasks, and the web UI confirms their success. Major 
hurdles included incorrect Docker networking (PGHOST was set to localhost instead of db), environment variable 
confusion, and Python version mismatches (e.g., using set[str] in Python 3.8). Debugging inside containers and 
streamlining the environment config made the difference. The pipeline now runs reliably under Airflow, which gives us a production-style orchestration backbone moving forward. The Airflow UI is accessible at [localhost:8080](http://localhost:8080) (`admin` / `admin`).


## April 12, 2025 – Fully Containerized Storage & Environment Stability

PostgreSQL was fully containerized, with scripts reading secrets from AWS Secrets Manager and using different environment configs for local and Docker contexts. We verified that scripts and containers communicate properly across networks, and that schemas auto-initialize on container startup. Logging was routed to pipeline.log, schema logic was centralized, and we cleaned up obsolete databases. We also renamed updated to is_validated for clarity and dropped redundant flags, ensuring all cleaning logic is robust and semantic.

## April 1, 2025 – Modularized Execution and Testing Foundations

We split the monolithic main.py into three separate scripts for ingestion, cleaning, and enrichment. Each can now run independently or through Airflow. We added README.md files across all folders, cleaned up old scripts into a legacy/ directory, and created version-controlled schemas. Unit tests were added for all key logic (PGN parsing, DB utils, upserting), improving reliability and debuggability. Logging and Git hygiene were also improved.

## March 31, 2025 – Structure Overhaul and Data Cleaning Expansion

Restructured the codebase into clear domains: ingestion, cleaning, enrichment, archive, and utils. Refactored user enrichment scripts and added missing data checks in validation. Cleaned invalid rows and marked records using new validation flags. Documentation and config consistency were improved across the board.

## March 30, 2025 – API Hardening and Rate Limit Handling

Introduced persistent session handling and graceful exits on API rate limits. Improved the user enrichment script with batch pausing, error handling, and connection pooling. All key game-related scripts were updated for better performance and safety. Table schemas were documented more clearly, including primary keys and indexes.

## March 25, 2025 – Lichess User Profile Enrichment

Built a new script to pull public profile data from Lichess and store it in a new table, lichess_users. Used smart logic to only fetch data for unprocessed users and track progress with a profile_updated flag. This enrichment pipeline ensures the database has rich, detailed player-level information.

## March 24, 2025 – Docker Connectivity Fixes and Secrets Management

Fixed PostgreSQL connection issues by overriding the host inside Docker. Used Docker Compose for orchestration and confirmed full pipeline functionality inside containers. Environment separation (.env.local vs .env.docker) was finalized, and all sensitive credentials were centralized using AWS Secrets Manager. Successfully ran and logged end-to-end runs using docker run.

## December 2024 – Initial Ingestion System Launched

Developed the first version of the KnightShift pipeline. Scripts were built to fetch Lichess game data from both TV streams and user profiles. Parsed and inserted the data into Postgres, with enrichment logic to avoid duplicate updates. This laid the foundation for the more robust modular system we have today.
