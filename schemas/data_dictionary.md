Data Dictionary: tv_channel_games Table

This table stores chess game metadata ingested from the Lichess TV stream. It is validated and cleaned via the validate_tv_channel_games.py script.

id
Type: VARCHAR (Primary Key)
Description: Unique identifier for the game.
Example: "abc123"

event
Type: VARCHAR
Description: Description of the event or arena (e.g., "Rated Bullet Game").

site
Type: VARCHAR
Description: URL to the Lichess game.

date
Type: DATE
Description: Local date the game occurred.

white, black
Type: VARCHAR
Description: Usernames of the players.
Validation Rule: Cannot be empty or null. Missing values result in row deletion.

result
Type: VARCHAR
Description: Final outcome of the game.
Valid Values: "1-0", "0-1", "1/2-1/2"
Validation Rule: Invalid results trigger deletion with note "Invalid result: <value>".

utc_date, utc_time
Type: DATE, TIME
Description: UTC timestamp of game start (split into date and time).

white_elo, black_elo
Type: INTEGER
Description: Elo rating of each player at game time.
Nullable: Yes (e.g. unrated or anonymous users)
Cleaning: Strings parsed to int. Invalids set to NULL, with validation notes like "Invalid white_elo".

white_title, black_title
Type: VARCHAR
Description: Official chess titles like "GM", "FM", etc.

variant
Type: VARCHAR
Description: Lichess variant type (e.g., "Standard", "Atomic").

time_control
Type: VARCHAR
Description: Clock format for the game (e.g., "180+0" for 3-minute games).

eco
Type: VARCHAR
Description: ECO (Encyclopaedia of Chess Openings) code.
Cleaning: "?" is normalized to NULL with "Set ECO to NULL" in notes.

termination
Type: VARCHAR
Description: How the game concluded (e.g., "Normal", "Time forfeit").

moves
Type: TEXT
Description: Full move list in PGN notation.
Validation Rule: Required. Empty values result in row deletion.

is_validated
Type: BOOLEAN (Default: false)
Description: Whether the row has been processed and validated.
Cleaning Logic: Set to true if the row passed cleaning.

opening
Type: TEXT
Description: Human-readable opening name derived from moves/ECO.

profile_updated
Type: BOOLEAN (Default: false)
Description: Indicates if additional user profile enrichment has been completed.

ingested_at
Type: TIMESTAMP (Default: CURRENT_TIMESTAMP)
Description: When the row was ingested into the database.

validation_notes
Type: TEXT
Description: Explanation of any data quality or formatting issues.
Nullable: Yes. Will be null if the row was valid with no notes.

Indexes
idx_is_validated – speeds up filtering for rows pending validation
idx_white – for queries filtering by the white player
idx_black – for queries filtering by the black player