# SNAPSHOT: May 4, 2025 – KnightShift Major Checkpoint

> This folder is a **frozen, self-contained snapshot** of the KnightShift pipeline at a major working state.  
> It includes its own DAGs, database, scripts, and observability stack. **DO NOT edit or refactor this** — it is preserved for testing, demos, and historical reference.

---

## `knightshift_foundation`

This is a complete snapshot of the KnightShift project, located at `checkpoints/knightshift_foundation`. It captures the full working pipeline along with a Prometheus + Grafana observability layer.

All services are containerized and decoupled from the main project. The snapshot includes:
- The complete `knightshift/` codebase (ingestion, cleaning, enrichment, utils, tests)
- The `airflow/` folder containing the working DAGs
- A copy of the main `docker-compose.yml`, renamed to `docker-compose.pipeline.yml`
- A renamed `.env.pipeline` file to avoid environment conflicts
- Localized volume paths and mounts
- An isolated PostgreSQL instance with a separate volume (`pg_data`)
- Full Prometheus + Grafana observability layer with simulated metrics

Airflow (DAG-based orchestration), Prometheus (metrics scraping), and Grafana (dashboarding) are all pre-integrated and isolated.

> A previous Grafana dashboard backup was successfully restored into this environment. You’ll find all metrics pre-wired and visualized as they existed at the time of the snapshot.

---

## Pipeline Architecture

This snapshot represents the foundational working version of the KnightShift data pipeline. It includes a complete three-stage DAG that runs every 2 hours and completes in under 2 minutes per cycle. Each task is isolated, reproducible, and unit-tested, built for modular execution via Airflow.

- **Ingestion** (`get_games_from_tv.py`)  
  Streams live chess games from Lichess TV, parses PGNs using `parse_pgn_lines`, and upserts them into the `tv_channel_games` table. The script differentiates between new and existing games via conditional INSERT/UPDATE logic and is configurable by time limit or max game count.

- **Cleaning** (`validate_tv_channel_games.py`)  
  Normalizes and validates records in `tv_channel_games`, fills missing or invalid fields, and updates validation status. Also patches incomplete records in `lichess_users`. Includes rollback protection, logging, and configurable throttling for safe bulk processing.

- **Enrichment** (`backfill_user_profiles.py`)  
  Identifies users without profiles and pulls their public data from the Lichess API. Inserts into `lichess_users` and flags related games as `profile_updated = TRUE`. Typically completes in ~5 seconds with built-in rate-limit protection.

---

## Observability Simulation

This environment includes a fake ingestion service (`prometheus_metrics.py`) that emits synthetic metrics to port `8000`. Prometheus scrapes these metrics and Grafana displays them through a pre-configured dashboard. This setup is fully decoupled from DAG execution, live data, and batch orchestration — ideal for local experimentation and dashboard prototyping.

- **Prometheus** collects synthetic metrics from a fake ingestion script (`prometheus_metrics.py`) exposed on port `8000`.
- **Grafana** visualizes these metrics on a custom dashboard.
- **Airflow UI** runs at [`localhost:8081`](http://localhost:8081)
- **Prometheus** runs at [`localhost:9090`](http://localhost:9090)
- **Grafana** runs at [`localhost:3000`](http://localhost:3000) (`admin` / `admin`)

---

## How to Run

From inside this folder, launch the full environment (pipeline + observability) with:

docker compose up --build
