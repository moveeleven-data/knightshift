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
    is_validated BOOLEAN DEFAULT false,
    opening TEXT,
    profile_updated BOOLEAN DEFAULT false,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validation_notes TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_is_validated ON tv_channel_games(is_validated);
CREATE INDEX IF NOT EXISTS idx_white ON tv_channel_games(white);
CREATE INDEX IF NOT EXISTS idx_black ON tv_channel_games(black);
