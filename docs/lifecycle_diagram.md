# KnightShift Data Lifecycle Diagram (ASCII)

    ┌──────────────────────┐
    │  Lichess TV API      │
    └─────────┬────────────┘
              │ Pull PGN (Streaming)
              ▼
    ┌──────────────────────┐
    │ get_games_from_tv.py │
    └─────────┬────────────┘
              │ Parse PGN
              ▼
    ┌──────────────────────┐
    │ build_game_data()    │
    └─────────┬────────────┘
              │ Upsert to DB
              ▼
    ┌────────────────────────┐
    │ tv_channel_games Table │
    └─────────┬──────────────┘
              │ Clean + Validate
              ▼
    ┌───────────────────────────────┐
    │ validate_tv_channel_games.py  │
    └─────────┬─────────────────────┘
              │ Remove/clean rows
              ▼
    ┌──────────────────────────────┐
    │ backfill_user_profiles.py    │
    └─────────┬────────────────────┘
              │ Fetch user metadata
              ▼
    ┌──────────────────────────────┐
    │ lichess_users Table          │
    └──────────────────────────────┘
