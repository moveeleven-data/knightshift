Project Progress – KnightShift

A running log of major development milestones, current state, and future plans for the KnightShift data pipeline.

## May 21, 2025

Today, I confirmed the stable startup of the Flask API container, ensuring full
database integration and live routes. In the process, I removed the experimental
pg8000 support and reverted to psycopg2, prioritizing reliability and
compatibility across Flask, SQLAlchemy, and Airflow. I also added a minimal
HTML-serving layer for health checks and metrics monitoring, setting the
foundation for future enhancements. Automatic database initialization and
Airflow user creation were successfully configured through the
`airflow db migrate` and `user bootstrap` commands in the Docker Compose setup.
Looking ahead, a clean and user-friendly metrics dashboard is in the pipeline
for further development.

Additionally, I finalized the Flask API integration with the KnightShift project,
marking the completion of the Flask-serving layer. The application now includes
real-time metrics displaying game statistics and player data through clean,
responsive HTML templates. I optimized the routes for games, players, and
metrics, ensuring efficient dynamic data fetching with pagination and filtering.
Notable improvements include the addition of detailed player statistics,
game history, and ratings across multiple formats, alongside tracking the most
popular game openings. The system now uses SQLAlchemy and psycopg2 for stable
database interactions, with comprehensive session and error logging. This marks
the conclusion of the Flask API development chapter, focusing on stability and
scalability, and setting the stage for future project enhancements.

---

## May 20, 2025

### [flask-api] Compatibility Fixes, Refactor, and Stability Pass

Resolved deep Flask compatibility issues blocking Airflow boot: downgraded
`flask==2.0.2` and `werkzeug==2.0.2` to align with Airflow 2.8.1 constraints
(was failing due to deprecated `flask.json.provider`). Replaced broken
`auth_manager` values (`None`, `FabAuthManager`, etc.) with valid
`airflow.auth.managers.fab.fab_auth_manager.FabAuthManager` path. Rebuilt
Docker images with pinned constraints and verified clean startup. Flask API
container is healthy and stable.

Next: finalize route validations, add response schema handling, and test DB
integration with pg8000 in a real DAG context.

---

## May 20, 2025

Alembic Integration Attempt:
Attempted to integrate Alembic for schema migrations in the KnightShift project
but encountered numerous issues related to migrations, revisions, and
configurations, particularly in the Dockerized Airflow pipeline. Despite
multiple manual fixes, Alembic proved inefficient and unsuitable for the setup.

Pivot to Simpler Solution:
Decided against using Great Expectations and dbt for data validation and
transformation. Instead, focused on enhancing the existing Airflow DAG by
implementing a robust database health check. This ensures that the DAG will
not continue to attempt data ingestion or writing if the database is not in a
healthy state, effectively preventing unnecessary pipeline execution.

Outcome:
This approach simplifies the pipeline, avoiding unnecessary complexity while
ensuring that the process only continues when the database is ready and functional.


✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦

# Checkpoint Reached → knightshift_foundation (observability sim)

## May 4, 2025

Created a fully self-contained snapshot of the KnightShift pipeline under `checkpoints/knightshift_foundation`, capturing both the full working batch pipeline and a simulated observability stack.

Originally built as a standalone Prometheus + Grafana simulation environment, this folder now includes:
- A fake ingestion service (`prometheus_metrics.py`) emitting synthetic metrics to port `8000`
- Prometheus scraping and Grafana dashboarding (ideal for local experimentation)
- The complete `knightshift/` and `airflow/` folders, fully integrated
- A renamed `.env.pipeline` and localized volume paths for isolation

The snapshot runs its own dedicated Postgres database (`pg_data`) and is fully decoupled from the main project — confirmed to not share any data or state. It includes a real DAG, schema init files, and a production-style pipeline that can run independently of the main environment.

Airflow is available at [localhost:8081](http://localhost:8081) (`admin` / `admin`), Prometheus at [localhost:9090](http://localhost:9090), and Grafana at [localhost:3000](http://localhost:3000), with a custom dashboard preloaded. A previously backed-up Grafana dashboard was successfully restored into this environment.

This environment is launched directly from its own folder using:

docker compose up --build

╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷
                  
Note: The main KnightShift pipeline remains managed through infra/compose/, which starts core services including Airflow, Postgres, and DAG scheduling via its own docker compose up. Prometheus and Grafana have been removed from the main stack and now live exclusively within this snapshot. The knightshift_foundation checkpoint runs fully independently for UI prototyping, testing, and historical preservation.

Also added .dockerignore files to infra/docker/ and checkpoints/knightshift_foundation/ to prevent container bloat.
                
╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷╷

Reflections & Structure Going Forward:

This marks a major architectural milestone — the first modular, observable, and reproducible state of KnightShift.

The checkpoints/ folder will serve as the canonical space for frozen, runnable versions of the pipeline at key milestones.

The experiments/ folder remains a sandbox for lightweight prototypes, one-off technical deep dives, or metric testing.

All active development continues in the main project folder, which remains the central workspace for pipeline evolution.
    

✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧✦✧


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
