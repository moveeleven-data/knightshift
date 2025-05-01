-- tv_channel_games.sql

CREATE TABLE IF NOT EXISTS tv_channel_games (
    id_game VARCHAR PRIMARY KEY,
    val_event_name VARCHAR,
    val_site_url VARCHAR,
    dt_game DATE,
    id_user_white VARCHAR,
    id_user_black VARCHAR,
    val_result VARCHAR,
    dt_game_utc DATE,
    tm_game_utc TIME,
    val_elo_white INTEGER,
    val_elo_black INTEGER,
    val_title_white VARCHAR,
    val_title_black VARCHAR,
    val_variant VARCHAR,
    val_time_control VARCHAR,
    val_opening_eco_code VARCHAR,
    val_termination VARCHAR,
    val_moves_pgn TEXT,
    val_opening_name TEXT,
    tm_ingested TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tm_validated TIMESTAMP,
    ind_validated BOOLEAN DEFAULT FALSE,
    val_validation_notes TEXT,
    ind_profile_updated BOOLEAN DEFAULT FALSE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_id_user_white ON tv_channel_games(id_user_white);
CREATE INDEX IF NOT EXISTS idx_id_user_black ON tv_channel_games(id_user_black);
CREATE INDEX IF NOT EXISTS idx_dt_game ON tv_channel_games(dt_game);
CREATE INDEX IF NOT EXISTS idx_variant ON tv_channel_games(val_variant);
CREATE INDEX IF NOT EXISTS idx_is_validated ON tv_channel_games(ind_validated);
