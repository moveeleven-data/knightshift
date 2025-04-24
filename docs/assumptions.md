# KnightShift – Assumptions, Risks, and Failure Handling

This document outlines key architectural assumptions, known failure points, and how the KnightShift pipeline currently handles (or plans to handle) them.

---

## Current Assumptions

### Data Input
- **Lichess TV API is publicly available** and serves PGN data without authentication beyond a Bearer token.
- **Each PGN block is complete and ends after a move line** (e.g., starts with headers, ends with a `1. e4` move line).
- **Player usernames in each PGN are accurate and stable**, allowing reliable enrichment via the user profile API.

### System Environment
- **Pipeline runs in either local or Dockerized mode**, using `.env.local` or `.env.docker` respectively.
- **Postgres database is containerized** via Docker Compose, accessible via:
  - `localhost:55432` from local scripts
  - `db` (Docker hostname) from other Docker containers

### Schema and Data Model
- **Two key tables exist**: `tv_channel_games` (games) and `lichess_users` (player metadata).
- **Schema changes are version-controlled** under `/schemas/` and auto-initialized via Docker volumes.

---

## Known Failure Points + Current Mitigations

| Failure Scenario                            | Current Behavior / Handling                                    | Planned Improvements                         |
|---------------------------------------------|----------------------------------------------------------------|-----------------------------------------------|
| API returns status `429` (rate limit)       | Script logs error and exits immediately                        | N/A               |
| API returns `500` or other transient errors | Script retries up to 3x with sleep between attempts            | Make retry policy configurable                |
| Invalid or incomplete PGN data              | Validation step deletes row and logs reason                    | Consider archiving invalid rows to S3         |
| Postgres container crashes mid-run          | Script raises exception and logs crash. Added DB health checks (via Dockerfile)         |
| Container cannot connect to DB              | Logs failure, retries on restart (when using Docker Compose)   | Improve resilience with smarter reconnect     |
| Lichess profile data is malformed/missing   | Skipped, logged as warning                                     | Cache failures to avoid re-hitting bad users  |
| User already exists in `lichess_users`      | Skips insert, only updates `tv_channel_games.profile_updated`  | May add optional upsert with merge later      |
| If a script is misconfigured (e.g. missing .env values or typos in code)         | The pipeline logs the error        | Add automatic code checks ("static linters") to catch issues before the code runs!     |

---

## Human Error Assumptions

- Secrets are stored securely in AWS Secrets Manager, and `.env.local` is not committed to Git.
- Use the RUNNING_IN_DOCKER=true flag to switch DB host logic (localhost vs. db)
- Use `docker compose down -v` carefully, as it **permanently deletes Postgres data** unless backed up.

---

## Logging as a Diagnostic Tool

- All ingestion, cleaning, and enrichment logs are written to `logs/pipeline.log`.
- Each script has its own logger via `logging_utils.py`.
- Docker logs are visible via `docker compose logs pipeline` or `docker logs`.

---

## Future Resilience Goals (Phase 2+)

- Graceful recovery from DB or API downtime
- Retry queues or stream buffering (i.e. Kafka)
- Archival of failed/invalid records
- Prometheus + Grafana for health monitoring
- Alerting if ingestion drops to zero

---

