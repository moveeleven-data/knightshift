📈 Project Progress – KnightShift

A running log of major development milestones, current state, and future plans for the KnightShift data pipeline.

---------------------------------

🗓 April 16, 2025

April 16, 2025 – Full Airflow Integration & Debugging Pipeline

Today, we successfully transitioned the KnightShift pipeline to run entirely through Apache Airflow using Docker
Compose. This marked a major milestone in maturing the project into a production-grade orchestration system. We
containerized the ingestion, cleaning, and enrichment scripts, built custom Docker images for both the pipeline and
Airflow, and configured the Airflow scheduler and webserver to manage task execution and DAG visibility. After launching
Airflow at localhost:8080, we triggered the knightshift_pipeline DAG, verified each task (ingestion → cleaning →
enrichment) succeeded, and confirmed that data flowed end-to-end into the tv_channel_games and lichess_users tables
within a containerized PostgreSQL instance.

Throughout the process, we encountered and resolved a range of critical issues. The pipeline container was unable to
detect Postgres readiness due to misconfigured networking (PGHOST=localhost instead of PGHOST=db). We resolved AWS
credential errors and SQLAlchemy connection failures by forwarding environment variables through docker-compose.yml,
ensuring every container had access to the necessary keys, secrets, and database config. We also faced Python 3.8
compatibility issues, such as set[str] type annotations, which were fixed by reverting to the older Set[str] syntax.
Crucially, we learned to debug from inside the containers—running docker compose exec airflow bash and executing failing
Python scripts manually—so we could iterate quickly and view full tracebacks without rebuilding images. This technique
proved invaluable and should be part of any Docker-based debugging workflow.

One persistent pain point was managing environment variables across local dev, Docker Compose, and Airflow. While
storing secrets and credentials in a .env.local file improves maintainability and security, juggling environment values
across multiple execution contexts introduced brittleness and confusion. Scripts occasionally failed due to incorrect
assumptions about the runtime environment. The broader takeaway is that multi-environment setups require disciplined
separation of environment-specific config and runtime logic. In the future, we may introduce centralized configuration
utilities, or shift to secrets managers or .env auto-detection logic to better isolate dev from prod. For now,
standardizing execution through Airflow avoids these pitfalls, ensures consistent behavior, and lets us focus on
stability and scaling instead of debugging broken dev workflows.

---------------------------------

🗓 April 12, 2025

Fully Containerized Storage:

Replaced local PostgreSQL with a Dockerized Postgres container for all ingestion, cleaning, and enrichment steps.

All pipeline scripts now correctly read credentials from AWS Secrets Manager and respect environment flags to switch
between local and container contexts.

Script + Env Overhaul:

Updated .env.local to point to 127.0.0.1:55432 for local scripts (connecting to Dockerized DB).

Updated .env.docker to use PGHOST=db for Docker-to-Docker internal communication.

Confirmed secrets LichessDBCreds_Docker and LichessDBCreds are being correctly used depending on context.

Verified End-to-End Functionality:

Local scripts connect to Dockerized DB as expected (RUNNING_IN_DOCKER=false).

Full pipeline runs inside Docker using container-internal networking (RUNNING_IN_DOCKER=true).

Game ingestion, validation, and enrichment confirmed writing to the correct database (inside container).

Current Status:

-PostgreSQL fully containerized via docker-compose
-Local scripts target Docker DB via port 55432
-Docker container targets DB via internal hostname db
-Both .env.local and .env.docker are correctly configured
-AWS Secrets Manager loads DB credentials successfully
-Game ingestion + enrichment write into the correct containerized DB
-Local system Postgres can now be safely disabled (optional cleanup)

Docker Compose Enhancements:

Confirmed docker-compose.yml orchestration of both Postgres and pipeline services.

Cleaned up Postgres volume with docker compose down -v to reset DB state.

Ensured persistent volume pg_data stores initialized database across reboots.

Corrected ports config for safe local exposure; retained 5432:5432 for host access during development.

Schema Initialization & Documentation:

