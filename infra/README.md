### KnightShift Infrastructure Setup

The `infra/` folder contains infrastructure code to run KnightShift with
**Docker Compose**, orchestrating Postgres, Airflow, and the ingestion worker together.

---

### Prerequisites

- Docker + Docker Compose
- `.env` file in project root (copy from template)

---

### Running with Docker Compose

1. Ensure `.env` exists in the project root.
2. (Windows only) Fix line endings in `run.sh`:

```bash
dos2unix run.sh
```

3. Build and start all services:

```bash
docker compose up --build
```

This will:

- Spin up a local Postgres container

- Launch Airflow (Scheduler, Webserver, Worker)

- Register and schedule the KnightShift ingestion DAG

- Begin streaming games into Postgres

---

### Accessing Airflow

Once running, open http://localhost:8080:

- Username: admin

- Password: admin

---

### Secrets Detection

This repo uses detect-secrets to prevent committing sensitive data.

Known secrets are tracked in .secrets.baseline.

If secrets rotate or are removed, regenerate the baseline:

```bash
detect-secrets scan > .secrets.baseline
git add .secrets.baseline
git commit -m "update secrets baseline"
```

---

### Restoring Grafana Dashboard from Backup

If you’ve torn down the stack or lost your Grafana dashboard, restore it with:

```bash
/backups/grafana/grafana_backup_2025-05-03.tar.gz
```

### Steps

1. Stop containers:

```bash
docker compose down
```

2. Restore the Grafana data volume:

```bash
docker run --rm \
  -v compose_grafana_data:/volume \
  -v $(pwd)/backups/grafana:/backup \
  alpine \
  sh -c "rm -rf /volume/* && tar xzf /backup/grafana_backup_2025-05-03.tar.gz -C /volume"
```

3. Rebuild and launch:

```bash
docker compose up --build
```

---

### Notes

- Airflow DAGs are located in ../airflow/dags.

- Logs and metadata are persisted between runs unless volumes are cleared.