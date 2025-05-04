# KnightShift Checkpoints

This folder contains frozen, self-contained snapshots of the KnightShift pipeline captured at key milestones. Each checkpoint is fully runnable and isolated from the main development environment, allowing for safe testing, historical reference, and demo purposes without risk of breaking the evolving core project.

---

## Current Checkpoints

### `knightshift_foundation/`  
**Date:** May 4, 2025  
**Description:**  
This is the first major checkpoint and represents the foundational working version of the KnightShift pipeline. It includes the full DAG-based pipeline (ingestion → cleaning → enrichment) orchestrated via Airflow, a PostgreSQL database, and a Prometheus + Grafana observability stack with simulated metrics. All services are containerized and fully decoupled from the main project. Airflow runs on `localhost:8081`, Prometheus on `localhost:9090`, and Grafana on `localhost:3000`, with a custom dashboard in place. This snapshot preserves the working system as it existed at a major milestone before future expansions such as Kafka, streaming data, and real-time metrics.

---

More checkpoints will be added as the project evolves.