Mounted schemas/ folder into Postgres using ./schemas:/docker-entrypoint-initdb.d to enable auto-initialization.

Verified tv_channel_games.sql and lichess_users.sql are correctly executed during first-time container startup.

Extended schema changelog to include initialization via raw SQL + Docker Compose integration.

Added `ingested_at TIMESTAMP` column to `tv_channel_games` to track arrival time of each record.

Logging & Debugging:

Verified that logs/pipeline.log captures ingestion, cleaning, and enrichment steps.

stdout and stderr now routed to terminal and log file for traceability.

Checked that PGHOST overrides work correctly inside Docker, ensuring consistent connectivity.

Project Hygiene & Clarity:

Removed obsolete local test databases and ensured schema initialization always reflects version-controlled SQL.

Confirmed clean docker compose build and up execution from scratch, with schema and logs persisting as expected.

Ensured rows with NULL `validation_notes` are reprocessed by resetting `is_validated` to false via SQL patch

Verified deletion logic triggers on invalid `result` values.

Added data_dictionary.md

Added backups folder

Validation Column Overhaul:

Renamed updated column to is_validated for semantic clarity.

Dropped redundant is_valid field from schema and scripts after audit confirmed is_validated fully captures validation
state.


---------------------------------

🗓 April 1, 2025

Pipeline Execution & Modularization:

Modularized main.py into run_ingestion.py, run_cleaning.py, and run_enrichment.py under src/pipeline/.

Scripts can now be triggered independently via Airflow DAGs, cron jobs, or CLI.

Created run_knightshift.bat for Windows-friendly orchestration.

Project Structure & Docs:

Added README.md files to all major folders (src/db, utils, pipeline, etc.) for self-contained clarity and navigation.

Renamed archive/ to legacy/ and moved inactive scripts inside for better organization.

Created schemas/ folder with version-controlled schema definitions for Postgres tables.

Created logs/ folder and redirected script logging output there. .gitkeep ensures folder is preserved in version
control.

Testing Foundations Expanded:

Finalized tests/ structure and Pytest setup for consistent local execution.

Added unit tests for:

pgn_parser.py (PGN header + move parsing)

db_utils.py (DB URL + token handling)

get_games_from_tv.py (build_game_data, parse_rating logic)

Verified all tests pass with proper path resolution and local import handling.

Database Logic Refactor:

Extracted build_game_data() and upsert_game() into src/db/game_upsert.py.

Added full type hints, robust error handling, and transaction safety via session.begin().

Improved testability by decoupling ingestion from persistence logic.

Configuration & Git Hygiene:

Updated .gitignore to handle logs/, .env*, compiled files, and Pytest artifacts.

Cleaned up stray log.txt files and added .gitkeep to persist logs/ structure.


---------------------------------

🗓 March 31, 2025

Project Restructuring & Modularization:

Restructured src/ into ingestion/, cleaning/, enrichment/, archive/, and utils/ folders.

Moved inactive scripts (e.g., update_all_games.py, get_games_from_users.py) into archive/.

Created utils/pgn_parser.py to handle PGN parsing independently (used in get_games_from_tv.py).

User Profile Pipeline Improvements:

Renamed add_users.py → backfill_user_profiles.py for clarity.

Refactored script to improve modularity, readability, and logging.

Improved error handling and exit behavior on failed inserts or malformed API data.

Data Cleaning Enhancements:

Expanded validate_tv_channel_games.py to check for missing required fields (white, black, moves, result).

Validated Lichess game URLs and cleaned malformed ELO values.

Removed invalid rows and marked cleaned records with updated=True and is_valid=True.

Docs & Configuration:

Updated README to reflect new project structure and script responsibilities.

Confirmed consistency in .env.local, logging format, and config loading across all modules.

Added logging for every script to standardize output and facilitate troubleshooting.


---------------------------------

🗓 March 30, 2025

API Hardening & Rate Limit Safety:

Standardized persistent requests.Session() usage across all API scripts.

