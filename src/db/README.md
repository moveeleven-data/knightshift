# 📦 src/db

This module contains reusable, low-level database logic for the KnightShift pipeline.

## What’s Inside

### `game_upsert.py`
- `build_game_data(game_dict)`  
  Converts a parsed PGN dictionary into a structured row for the `tv_channel_games` table.

- `upsert_game(session, table, game_data)`  
  Performs an UPSERT (insert or update) for a single game record using SQLAlchemy Core.

- `parse_rating(value)`  
  Helper function to safely convert string ratings to integers.

## Why This Exists

- **Decoupling logic** from ingestion scripts makes testing easier and cleaner.
- Keeps SQLAlchemy operations centralized, improving maintainability and reuse across the project.
- Prepares KnightShift for future modularity (e.g., moving from Postgres to Redshift, or adding bulk operations).

## Usage Example

```python
from src.db.game_upsert import build_game_data, upsert_game

game_data = build_game_data(parsed_game)
was_updated = upsert_game(session, tv_channel_games_table, game_data)
