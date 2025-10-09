# ==============================================================================
# pgn_parser.py  –  Utility for parsing PGN lines
#
# Parses PGN headers and moves from raw bytes (e.g., Lichess TV stream).
# Returns a dict of headers (lowercased keys) plus a `moves` entry.
# ==============================================================================

from __future__ import annotations
from typing import List, Dict


def parse_pgn_lines(pgn_lines: List[bytes]) -> Dict[str, str]:
    """
    Parse PGN lines into headers + move string.

    Parameters
    ----------
    pgn_lines : List[bytes]
        Raw PGN lines (bytes), typically from a Lichess TV stream.

    Returns
    -------
    Dict[str, str]
        Dictionary of PGN headers (lowercased keys),
        with a `"moves"` key containing the full moves string.
    """
    game_data: Dict[str, str] = {}
    moves: list[str] = []

    for line in pgn_lines:
        decoded_line = line.decode("utf-8").strip()

        if decoded_line.startswith("["):
            # Example: [Result "1-0"] → key='Result', value='1-0'
            key, value = decoded_line[1:-1].split(" ", 1)
            game_data[key.lower()] = value.strip('"')
        else:
            # Remaining lines are move text (e.g., "1. e4 e5 2. Nf3 Nc6 …")
            if decoded_line:
                moves.append(decoded_line)

    game_data["moves"] = " ".join(moves)
    return game_data