Added early exit on HTTP 429 (rate limit) in all relevant scripts.

Centralized error handling and added backoff logic where needed.

User Profile Pipeline Improvements:

Refined add_users.py with:

Connection pooling,

API robustness,

Batch pausing after large inserts.

Game Scripts Enhancements:

get_games_from_tv.py and update_all_games.py updated for API safety and performance.

clean_invalid_games.py confirmed as safe (no Lichess API usage).

Schema & Docs:

Documented lichess_users table schema.

Added primary key and index sections for all major tables.


---------------------------------

🗓 March 25, 2025

User Profile Enrichment + Smart Update Tracking

User Metadata Table Creation:

Designed and created the lichess_users table to store enriched user-level profile data (e.g., ratings, location, real
name, titles, time played, etc.).

Selected the most meaningful subset of attributes from the Lichess user API and mapped them to appropriate Postgres
column types.

Profile Ingestion Script:

Built a new standalone ingestion script that fetches public user profile data from the Lichess API.

Extracted unique usernames from the white and black columns of the tv_channel_games table where profile_updated is
false.

Handled edge cases (e.g., already-ingested users, duplicate usernames across games).

Converted and inserted cleaned user data into lichess_users.

Tracking State with profile_updated:

After each user is successfully inserted, all matching tv_channel_games rows (where the user appears as white or black)
are updated with profile_updated = true.

Skips processing for users who are already present in the lichess_users table.

---------------------------------

🗓 March 24, 2025 (Evening Update)

PostgreSQL Connection Fix: Updated the .env.docker configuration to connect the Docker container to the local Postgres
instance using host.docker.internal as the host.

Docker Compose: Used docker compose up --build to run the pipeline, verified PostgreSQL container connectivity, and
confirmed data ingestion functionality.

Database Interaction: Confirmed that the Dockerized pipeline now interacts successfully with the tv_channel_games table
in the local Postgres database via Docker.

Log Verification: Verified end-to-end pipeline execution, ensuring that logs are properly generated, and the data
pipeline completes as expected.

---------------------------------

🗓 March 24, 2025

Significant Enhancements and Restructuring:

Refactoring: Modularized the pipeline into distinct scripts and created main.py to orchestrate all processes.

CLI Execution: Added a run.sh script for simplified pipeline execution.

Credential Management: Centralized DB and Lichess token loading in db_utils.py, reducing redundancy.

Secure Secrets Handling: Implemented AWS Secrets Manager for environment-driven credential loading (local vs Docker).

Docker Integration: Verified Docker container connectivity to PostgreSQL via IP override (host.docker.internal ➝
192.168.65.254).

Environment Configuration: Updated .env.local and .env.docker to distinguish between local and container contexts.

End-to-End Execution: Successfully ran the pipeline inside Docker using docker run -it, confirming full functionality.

Function Verification: Verified that run_tv_ingestion, run_update_pass, and run_cleaning_pass execute reliably.

To run on Docker:

Run dos2unix on run.sh to ensure it has Unix-style line endings. You can install it on your system if needed.

If you're on Windows, run dos2unix using Git Bash or other terminal tools. If dos2unix is not installed, run the
following command:

bash
Copy
Edit
dos2unix run.sh
To build the Docker image (make sure you're in the project directory where the Dockerfile is):

bash
Copy
Edit
docker build -t knightshift-pipeline .
Run the Docker container with logs:

bash
Copy
Edit
docker run -it --env-file .env.docker knightshift-pipeline

---------------------------------

🗓 December 2024

Initial ingestion system established:

Get Games from Users: Fetches historical PGN data for specific Lichess user IDs and inserts it into the chess_games
table.

Get Games from TV: Continuously streams games from all Lichess TV channels (e.g., blitz, rapid, horde) and inserts
records into the tv_channel_games table. Each row includes metadata such as player names, ELO ratings, time controls,
results, and PGN move text.

Update All Games: Enriches previously ingested records. Uses a Boolean updated column to selectively update stale or
partial rows, optimizing for performance via indexed queries.
