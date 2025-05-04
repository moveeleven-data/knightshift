# 🗂️ Schema Mappings – KnightShift

This document maps legacy column names to the new standardized naming convention using the prefix system (`id_`, `val_`, `dt_`, `tm_`, `ind_`, etc.).

---

## tv_channel_games

| Old Name         | New Name              | Notes                              |
|------------------|-----------------------|------------------------------------|
| id               | id_game               | Unique game identifier             |
| event            | val_event_name        | Name of event or arena             |
| site             | val_site_url          | URL of game page                   |
| date             | dt_game               | Local calendar date                |
| white            | id_user_white         | Username of white player           |
| black            | id_user_black         | Username of black player           |
| result           | val_result            | Game outcome ("1-0", etc.)         |
| utc_date         | dt_utc_game_date      | UTC date                           |
| utc_time         | tm_utc_game_start     | UTC time                           |
| white_elo        | val_elo_white         | Elo rating of white player         |
| black_elo        | val_elo_black         | Elo rating of black player         |
| white_title      | val_title_white       | Title of white player (GM, etc.)   |
| black_title      | val_title_black       | Title of black player              |
| variant          | val_variant           | Variant type (Standard, etc.)      |
| time_control     | val_time_control      | Clock format ("180+0")             |
| eco              | val_opening_eco_code  | ECO code                           |
| termination      | val_termination       | How the game ended                 |
| moves            | val_moves_pgn         | Full PGN move list                 |
| is_validated     | ind_validated         | Whether row passed validation      |
| opening          | val_opening_name      | Human-readable opening name        |
| profile_updated  | ind_profile_updated   | Profile enrichment flag            |
| ingested_at      | tm_ingested           | Ingestion timestamp                |
| validation_notes | val_validation_notes  | Notes about validation             |

---

## lichess_users

| Old Name             | New Name               | Notes                           |
|----------------------|------------------------|---------------------------------|
| id                   | id_user                | Primary key                     |
| username             | val_username           | Username string                 |
| title                | val_title              | Title string (GM, IM, etc.)     |
| url                  | val_profile_url        | Profile URL                     |
| real_name            | val_name               | Player's real name              |
| location             | val_location           | Player's self-reported location |
| bio                  | val_bio_text           | Profile bio                     |
| fide_rating          | val_fide_rating        | FIDE Elo rating                 |
| uscf_rating          | val_uscf_rating        | USCF Elo rating                 |
| bullet_rating        | val_rating_bullet      | Bullet rating                   |
| blitz_rating         | val_rating_blitz       | Blitz rating                    |
| classical_rating     | val_rating_classical   | Classical rating                |
| rapid_rating         | val_rating_rapid       | Rapid rating                    |
| chess960_rating      | val_rating_960         | Chess960 rating                 |
| ultra_bullet_rating  | val_rating_ultrabullet | Ultrabullet rating              |
| country_code         | val_country_code       | ISO country code                |
| created_at           | tm_created             | Epoch created time              |
| seen_at              | tm_last_seen           | Epoch last-seen time            |
| playtime_total       | amt_playtime_total     | Total minutes played            |
| playtime_tv          | amt_playtime_tv        | Total minutes on TV             |
| games_all            | n_games_all            | Total games played              |
| games_rated          | n_games_rated          | Rated games played              |
| games_win            | n_games_win            | Games won                       |
| games_loss           | n_games_loss           | Games lost                      |
| games_draw           | n_games_draw           | Games drawn                     |
| patron               | ind_is_patron          | Patron flag                     |
| streaming            | ind_is_streaming       | Streaming flag                  |
