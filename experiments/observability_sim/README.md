# Observability Sim – KnightShift (Experimental)

## May 4, 2025

This folder contains a standalone Prometheus + Grafana simulation environment used to test and demonstrate observability concepts **without affecting the core KnightShift pipeline**. It runs a fake ingestion service (`prometheus_metrics.py`) that emits synthetic metrics to port `8000`, which Prometheus scrapes and Grafana visualizes. The setup is designed for local, exploratory use and is decoupled from DAG execution, live data, or batch orchestration. This allows you to prototype metrics and dashboard logic without interfering with production containers.

Today’s changes: extracted Prometheus and Grafana logic from the main KnightShift pipeline, relocated all related files into `experiments/observability_sim/`, and assigned unique ports to resolve conflicts with the main pipeline. A standalone Docker Compose file now handles the fake pipeline and observability stack, which can run alongside the production containers. The simulated pipeline uses the same schema and database but is decoupled at the service level. Run with `docker compose up` from within the `observability_sim` folder. Prometheus is accessible at [localhost:9090](http://localhost:9090) and Grafana at [localhost:3000](http://localhost:3000); a custom Grafana dashboard was created to visualize simulated ingestion metrics.
