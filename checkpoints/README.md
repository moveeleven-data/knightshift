# KnightShift Checkpoints

This folder contains frozen, self-contained snapshots of the KnightShift pipeline captured at key milestones. Each checkpoint is fully runnable and isolated from the main development environment, allowing for safe testing, historical reference, and demos without affecting the evolving core project.

---

## Current Checkpoints

### `knightshift_foundation/`  
**Date:** May 4, 2025  
**Summary:**  
The foundational working version of the KnightShift pipeline. Includes a full three-stage batch pipeline (ingestion → cleaning → enrichment) orchestrated by Airflow, an isolated PostgreSQL database, and a Prometheus + Grafana observability layer emitting simulated metrics. All services are containerized and decoupled from the main project.

- DAG runs every 2 hours and completes in under 2 minutes
- Fully isolated `.env`, volumes, and database
- Restored Grafana dashboard included
- Airflow at `localhost:8081`, Prometheus at `9090`, Grafana at `3000`

> This snapshot preserves the first production-style version of KnightShift before future expansions like Kafka, streaming data, and cloud deployment.

---

More checkpoints will be added as the project evolves.
