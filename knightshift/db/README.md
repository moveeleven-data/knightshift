### src/db

This module contains reusable, low-level database logic for the KnightShift pipeline.

#### `game_upsert.py`

- `build_game_data(game_dict)`  
  Converts a parsed PGN dictionary into a structured row for the `tv_channel_games` table.


- `upsert_game(session, table, game_data)`  
  Performs an UPSERT (insert or update) for a single game record using SQLAlchemy Core.


- `parse_rating(value)`  
  Helper function to safely convert string ratings to integers.