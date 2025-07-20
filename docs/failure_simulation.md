# 📉 Failure Simulation: Postgres Downtime During Ingestion

**Date:** 2025-04-15  
**Simulated Event:** Manual shutdown of the Postgres container while the `pipeline-1` container was ingesting real-time Lichess TV games.

---

## Behavior Observed

- Pipeline successfully ingested multiple `bullet` and `blitz` games.
- Upon manually stopping the Postgres container, the following behaviors were logged:
  - `ConnectionResetError: [Errno 104] Connection reset by peer`
  - `pg8000.exceptions.InterfaceError: network error`
  - `ProgrammingError: the database system is shutting down`
  - `Can't create a connection to host db and port 5432`
- Errors appeared consistently during upsert attempts across different game variants.
- The ingestion script did **not crash**, and continued trying to fetch and upsert games.
- The error logs were cleanly recorded to both console and `logs/pipeline.log`.

---

## What This Confirms

- Docker networking and service resolution (`db:5432`) is functioning as expected.
- The pipeline's database access layer gracefully handles mid-session shutdowns.
- SQLAlchemy and pg8000 exceptions are not only caught, but logged in human-readable formats.
- Logging setup is robust and timestamps help pinpoint failure moments.
- Pipeline continues running even with persistent DB errors, avoiding total failure.

---

## Next Steps (Improvements)

- Add retry + backoff strategy for `InterfaceError` or `57P03` shutdowns.
- Pause ingestion loop if DB unavailability is detected repeatedly.
- Optionally raise a specific alert (e.g., push to Slack or email) on repeated DB failures.
- Implement a health check wrapper that verifies DB connection before each batch insert.
- Consider using SQLAlchemy connection pool pre-ping settings to catch dead sockets.