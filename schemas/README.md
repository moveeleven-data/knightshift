# KnightShift Database Schemas

This folder contains raw SQL definitions for initializing and versioning key
database tables used in the KnightShift data pipeline.

# Schemas Directory

- `init/`: Base SQL schemas auto-loaded at container startup.
- `migrations/`: Versioned schema evolution files (manual or tool-driven).
- `CHANGELOG.md`: History of all structural changes.
- `schema_mappings.md`: Maps old column names to new.
- `data_dictionary.md`: Field-by-field definitions for core tables.

## Purpose

These schema files ensure:
- Reliable, version-controlled initialization of the database
- Easy portability across local, Docker, and cloud environments
- Clear visibility into table structure and evolution over time

## Files

- `tv_channel_games.sql`  
  Defines the structure of ingested chess game data from Lichess TV,
  including PGN fields, metadata, and validation flags.

- `lichess_users.sql`  
  Defines the structure for enriched user profiles pulled from the Lichess API,
  including ratings, titles, and activity data.

## Usage

These files are automatically loaded when the Postgres container is first
initialized via Docker Compose.

If changes are made to the schema:
1. Update the SQL file in this directory
2. Add a description of the change to the changelog (`changelog.md`)
3. Rebuild the containers with `docker compose down -v && docker compose up`