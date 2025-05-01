# src/utils/pgn_parser.py

"""
pgn_parser.py

Parse raw PGN (Portable Game Notation) lines from Lichess TV into structured dictionaries.

Each chess game is streamed as:
- a header section (metadata like players, ratings, etc.),
- and a moves section (the sequence of chess moves).

This module organizes that information into a clean dictionary ready for database insertion.

Note:
- This parser assumes each PGN header and move line arrives on its own line.
- If Lichess ever changes their formatting (e.g., no line breaks), this script would need updates.
"""

from typing import List, Dict  # Import type hinting tools: List and Dict.

# ────────────────────────────────────────────────────────────────────────


def parse_pgn_lines(pgn_lines: List[bytes]) -> Dict[str, str]:
    """
    Parse a list of PGN lines into structured game data.

    Args:
        pgn_lines (List[bytes]): List of raw PGN lines as bytes (b"...").

    Returns:
        Dict[str, str]: Dictionary containing parsed header fields and a single 'moves' string.
    """

    game_data = (
        {}
    )  # Dictionary to store parsed PGN header fields (e.g., 'white', 'black', etc.).
    moves = []  # List to accumulate all move lines.

    for line in pgn_lines:  # Loop through each raw PGN line.
        decoded_line = line.decode(
            "utf-8"
        ).strip()  # Decode bytes to text and remove surrounding whitespace.

        if decoded_line.startswith(
            "["
        ):  # If the line is a PGN header (e.g., [White "Carlsen"]):
            key, value = decoded_line[1:-1].split(" ", 1)
            # Remove the outer [ ] by slicing [1:-1], then split into key and value at the first space.

            game_data[key.lower()] = value.strip('"')
            # Lowercase the key and remove the quotes around the value, then store them.
            #
            # Quick flow:
            # [White "Carlsen"]
            # → After slicing: White "Carlsen"
            # → After splitting: key='White', value='"Carlsen"'
            # → After cleaning: 'white': 'Carlsen'

        else:  # Otherwise, it's part of the moves section (e.g., "1. e4 e5").
            moves.append(decoded_line)  # Add the whole move line to the moves list.

    game_data["moves"] = " ".join(moves)
    # Join all move lines together into one long string,
    # inserting exactly one space (" ") between full lines.
    # (Any spaces *inside* a move line are preserved — no extra spaces added.)
    #
    # Example:
    # Input list: ["1. e4 e5", "2. Nf3 Nc6"]
    # After join: "1. e4 e5 2. Nf3 Nc6"
    #
    # This final "moves" string is stored under the "moves" key in game_data.

    return game_data  # Return the full parsed game data: headers + moves.
