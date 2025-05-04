# Cleaning Module

This folder contains scripts for cleaning and validating ingested chess games.

### Scripts:
- `validate_tv_channel_games.py`: Drops invalid rows, sanitizes Elo ratings, and flags malformed URLs.

### Output:
- Validated and normalized records in `tv_channel_games`, with flags like `is_valid` and `updated`.
