📈 Project Progress – KnightShift

A running log of major development milestones, current state, and future plans for the KnightShift data pipeline.

------------------------------------

🗓 December 2024

Initial ingestion system established:

Get Games from Users:
Fetches historical PGN data for specific Lichess user IDs and inserts it into the chess_games table.

Get Games from TV:
Continuously streams games from all Lichess TV channels (e.g. blitz, rapid, horde) and inserts records into the tv_channel_games table. Each row includes metadata such as player names, ELO ratings, time controls, results, and PGN move text.

Update All Games:
Enriches previously ingested records. Uses a Boolean updated column to selectively update stale or partial rows, optimizing for performance via indexed queries.

------------------------------------

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

------------------------------------

🔭 Near-Term Plans (Q2 2025)

 Redirect standard output to a persistent log file (e.g., pipeline.log) via run.sh.

 Dockerize the entire application (handling .env, credentials, and PostgreSQL integration).

 Set up local automation via cron (Linux/WSL) or Task Scheduler (Windows).

⚙️ Mid-Term Goals (Spring 2025)

 Validate ingested game records with basic data quality checks (e.g., ELO ranges, valid PGN structure).

 Investigate and resolve source of invalid game IDs.

 Partition tv_channel_games table by ingestion date for scalability.

 Add monitoring utilities to surface ingestion stats and error rates.

🚀 Long-Term Vision (Summer 2025)

 Stage raw data in AWS S3 and archive invalid records.

 Deploy containerized ingestion pipeline to AWS (ECS or EC2).

 Integrate external sources (e.g., FIDE ratings, Kaggle archives).

 Expand analytics layer: Redshift, dashboards via QuickSight or Metabase.

