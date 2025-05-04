# Data Dictionary: `tv_channel_games` Table

This table stores cleaned chess game metadata ingested from the Lichess TV stream.  
It is validated via `validate_tv_channel_games.py`, which enforces data integrity before enrichment or analytics.

---

## Identifiers

| Column         | Type     | Description                                                  |
|----------------|----------|--------------------------------------------------------------|
| id_game        | VARCHAR  | Unique identifier for the game (primary key). Example: "abc123" |
| id_user_white  | VARCHAR  | Lichess ID of the white player. Required.                   |
| id_user_black  | VARCHAR  | Lichess ID of the black player. Required.                   |

---

## Game Metadata

| Column             | Type     | Description                                 |
|--------------------|----------|---------------------------------------------|
| val_event_name     | VARCHAR  | Name of the game event (e.g., "Rated Blitz Game"). |
| val_site_url       | VARCHAR  | Lichess game URL.                           |
| dt_game            | DATE     | Local calendar date of the game.            |
| dt_game_utc        | DATE     | UTC calendar date of the game.              |
| tm_game_utc        | TIME     | UTC start time of the game.                 |
| val_variant        | VARCHAR  | Lichess variant type (e.g., "Standard", "Atomic"). |
| val_time_control   | VARCHAR  | Time control (e.g., "180+0" for a 3-minute game). |
| val_termination    | VARCHAR  | How the game ended (e.g., "Normal", "Time forfeit"). |

---

## Player Ratings & Titles

| Column           | Type     | Description                                  |
|------------------|----------|----------------------------------------------|
| val_elo_white    | INTEGER  | White's Elo rating. Nullable if unrated.     |
| val_elo_black    | INTEGER  | Black's Elo rating. Nullable if unrated.     |
| val_title_white  | VARCHAR  | Chess title of the white player (e.g., GM).  |
| val_title_black  | VARCHAR  | Chess title of the black player.             |

---

## PGN & Opening Info

| Column                | Type   | Description                                                |
|-----------------------|--------|------------------------------------------------------------|
| val_moves_pgn         | TEXT   | PGN string representing all moves. Required.               |
| val_result            | VARCHAR| Final outcome: "1-0", "0-1", or "1/2-1/2". Invalid values cause deletion. |
| val_opening_eco_code  | VARCHAR| ECO code (e.g., "C20"). "?" is normalized to NULL.         |
| val_opening_name      | TEXT   | Human-readable name of the opening (if known).             |

---

## Timestamps & Flags

| Column               | Type      | Description                                               |
|----------------------|-----------|-----------------------------------------------------------|
| tm_ingested          | TIMESTAMP | When the row was inserted into the database. Defaults to CURRENT_TIMESTAMP. |
| tm_validated         | TIMESTAMP | Timestamp when validation was performed. Nullable.        |
| ind_validated        | BOOLEAN   | Whether the row passed validation. Default: FALSE.        |
| ind_profile_updated  | BOOLEAN   | Whether user profile enrichment has been completed. Default: FALSE. |
| val_validation_notes | TEXT      | Any cleaning actions or validation issues. NULL if fully valid. |

---

## Indexes

| Index Name        | Columns Indexed     | Purpose                                      |
|-------------------|---------------------|----------------------------------------------|
| idx_id_user_white | id_user_white       | Filters by white player (e.g., enrichment).  |
| idx_id_user_black | id_user_black       | Filters by black player.                     |
| idx_dt_game       | dt_game             | Enables time-range queries and analytics.    |
| idx_variant       | val_variant         | Supports filtering by chess variant.         |
| idx_is_validated  | ind_validated       | Speeds up validation filtering logic.        |

------------------------------------------------

## Data Dictionary: `lichess_users` Table

This table stores public profile metadata for Lichess users, enriched via API.

---

### Identifiers

| Column     | Type         | Description                              |
|------------|--------------|------------------------------------------|
| id_user    | VARCHAR(50)  | Unique Lichess user ID (primary key).    |

---

### User Profile Info

| Column            | Type         | Description                                      |
|-------------------|--------------|--------------------------------------------------|
| val_username      | VARCHAR(50)  | Lichess username (displayed name).              |
| val_title         | VARCHAR(10)  | Official chess title (e.g., GM, FM).            |
| val_url           | TEXT         | Profile URL on Lichess.                         |
| val_real_name     | TEXT         | User’s real name (if available).                |
| val_location      | TEXT         | User’s location (if provided).                  |
| val_bio           | TEXT         | User biography text.                            |
| val_country_code  | VARCHAR(20)  | Two-letter country code from profile flag.      |

---

### Ratings

| Column                   | Type     | Description                      |
|--------------------------|----------|----------------------------------|
| val_rating_fide          | INTEGER  | FIDE rating (optional).          |
| val_rating_uscf          | INTEGER  | USCF rating (optional).          |
| val_rating_bullet        | INTEGER  | Bullet rating.                   |
| val_rating_blitz         | INTEGER  | Blitz rating.                    |
| val_rating_classical     | INTEGER  | Classical rating.                |
| val_rating_rapid         | INTEGER  | Rapid rating.                    |
| val_rating_chess960      | INTEGER  | Chess960 variant rating.         |
| val_rating_ultra_bullet  | INTEGER  | UltraBullet rating.              |

---

### Timestamps

| Column      | Type   | Description                                |
|-------------|--------|--------------------------------------------|
| tm_created  | BIGINT | Epoch timestamp of account creation.       |
| tm_seen     | BIGINT | Epoch timestamp of last seen activity.     |

---

### Play Time

| Column            | Type    | Description                               |
|-------------------|---------|-------------------------------------------|
| n_playtime_total  | INTEGER | Total time played (in seconds).           |
| n_playtime_tv     | INTEGER | Time played on Lichess TV (in seconds).   |

---

### Game Counts

| Column         | Type    | Description                        |
|----------------|---------|------------------------------------|
| n_games_all    | INTEGER | Total number of games played.      |
| n_games_rated  | INTEGER | Number of rated games.             |
| n_games_win    | INTEGER | Games won.                         |
| n_games_loss   | INTEGER | Games lost.                        |
| n_games_draw   | INTEGER | Games drawn.                       |

---

### Flags

| Column         | Type    | Description                                 |
|----------------|---------|---------------------------------------------|
| ind_patron     | BOOLEAN | Whether the user is a Lichess patron.       |
| ind_streaming  | BOOLEAN | Whether the user has a linked stream.       |
