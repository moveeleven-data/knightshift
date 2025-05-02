📈 Project Progress – KnightShift

A running log of major development milestones, current state, and future plans for the KnightShift data pipeline.
                            
---------------------------------    

## May 1, 2025 – Test Automation and GitHub CI Integration

Enhanced the CI/CD pipeline by creating two test scripts and integrating them with GitHub Actions 
for continuous integration. The test scripts were developed to ensure that key functionalities, such as game validation and user profile backfilling, are working as expected. Specifically, we wrote tests for validating TV channel game data and for the backfill_user_profiles process that pulls data from the Lichess API and updates the database.

We also added additional checks to our validation script to ensure that edge cases and potential data anomalies are caught, further improving the robustness of our system.

We then configured GitHub Actions to run these tests automatically on each push to the master branch, ensuring that any new changes are tested before being merged. The integration with GitHub Actions marks a significant improvement in our development workflow, automating the testing process and catching potential issues early.

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

We successfully transitioned the KnightShift pipeline to run fully through Apache Airflow using Docker Compose. All scripts—ingestion, cleaning, enrichment—now run as Airflow tasks, and the web UI confirms their success. Major hurdles included incorrect Docker networking (PGHOST was set to localhost instead of db), environment variable confusion, and Python version mismatches (e.g., using set[str] in Python 3.8). Debugging inside containers and streamlining the environment config made the difference. The pipeline now runs reliably under Airflow, which gives us a production-style orchestration backbone moving forward.

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
