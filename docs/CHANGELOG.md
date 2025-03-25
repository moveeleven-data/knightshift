📈 Project Progress – KnightShift

A running log of major development milestones, current state, and future plans for the KnightShift data pipeline.

---------------------------------

🗓 March 25, 2025

User Profile Enrichment + Smart Update Tracking

User Metadata Table Creation:

Designed and created the lichess_users table to store enriched user-level profile data (e.g., ratings, location, real name, titles, time played, etc.).

Selected the most meaningful subset of attributes from the Lichess user API and mapped them to appropriate Postgres column types.

Profile Ingestion Script:

Built a new standalone ingestion script that fetches public user profile data from the Lichess API.

Extracted unique usernames from the white and black columns of the tv_channel_games table where profile_updated is false.

Handled edge cases (e.g., already-ingested users, duplicate usernames across games).

Converted and inserted cleaned user data into lichess_users.

Tracking State with profile_updated:

After each user is successfully inserted, all matching tv_channel_games rows (where the user appears as white or black) are updated with profile_updated = true.

Skips processing for users who are already present in the lichess_users table.

---------------------------------

🗓 March 24, 2025 (Evening Update)

PostgreSQL Connection Fix: Updated the .env.docker configuration to connect the Docker container to the local Postgres instance using host.docker.internal as the host.

Docker Compose: Used docker compose up --build to run the pipeline, verified PostgreSQL container connectivity, and confirmed data ingestion functionality.

Database Interaction: Confirmed that the Dockerized pipeline now interacts successfully with the tv_channel_games table in the local Postgres database via Docker.

Log Verification: Verified end-to-end pipeline execution, ensuring that logs are properly generated, and the data pipeline completes as expected.

---------------------------------

🗓 March 24, 2025

Significant Enhancements and Restructuring:

Refactoring: Modularized the pipeline into distinct scripts and created main.py to orchestrate all processes.

CLI Execution: Added a run.sh script for simplified pipeline execution.

Credential Management: Centralized DB and Lichess token loading in db_utils.py, reducing redundancy.

Secure Secrets Handling: Implemented AWS Secrets Manager for environment-driven credential loading (local vs Docker).

Docker Integration: Verified Docker container connectivity to PostgreSQL via IP override (host.docker.internal ➝ 192.168.65.254).

Environment Configuration: Updated .env.local and .env.docker to distinguish between local and container contexts.

End-to-End Execution: Successfully ran the pipeline inside Docker using docker run -it, confirming full functionality.

Function Verification: Verified that run_tv_ingestion, run_update_pass, and run_cleaning_pass execute reliably.

To run on Docker:

Run dos2unix on run.sh to ensure it has Unix-style line endings. You can install it on your system if needed.

If you're on Windows, run dos2unix using Git Bash or other terminal tools. If dos2unix is not installed, run the following command:

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

Get Games from Users: Fetches historical PGN data for specific Lichess user IDs and inserts it into the chess_games table.

Get Games from TV: Continuously streams games from all Lichess TV channels (e.g., blitz, rapid, horde) and inserts records into the tv_channel_games table. Each row includes metadata such as player names, ELO ratings, time controls, results, and PGN move text.

Update All Games: Enriches previously ingested records. Uses a Boolean updated column to selectively update stale or partial rows, optimizing for performance via indexed queries.

---------------------------------

Near-Term Plans (Q2 2025)

Redirect standard output to a persistent log file (e.g., pipeline.log) via run.sh.

Dockerize the entire application (handling .env, credentials, and PostgreSQL integration).

Set up local automation via cron (Linux/WSL) or Task Scheduler (Windows).


Mid-Term Goals (Spring 2025)

Validate ingested game records with basic data quality checks (e.g., ELO ranges, valid PGN structure).

Investigate and resolve the source of invalid game IDs.

Partition tv_channel_games table by ingestion date for scalability.

Add monitoring utilities to surface ingestion stats and error rates.


Long-Term Vision (Summer 2025)

Stage raw data in AWS S3 and archive invalid records.

Deploy containerized ingestion pipeline to AWS (ECS or EC2).

Integrate external sources (e.g., FIDE ratings, Kaggle archives).

Expand analytics layer: Redshift, dashboards via QuickSight or Metabase.

Fix Get Games from Users: Investigate and resolve the current issues with
fetching PGN data for specific Lichess user IDs, ensuring
functionality for future data ingestion.

