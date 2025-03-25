# 📊 Database Schema – KnightShift

A complete reference for the PostgreSQL schema used in the KnightShift data
pipeline. Includes column definitions, data types, nullability, default values,
primary keys, and indexes.

---

## 📁 tv_channel_games  

**Used by:** `get_games_from_tv.py`  
**Description:** Stores live-streamed games from Lichess TV channels.  

**Primary Key:** `id`  
**Indexes:** `tv_channel_games_pkey`, `tv_channel_games_updated_idx`  

| Column Name   | Data Type                 | Nullable | Default | Notes                        |
|---------------|---------------------------|----------|---------|------------------------------|
| id            | character varying         | NO       | NULL    | Unique game ID               |
| event         | character varying         | YES      | NULL    | Tournament or event name     |
| site          | character varying         | YES      | NULL    | Lichess game URL             |
| date          | date                      | YES      | NULL    | Game date                    |
| white         | character varying         | YES      | NULL    | White player username        |
| black         | character varying         | YES      | NULL    | Black player username        |
| result        | character varying         | YES      | NULL    | Game result (e.g., 1-0)      |
| utc_date      | date                      | YES      | NULL    | UTC game date                |
| utc_time      | time without time zone    | YES      | NULL    | UTC game time                |
| white_elo     | integer                   | YES      | NULL    | White player ELO             |
| black_elo     | integer                   | YES      | NULL    | Black player ELO             |
| white_title   | character varying         | YES      | NULL    | Title (e.g., GM)             |
| black_title   | character varying         | YES      | NULL    | Title (e.g., IM)             |
| variant       | character varying         | YES      | NULL    | Game variant (e.g., blitz)   |
| time_control  | character varying         | YES      | NULL    | Clock format                 |
| eco           | character varying         | YES      | NULL    | Opening classification       |
| termination   | character varying         | YES      | NULL    | Game termination type        |
| moves         | text                      | YES      | NULL    | PGN move sequence            |
| updated       | boolean                   | YES      | false   | Row enrichment status        |
| url_valid     | boolean                   | YES      | NULL    | Whether URL is valid         |
| opening       | text                      | YES      | NULL    | Opening name                 |
|profile_updated| boolean                   | YES      | false   | Whether we got info on player|

---

## 📁 chess_games  

**Used by:** `get_games_from_users.py`  
**Description:** Stores historical or user-specific games via Lichess API.  

**Primary Key:** `id`  
**Indexes:** `chess_games_pkey`  

| Column Name       | Data Type        | Nullable | Default | Notes                          |
|-------------------|------------------|----------|---------|--------------------------------|
| id                | character varying| NO       | NULL    | Unique game ID                 |
| rated             | boolean          | YES      | NULL    | Whether the game was rated     |
| variant           | character varying| YES      | NULL    | Game variant                   |
| speed             | character varying| YES      | NULL    | Game speed (e.g., blitz)       |
| perf              | character varying| YES      | NULL    | Performance category           |
| created_at        | bigint           | YES      | NULL    | Epoch timestamp                |
| status            | integer          | YES      | NULL    | Game status code               |
| status_name       | character varying| YES      | NULL    | Human-readable status          |
| clock_initial     | integer          | YES      | NULL    | Initial clock time (seconds)   |
| clock_increment   | integer          | YES      | NULL    | Time increment per move        |
| clock_total_time  | integer          | YES      | NULL    | Total time (initial + inc.)    |
| white_user_id     | character varying| YES      | NULL    | White player's ID              |
| white_rating      | integer          | YES      | NULL    | White player's rating          |
| black_user_id     | character varying| YES      | NULL    | Black player's ID              |
| black_rating      | integer          | YES      | NULL    | Black player's rating          |

---

## 🔑 Primary Keys

| Table            | Primary Key Column | Constraint Name        |
|------------------|--------------------|------------------------|
| tv_channel_games | id                 | tv_channel_games_pkey  |
| chess_games      | id                 | chess_games_pkey       |

---

## 📌 Indexes

| Table            | Index Name                  | Definition                                 |
|------------------|-----------------------------|--------------------------------------------|
| tv_channel_games | tv_channel_games_pkey       | PRIMARY KEY USING btree (id)               |
| tv_channel_games | tv_channel_games_updated_idx| INDEX ON updated (manual, recommended)     |
| chess_games      | chess_games_pkey            | PRIMARY KEY USING btree (id)               |

> 📝 *Note: `tv_channel_games_updated_idx` is a manual index to improve
performance of update scripts filtering by `updated = false`.*
