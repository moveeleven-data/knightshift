-- Add tm_validated: timestamp to mark data cleaning completion
ALTER TABLE tv_channel_games
ADD COLUMN IF NOT EXISTS tm_validated TIMESTAMP DEFAULT NULL;

-- Drop obsolete columns from early drafts
ALTER TABLE tv_channel_games DROP COLUMN IF EXISTS is_valid;
ALTER TABLE tv_channel_games DROP COLUMN IF EXISTS validation_errors;
ALTER TABLE tv_channel_games DROP COLUMN IF EXISTS url_valid;
