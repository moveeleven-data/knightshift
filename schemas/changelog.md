# 📜 Schema Changelog – KnightShift

Tracks structural changes to database tables (DDL) that impact table creation, evolution, or usage.

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
