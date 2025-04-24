# KnightShift: Project Overview

KnightShift is a production-style chess data pipeline that streams live PGN
games from the Lichess TV API, parses and cleans the data, and stores validated
game records in PostgreSQL. The project is modular, secure, and built to
simulate real-world data engineering workflows.

## 🔄 Mapping to the Data Engineering Lifecycle

| Lifecycle Stage        | How KnightShift Implements It |
|------------------------|-------------------------------|
| **Generation**         | Pulls live PGN data from the Lichess TV API |
| **Storage**            | Uses Dockerized PostgreSQL with schema auto-init and persistent volumes |
| **Ingestion**          | Streamed via `get_games_from_tv.py`, processed and upserted with schema validation |
| **Transformation**     | PGNs are parsed, ELO values cleaned, invalid rows deleted (`validate_tv_channel_games.py`) |
| **Serving**            | Cleaned records are stored for future querying, analytics, or dashboarding |
| **Security / DataOps** | AWS Secrets Manager handles credentials; logging and modular scripts ensure maintainability |

## 🧠 Role Reflection (A→B Continuum)

According to FDE’s A→B model:
> A = software engineer building their first data system  
> B = data engineer building distributed, orchestrated, production-ready pipelines

I currently identify as a **strong A, bridging into early B**. I've:
- Built a real-time ingestion system
- Modularized my code and run orchestration
- Used Docker Compose and AWS Secrets Manager

I’m now working toward:
- Scheduling and orchestration (cron/Airflow)
- Schema evolution and transformations
- Observability, replication, and partitioning

## 🎯 Project Goals (Short-Term)

- Ingest real-time games from all Lichess TV channels
- Clean and validate PGN records with rating sanity checks
- Enrich data using the Lichess user API
- Simulate a production-grade ingestion system using secure secrets and Docker

## 🔭 Long-Term Vision

- Evolve KnightShift into **KnightshiftHQ**, a multi-source chess analytics platform
- Add streaming (Kafka), orchestration (Airflow), and monitoring (Prometheus + Grafana)
- Load enriched data into Redshift for BI dashboards via AWS QuickSight
