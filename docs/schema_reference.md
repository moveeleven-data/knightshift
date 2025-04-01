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
|is_valid       | boolean                   | YES      | true    | whether row is valid         |
|validation_errors| text                    | YES      | false   | info about validation errors |


## 🔑 Primary Keys

| Table            | Primary Key Column | Constraint Name         |
|------------------|--------------------|--------------------------|
| tv_channel_games | id                 | tv_channel_games_pkey    |

---

## 📌 Indexes

| Table            | Index Name           | Definition                                 |
|------------------|----------------------|--------------------------------------------|
| tv_channel_games | tv_channel_games_pkey| PRIMARY KEY USING btree (id)               |
| tv_channel_games | idx_updated          | INDEX ON updated                           |

> 📝 *Note: `idx_updated` is used to efficiently filter rows where `updated = false`, which is common during enrichment and synchronization passes.*

---

## 📁 lichess_users

**Used by:** `add_users.py`  
**Description:** Stores enriched user profile data fetched from the Lichess API.

**Primary Key:** `id`  
**Indexes:** `lichess_users_pkey`

| Column Name         | Data Type         | Nullable | Default | Notes                                      |
|---------------------|-------------------|----------|---------|--------------------------------------------|
| id                  | character varying | NO       | NULL    | Unique Lichess user ID                     |
| username            | character varying | YES      | NULL    | Public username                            |
| title               | character varying | YES      | NULL    | Player title (e.g., GM, IM, FM)            |
| url                 | text              | YES      | NULL    | Full profile URL                           |
| real_name           | text              | YES      | NULL    | Real name from user profile                |
| location            | text              | YES      | NULL    | Country or city from profile               |
| bio                 | text              | YES      | NULL    | Bio text from user profile                 |
| fide_rating         | integer           | YES      | NULL    | FIDE rating (if available)                 |
| uscf_rating         | integer           | YES      | NULL    | USCF rating (if available)                 |
| bullet_rating       | integer           | YES      | NULL    | Rating for bullet games                    |
| blitz_rating        | integer           | YES      | NULL    | Rating for blitz games                     |
| classical_rating    | integer           | YES      | NULL    | Rating for classical games                 |
| rapid_rating        | integer           | YES      | NULL    | Rating for rapid games                     |
| chess960_rating     | integer           | YES      | NULL    | Rating for Chess960                        |
| ultra_bullet_rating | integer           | YES      | NULL    | Rating for ultra-bullet games              |
| country_code        | character varying | YES      | NULL    | Country flag (ISO code)                    |
| created_at          | bigint            | YES      | NULL    | Account creation timestamp (epoch ms)      |
| seen_at             | bigint            | YES      | NULL    | Last seen timestamp (epoch ms)             |
| playtime_total      | integer           | YES      | NULL    | Total minutes played                       |
| playtime_tv         | integer           | YES      | NULL    | Minutes played on TV channel               |
| games_all           | integer           | YES      | NULL    | Total games played                         |
| games_rated         | integer           | YES      | NULL    | Rated games count                          |
| games_win           | integer           | YES      | NULL    | Number of wins                             |
| games_loss          | integer           | YES      | NULL    | Number of losses                           |
| games_draw          | integer           | YES      | NULL    | Number of draws                            |
| patron              | boolean           | YES      | NULL    | Whether the user is a Lichess patron       |
| streaming           | boolean           | YES      | NULL    | Whether the user is marked as streaming    |

## 🔑 Primary Keys

| Table         | Primary Key Column | Constraint Name       |
|---------------|--------------------|------------------------|
| lichess_users | id                 | lichess_users_pkey     |

---

## 📌 Indexes

| Table         | Index Name          | Definition                          |
|---------------|---------------------|-------------------------------------|
| lichess_users | lichess_users_pkey  | PRIMARY KEY USING btree (id)        |

> 📝 *Note: The `id` column in `lichess_users` is the unique Lichess user ID and serves as the primary identifier for joining with game tables or external data.*