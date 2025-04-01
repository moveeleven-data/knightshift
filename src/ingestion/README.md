# Ingestion Module

This folder contains scripts that stream live chess games from the Lichess TV API.

### Scripts:
- `get_games_from_tv.py`: Streams and parses PGN data, then upserts games into PostgreSQL.

### Output:
- Raw but structured game records are written to the `tv_channel_games` table.