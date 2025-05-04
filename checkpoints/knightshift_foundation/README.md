# SNAPSHOT: May 4, 2025 – KnightShift Major Checkpoint

> This folder is a **frozen, self-contained snapshot** of the KnightShift pipeline at a major working state.  
> It includes its own DAGs, database, scripts, and observability stack. **DO NOT edit or refactor this** — it is preserved for testing, demos, and historical reference.

---

## `knightshift_foundation`

This is a complete snapshot of the KnightShift project, located at `checkpoints/knightshift_foundation`. It captures the full working pipeline along with a Prometheus + Grafana observability layer.

- Includes: `knightshift/`, `airflow/`, and a copy of the main `docker-compose.yml` (renamed to `docker-compose.pipeline.yml`)
- All volume paths are localized
- Uses a renamed `.env.pipeline` to prevent environment conflicts
- Runs a dedicated PostgreSQL instance with a separate volume (`pg_data`)
- Confirmed: this snapshot does **not** share data with the main project

Airflow (DAG-based orchestration), Prometheus (metrics scraping), and Grafana (dashboarding) are all pre-integrated and isolated. The Airflow web UI is accessible at [localhost:8081](http://localhost:8081) and Grafana at [localhost:3000](http://localhost:3000), both using default credentials (`admin` / `admin`). Prometheus runs at [localhost:9090](http://localhost:9090).

> A previous Grafana dashboard backup was successfully restored into this environment. You’ll find all metrics pre-wired and visualized as they existed at the time of the snapshot.

---

## Observability Simulation

This environment includes a fake ingestion service (`prometheus_metrics.py`) that emits synthetic metrics to port `8000`. Prometheus scrapes these metrics and Grafana displays them through a pre-configured dashboard. This setup is fully decoupled from DAG execution, live data, and batch orchestration — ideal for local experimentation and dashboard prototyping.

---

## ▶How to Run

From inside this folder, launch the full environment (pipeline + observability) with:

```bash
docker compose up --build
