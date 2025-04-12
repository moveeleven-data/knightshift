-- tv_channel_games.sql

CREATE TABLE IF NOT EXISTS tv_channel_games (
    id VARCHAR PRIMARY KEY,
    event VARCHAR,
    site VARCHAR,
    date DATE,
    white VARCHAR,
    black VARCHAR,
    result VARCHAR,
    utc_date DATE,
    utc_time TIME,
    white_elo INTEGER,
    black_elo INTEGER,
    white_title VARCHAR,
    black_title VARCHAR,
    variant VARCHAR,
    time_control VARCHAR,
    eco VARCHAR,
    termination VARCHAR,
    moves TEXT,
    updated BOOLEAN DEFAULT false,
    url_valid BOOLEAN,
    opening TEXT,
    profile_updated BOOLEAN DEFAULT false,
    is_valid BOOLEAN DEFAULT true,
    validation_errors TEXT,
    raw_pgn JSONB
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_updated ON tv_channel_games(updated);
CREATE INDEX IF NOT EXISTS idx_white ON tv_channel_games(white);
CREATE INDEX IF NOT EXISTS idx_black ON tv_channel_games(black);
