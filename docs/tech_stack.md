# 🧱 KnightShift Tech Stack Overview

This document explains the key technologies used in the KnightShift pipeline and why they were chosen. It maps directly to Phase 1 of the project roadmap and provides clarity for future extensions.

---

## Python 3.10+
- **Why:** Easy to write, great libraries for data and APIs, widely used in data engineering.
- **Used For:** All scripts — ingestion, validation, enrichment, and orchestration (`main.py`).

---

## PostgreSQL (via Docker)
- **Why:** Reliable, mature relational database with strong SQL support.
- **Used For:** Storing structured chess game records and enriched user profiles.
- **Extras:** We use Docker volumes for persistence and SQL files for schema versioning.

---

## SQLAlchemy Core
- **Why:** Gives us low-level SQL control with Python readability.
- **Used For:** Creating engine connections, running queries, and building insert/update logic.

---

## AWS Secrets Manager
- **Why:** Keeps DB credentials secure and out of version control.
- **Used For:** Centralized DB secrets. Supports both local and Docker-based execution via `db_utils.py`.

---

## Requests Library
- **Why:** Lightweight HTTP library.
- **Used For:** Fetching PGN and user data from the Lichess API (TV endpoint + User endpoint).

---

## Docker + Docker Compose
- **Why:** Ensures consistent environments, simplifies local orchestration.
- **Used For:**
  - Spinning up Postgres and the pipeline together.
  - Mounting volumes (`pg_data`, `schemas/`, `logs/`).
  - Running scripts inside containers.

---

## dotenv (.env Files)
- **Why:** Easily switch between environments.
- **Used For:** `.env.local` for scripts, `.env.docker` for container-based runs.

---

## Logging
- **Why:** Debugging, observability, and error recovery.
- **Used For:** Every script uses `logging_utils.py` to output to both terminal and `logs/pipeline.log`.

---

## Testing (Pytest)
- **Why:** Catch bugs early, make refactors safer.
- **Used For:** Testing PGN parsing, DB utils, and validation logic.

---

## Folder Structure
| Folder | Purpose |
|--------|---------|
| `src/` | Core scripts: ingestion, cleaning, enrichment |
| `schemas/` | SQL schema files auto-loaded into Postgres |
| `config/` | Environment files (`.env.local`, `.env.docker`) |
| `logs/` | Captures logs from pipeline execution |
| `tests/` | Unit tests for core logic |
| `docs/` | Documentation + architecture notes |

---

## Why This Stack Works
- **Beginner-friendly but production-relevant.**
- **Extensible toward Airflow, Kubernetes, and cloud platforms.**
- **Secure, observable, and modular from the start.**

---

## Future Tech Stack Additions (Phase 2+)
| Tech | Role |
|------|------|
| Airflow | DAG-based orchestration for scheduling + monitoring |
| Great Expectations | Data validation framework |
| Redshift or ClickHouse | High-performance analytics/BI |
| Prometheus + Grafana | Metrics + dashboards |
| Kafka | Streaming ingestion |

---
