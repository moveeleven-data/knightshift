# src/utils/pgn_parser.py

"""
pgn_parser.py

A simple utility module to parse PGN data from a list of bytes lines.
"""

from typing import List, Dict


def parse_pgn_lines(pgn_lines: List[bytes]) -> Dict[str, str]:
    """
    Parse a list of PGN lines from a Lichess TV stream (or any PGN source).

    Args:
        pgn_lines (List[bytes]): Raw lines of PGN data.

    Returns:
        Dict[str, str]: A dictionary of PGN headers (lowercased keys) with
                        a 'moves' key containing the concatenated move string.
    """
    game_data = {}
    moves = []
    for line in pgn_lines:
        decoded_line = line.decode("utf-8").strip()
        if decoded_line.startswith("["):
            # Example line: [Result "1-0"]
            # -> key = 'Result', value = '1-0'
            key, value = decoded_line[1:-1].split(" ", 1)
            game_data[key.lower()] = value.strip('"')
        else:
            # These lines will represent the moves (e.g., 1. e4 e5 2. ...)
            moves.append(decoded_line)

    game_data["moves"] = " ".join(moves)
    return game_data
