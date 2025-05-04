# 📜 Schema Changelog – KnightShift

Tracks structural changes to database tables (DDL) that impact table creation, evolution, or usage.

---

## 2025-04-12

### Enabled auto-initialization of Postgres schema via Docker
- Mounted raw SQL files from `schemas/` into Postgres container using Docker volume.
- Files initialized:
  - `lichess_users.sql`
  - `tv_channel_games.sql`
- Ensures tables and indexes are created automatically on first container startup.
- Docker Compose volume: `./schemas:/docker-entrypoint-initdb.d`
- Future migrations can follow similar raw SQL or tool-based workflows (e.g. Flyway or Alembic).
- Added `ingested_at TIMESTAMP` column to `tv_channel_games` to track arrival time of each record.


---

## 2025-03-25

### Created `lichess_users` table
- Designed for user profile enrichment (ratings, bios, etc.).
- Mapped selected fields from Lichess API to typed Postgres columns.
- Primary key: `id`.

---

## 2025-03-30

### Added index on `tv_channel_games.updated`
- Index: `idx_updated`
- Enables fast filtering during enrichment/validation passes.

---

## 2025-03-31

### Extended `tv_channel_games` schema:
- New columns:
  - `profile_updated` (boolean, default false)
  - `is_valid` (boolean, default true)
  - `validation_errors` (text)
  - `url_valid` (boolean)
- Added logic in `validate_tv_channel_games.py` to drop invalid rows and mark cleaned ones with `updated=True`.

---
