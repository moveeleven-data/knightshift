# Observability Sim – KnightShift (Experimental)

created a fully self-contained snapshot of the KnightShift project inside experiments/observability_sim, capturing the entire pipeline, Airflow DAGs, and a Prometheus + Grafana observability layer with simulated metrics. I copied over the knightshift/ and airflow/ folders, brought in the main pipeline’s docker-compose.yml as docker-compose.pipeline.yml, and updated all volume paths to be local. I also renamed the main .env to .env.pipeline for clarity. This snapshot runs its own isolated Postgres instance with a separate volume (pg_data), and I confirmed that it doesn’t share data with the main project database. Airflow is available at localhost:8081, Grafana at localhost:3000, and Prometheus at localhost:9090. This snapshot is frozen at a major working checkpoint and won’t evolve with the rest of the project—it's here for testing, demos, and historical comparison.

## May 4, 2025

# Observability Sim – KnightShift (Snapshot)

This folder (root/experiments/observability_sim) contains a standalone Prometheus + Grafana simulation environment 
used to test and demonstrate observability concepts **without affecting the core KnightShift pipeline**. It runs a fake ingestion service (`prometheus_metrics.py`) that emits synthetic metrics to port `8000`, which Prometheus scrapes and Grafana visualizes. The setup is designed for local, exploratory use and is decoupled from DAG execution, live data, or batch orchestration. This allows for fast prototyping of metrics and dashboards without interfering with production containers.

As of May 4, 2025, I expanded this environment into a **fully self-contained snapshot of the entire KnightShift 
pipeline**, frozen at a major working checkpoint. I copied over the complete `knightshift/` and `airflow/` folders, 
brought in the production `docker-compose.yml` as `docker-compose.pipeline.yml`, and updated all volume paths to be 
local. I also renamed the main `.env` to `.env.pipeline` to avoid conflicts. The snapshot now runs its own isolated 
Postgres instance with a separate volume (`pg_data`), and I confirmed it does **not** share data with the main pipeline. It includes the real DAG, scripts, schema init files, and a working batch pipeline, but all decoupled from the production environment. Airflow runs on [localhost:8081](http://localhost:8081) (`admin` / `admin`), Prometheus on [localhost:9090](http://localhost:9090), and Grafana on [localhost:3000](http://localhost:3000) (`admin` / `admin`), with a custom dashboard pre-configured to show simulated ingestion metrics.

To run the full environment (including both the observability stack and the real pipeline), navigate to this folder 
and execute: docker compose up
