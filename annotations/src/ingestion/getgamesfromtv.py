#!/usr/bin/env python3

# ───────────────────────────────────────────────────────────────
# Shebang: why it matters
# ───────────────────────────────────────────────────────────────
# • A "shebang" tells the OS **which interpreter** to use when running this file directly.
# • Here, it says: "Use Python 3."
#
# When you need it:
# -----------------
# → Typing manually:
#       python3 get_games_from_tv.py
#   (No shebang needed — you specify Python yourself.)
#
# → Running directly:
#       ./get_games_from_tv.py
#   (No "python3" in front — OS must figure it out.)
#   Without a shebang, this will fail ("unknown interpreter" or "permission denied").

# Why it’s required here:
# ------------------------
# • KnightShift scripts are run automatically (Docker, Airflow, cron).
# • Those systems expect self-contained, executable scripts — they **don’t** prefix them with "python3."
#
# ➔ Bottom line:
# - Shebang is essential for automation.
# - Not strictly needed for manual runs, but safe to always include.


"""
get_games_from_tv.py
~~~~~~~~~~~~~~~~~~~~
Periodically grabs **snapshots of the best ongoing games** from Lichess TV,
parses each PGN with `parse_pgn_lines`, and **upserts** the results into
a PostgreSQL table.

Execution flow
==============
1. Load DB credentials
   • Always fetch credentials from AWS Secrets Manager (DB_SECRET_NAME).
   • If RUNNING_IN_DOCKER=true, override the fetched PGHOST value to "db" (the Docker Compose service name).
   (load_db_credentials() handles both fetching and overriding automatically.)

   ➔ Why it’s designed this way:
     – Centralized secret management: AWS Secrets Manager holds the canonical, up-to-date credentials.
     – Environment independence: the code works the same in local, Docker, Airflow, ECS, etc.
     – Security: secrets never leak into GitHub, local files, or CLI history.
     – Reliable networking: inside Docker Compose, "db" correctly points to the Postgres container.
     – Operational simplicity: no messy "if env var" or "if Docker" branching — one unified loading path.

   ➔ Why documenting it clearly matters:
     – Avoids false expectations (e.g., thinking direct env-vars are used instead of Secrets Manager).
     – Makes the system self-explanatory and future-proof.
     – Reflects a professional production-grade pipeline design: AWS-first, environment-agnostic, secret-safe.

   ➔ Why not just rely on environment variables directly?
     – Env-vars are easy to misconfigure, can drift between machines, and expose secrets if mishandled.
     – Secrets Manager enforces a single, secure source of truth — safer, cleaner, and scales to cloud deployments.

2. Loop over every TV channel (bullet, blitz, classical, …).
   For each channel, call the Lichess endpoint `/api/tv/{channel}` to
   fetch a finite batch (≤10 games by default, ≤30 with `nb=`) of PGN
   text lines.

3. Read that batch line-by-line, detect when a full game is complete,
   and upsert it:
      • **INSERT** if the game ID is new.
      • **UPDATE** if the game ID already exists.
        The helper `upsert_game()` decides which action to take.

      – *Upsert* = “insert-or-update in one step.”
      – *Helper function* = a small, reusable sub-routine that keeps the
        main loop easy to read.

4. Repeat the channel sweep until either
      • total wall-clock time ≥ `TIME_LIMIT`, **or**
      • total ingested games in this run ≥ `MAX_GAMES`
        (triggers a self-throttle pause, then continues).

The function produces no return value; all work is done via side effects
(database writes and logging).
"""

# ────────────────────────────────────────────────────────────────────────────────
# Future imports (Python language features that change default behavior)
# ────────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

# This line tells Python to **store all type hints as plain strings** instead of trying to interpret them immediately.
# Normally, Python tries to resolve every type hint (like `Game`, `User`, etc.) as soon as it sees it.
# But with this setting, it *waits until the whole file is loaded* before interpreting the types.
#
# Why this matters:
# - If you reference a class or type that hasn't been defined yet, Python won’t crash — it will resolve it later.
# - You avoid errors when hinting types that are declared further down in the file or imported later.
#
# Example WITHOUT `from __future__ import annotations`:
#
#     def transform(game: Game) -> dict:
#
# If `Game` is not already defined *above* this function, Python will immediately crash with a NameError
# because it tries to interpret `Game` right away, before it knows what `Game` means.
#
# Example WITH `from __future__ import annotations`:
#
#     def transform(game: "Game") -> "dict"
#
# With the future import, Python **stores** type hints like `"Game"` and `"dict"` as plain text strings at first.
# It doesn't care whether `Game` is defined yet — it will figure it out *later* after the whole file is loaded.
#
# ➔ Bottom line: You can safely reference types that are defined *later* in the file without causing errors.
#
# With `from __future__ import annotations`, you get this safe behavior automatically — no need for manual quotes.
# This makes large projects like KnightShift more flexible, avoids circular import problems,
# and improves compatibility with modern tooling (editors, type checkers, etc.).


# ────────────────────────────────────────────────────────────────────────────────
# Standard library imports (Python built-in modules)
# ────────────────────────────────────────────────────────────────────────────────

import logging

# Standard logging module used to configure structured logging.
# In KnightShift, this lets us emit logs during game ingestion, retries, rate limits, and overall flow,
# and is useful for debugging or monitoring when running inside containers or Airflow tasks.

import os

# Gives access to OS-level functionality, like reading environment variables (e.g., TIME_LIMIT),
# which are used to control script behavior without modifying code. Also used to access file paths.

import sys

# Used for runtime environment operations like manipulating sys.path.
# Here, we insert the project root to enable clean local imports like `from src.db...` even when
# running the script directly (e.g., `./get_games_from_tv.py` from CLI or Airflow).

import time

# Provides time-related utilities like `time.sleep()` and timestamp differences.
# Critical for handling retry intervals, cooldowns, and timeout logic across ingestion loops.

from pathlib import Path

# `pathlib` is Python’s modern way to handle file system paths.
#
# Old approach (os.path):
# - Paths were just text strings.
# - You had to manually join parts with functions like os.path.join().
#
# New approach (pathlib):
# - Paths are real **Path objects** — not just strings.
# - You can join, navigate, and manipulate them using methods and the `/` operator,
#   making your code cleaner, more reliable, and easier to read.
#
# Example:
# - Old (os.path):
#     os.path.join("folder", "subfolder", "file.txt")
#
# - New (pathlib):
#     Path("folder") / "subfolder" / "file.txt"
#
# ➔ Why it matters:
# - It's automatically cross-platform (works the same on Linux, Mac, Windows).
# - It protects you from common bugs (like missing slashes between folders).
# - It makes complex paths easier to build and understand.
#
# ➔ In this project:
# - We use `Path` to dynamically build paths like `PROJECT_ROOT` and locate `.env.local`,
#   no matter where the script is started from (Docker, cron, Airflow, manual run, etc.).
# - This keeps paths reliable and portable, without hardcoding machine-specific details.

from typing import Final, List, Sequence

# Type hinting tools from the `typing` module help describe the shape of your data without changing
# how your code runs. `Final` is used to mark constants like `TIME_LIMIT` or `CHANNELS`, signaling
# that they’re not meant to be reassigned. While Python won’t enforce this at runtime, tools like
# PyCharm or static type checkers such as `mypy` will warn you if you try to change them, which makes
# your code more self-documenting and stable as it grows.

# `List` and `Sequence` are used to describe collections: `List[bytes]` says you're working with a
# list of byte strings (like PGN lines), while `Sequence[str]` is a more flexible version that can
# accept lists, tuples, or other ordered collections — useful when the function only needs to read,
# not modify. In KnightShift, these hints are especially helpful since you're working with lots of
# structured data passed between modules. Even if you're not explicitly running a type checker yet,
# your editor (like PyCharm) is already using these hints to provide better autocompletion,
# inline warnings, and smarter code navigation. They’re optional, but in a pipeline like this,
# they add a lot of safety and clarity for both you and your tools.


# ────────────────────────────────────────────────────────────────────────────────
# Third-party imports (installed via pip)
# ────────────────────────────────────────────────────────────────────────────────

import requests

# This is a third-party HTTP library that makes it easy to work with web APIs.
# It's much simpler and more powerful than older built-in tools like `urllib`, and it's considered
# the standard way to make API calls in most modern Python projects.
#
# In this script, we use `requests.Session()` to open a long-lived connection to the Lichess API
# and stream live PGN game data from Lichess TV. Sessions are more efficient than sending separate
# requests each time — they let us reuse the connection, handle headers, and manage retries if needed.

from dotenv import load_dotenv

# Loads environment variables from a `.env` file so the script can access config like DB credentials,
# API tokens, and timeouts without hardcoding them. This makes the script behave the same way across
# different environments — whether it’s run from PyCharm, Docker, Airflow, or the command line.
#
# In KnightShift, this supports a clean, production-style setup by abstracting away machine-specific
# settings from the code itself. Other developers (on any system) can simply edit their own `.env.local`
# file to match their environment, making the project portable, consistent, and easy to share.

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Time,
    create_engine,
)

# These are the building blocks for defining and interacting with a Postgres table using SQLAlchemy Core.
# - Table and Column let us define the schema for `tv_channel_games` in Python, instead of writing raw SQL.
# - Types like String, Integer, and Date help enforce the structure and data types expected in each column.
# - create_engine sets up the connection to the Postgres database so we can send and receive data.

from sqlalchemy.orm import Session, sessionmaker

# ─────────────────────────────────────────────────────────────────────
# Why import Session and sessionmaker
# ─────────────────────────────────────────────────────────────────────
# SQLAlchemy is a powerful toolkit for working with relational databases.
# It supports two main ways of writing database code:
#
# • Core (low-level style):
#   - You define tables and write queries manually.
#   - SQLAlchemy just helps you *build* SQL — you still think like a SQL developer.
#
# • ORM (high-level style):
#   - You map Python classes directly onto database tables.
#   - You interact with objects, not rows — much less raw SQL involved.
#
# In KnightShift, we use a **hybrid** approach:
# - We define our table (`tv_channel_games`) using **Core**.
# - But we manage **sessions** and **transactions** using a small piece of the **ORM** (`Session`, `sessionmaker`).
#
# ➔ Why this balance?
# - Core gives us precise, transparent control over the schema.
# - ORM Sessions give us clean transaction handling without manually managing every SQL commit.
#
# --- Quick overview of what we import ---
#
# - `sessionmaker`:
#     → Creates a *factory* that knows how to build sessions tied to our database engine.
#     → Each session represents a unit of work (like inserting/updating one game).
#
# - `Session`:
#     → Represents a single connection to the database, with transaction controls (begin, commit, rollback).
#     → In KnightShift, every call to `upsert_game()` uses a Session under the hood.
#
# --- Why Sessions matter for data safety ---
#
# Sessions automatically give us ACID properties:
#
# • Atomicity:
#     - Each upsert (insert/update) fully succeeds or fully fails — no half-written rows.
#
# • Consistency:
#     - Every change conforms to the table schema and database constraints.
#
# • Isolation:
#     - If we later scale up to parallel ingestion, sessions keep operations separate and safe.
#
# • Durability:
#     - Once a session commits, the changes survive even a crash or power loss.
#
# ➔ Bottom line:
# Using Core for schema + ORM sessions for transaction control gives KnightShift
# a lightweight but *very robust* foundation for continuous, reliable ingestion.


# ────────────────────────────────────────────────────────────────────────────────
# Local project imports (KnightShift modules)
# ────────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ➔ What this does:
# 1. `__file__` is a special variable — it holds the path of the current Python file (this script).
# 2. `.resolve()` turns it into an absolute path (no shortcuts like ".." left).
# 3. `.parent.parent.parent` walks up three folders from where this file is.
#
# Why three parents?
# - If this script is in something like: KnightShift/src/ingestion/get_games_from_tv.py
#   Going up three levels lands us back at the KnightShift **project root**.
#
# ➔ Why it matters:
# - Big projects often need to find config files, schemas, or other scripts based on a known root folder.
# - Different tools (like Docker, Airflow, cron jobs) might start the script from different "working directories."
# - If we don't set a stable starting point, imports like `from src.db.game_upsert import ...` might break.
#
# By setting `PROJECT_ROOT`, we always know exactly where the *real* top of the project is —
# no matter where or how this script is launched.

sys.path.insert(0, str(PROJECT_ROOT))  # idempotent

# ➔ What this does:
# - Python has a special list called `sys.path`.
#   It's the list of places Python checks — in order — whenever you write an `import`.
# - Normally, Python starts by checking the standard library, installed packages, and the current folder.
#
# - By inserting our `PROJECT_ROOT` at the very beginning of `sys.path` (at position 0),
#   we tell Python:
#     "First, look in *our project* for imports — before looking anywhere else."
#
# - This means imports like:
#     from src.db.game_upsert import upsert_game
#   will always work — because Python knows exactly where to find the `src` folder.
#
# - This is especially important in automation tools like Docker, Airflow, and cron,
#   because the *starting working directory* (where Python thinks it is when the script starts)
#   might be unpredictable.
#
#   For example:
#   - When you run `python3 get_games_from_tv.py` manually, your working folder is wherever you were in the terminal.
#   - But when Docker or Airflow runs your script, they might set the working directory to `/app/`, `/opt/airflow/`, or some internal container path you didn't choose.

from src.db.game_upsert import build_game_data, upsert_game

# KnightShift-specific database helpers:
# - build_game_data transforms parsed PGN metadata into a dictionary matching the DB schema.
# - upsert_game handles insert-or-update logic for each game into the `tv_channel_games` table.
#   This is important because during the Lichess TV stream:
#     • You might first capture a game while it’s still in progress (incomplete moves).
#     • Later, the same game ID can appear again — now with more moves or finalized results.
#   Upserting ensures the pipeline gracefully updates the existing game record,
#   rather than inserting duplicates or missing late-game updates.

from src.utils.db_utils import get_database_url, get_lichess_token, load_db_credentials

# Core utility functions for secure config management:
# - get_database_url takes a dictionary of DB credentials (user, password, host, port, db name)
#   and builds a full SQLAlchemy connection URL like:
#   "postgresql+psycopg2://user:password@host:port/dbname"
#   This URL tells SQLAlchemy how to connect to the Postgres database. We pass it to create_engine,
#   which creates a reusable connection object for sending queries and managing transactions.
#
# - get_lichess_token retrieves the API key needed to access Lichess TV stream.
# - load_db_credentials abstracts away whether we're using a local `.env` or AWS Secrets Manager,
#   making this script production-ready without changes.

from src.utils.logging_utils import setup_logger

# Creates a clean, production-grade logger with both console and file output:
#
# - Console logs: Always print to the terminal (stdout) — great for live runs,
#   viewing logs inside Docker containers, or monitoring Airflow tasks.
#
# - File logs: Also saves a full copy of the logs into a timestamped `.log` file
#   (saved under `/logs/` locally, or `/opt/airflow/logs/pipeline_logs` inside Airflow).
#   This makes it easy to review past runs even after the session ends.
#
# ➔ setup_logger() automatically handles:
#   - Consistent log formatting (timestamp | log level | message)
#   - Smart directory detection: knows whether we’re running locally vs. inside Airflow
#   - File-safe setup: creates the logs folder if needed, but keeps running even
#     if file writing isn’t possible (e.g., permission errors).
#
#   - Idempotent behavior:
#     • In Python logging, a **handler** is an object that decides *where* your log messages go
#       — like the console (StreamHandler) or a log file (FileHandler).
#     • If you don’t clear old handlers, you can accidentally "stack" outputs —
#       causing the same log message to be printed multiple times.
#     • setup_logger() **removes all old handlers first**, so every time you call it,
#       you get exactly one clean console output and (optionally) one file output — no duplicates.
#
# In short:
# Every script that calls setup_logger() immediately gets structured,
# consistent, dual-destination logging — perfect for real-world pipelines,
# debugging during development, and clean operational monitoring.

from src.utils.pgn_parser import parse_pgn_lines

# Core PGN parser function.
#
# ➔ "Parsing" means: taking messy, unstructured raw text (PGN lines) and
#    analyzing it carefully to pull out meaningful pieces of information.
#
# In this case:
# - The raw stream from Lichess is just **lines of text** (like "[White "MagnusCarlsen"]", "1. e4 e5", etc.)
# - `parse_pgn_lines` reads through those lines **one by one**,
#   and organizes them into a clean Python dictionary with:
#     • metadata (who played, ratings, variant, etc.)
#     • move list (the sequence of moves in the game)
#
# ➔ Why this matters:
# - Computers can't easily understand raw text — they need **structured** data.
# - This parsing step transforms the chaotic text stream into a clean format
#   that can be **inserted into the database** correctly.
#
# Without parsing first, we couldn't search, store, or analyze the games properly.
#
# In short: parse_pgn_lines is the brain that turns messy chess game text
# into usable, structured information.


# ──────────────────────────────────────────────────────────────────────────
#   Environment & config
# ──────────────────────────────────────────────────────────────────────────

ENV_FILE = PROJECT_ROOT / ".env.local"

# Build the full, absolute path to our `.env.local` config file.
#
# ➔ Why do it this way (with PROJECT_ROOT)?
# - If you just hardcoded a relative path (like "../../config/.env.local"),
#   it would *only* work if you launched the script from a very specific folder.
# - But in real projects (cron jobs, Docker, Airflow, CLI runs),
#   scripts can be launched from **different** starting locations.
#
# ➔ Using PROJECT_ROOT makes this path *absolute* — based on where the script physically lives,
#   not based on where you ran it from.
#
# ➔ Result: No matter what machine, OS, Docker container, or working directory you're in,
#   Python will *always* find `.env.local` correctly — fully automatic, zero guessing.

load_dotenv(ENV_FILE)

# Load all the variables from the .env.local file (like DB credentials, API keys, etc.)
# into the current process's environment, so Python can access them with os.getenv().
#
# ➔ Priority:
# - If a variable is already set in the operating system (e.g., by Docker, Airflow, or CI/CD),
#   that value takes priority.
# - If not, the script falls back to the value from .env.local.
#
# ➔ Why this matters:
# - Keeps sensitive secrets (like passwords) *out* of the codebase and Git history.
# - Makes the project easily portable — any machine can run it safely without hardcoding secrets.
#
# In short: this line makes KnightShift run cleanly whether it's on your laptop, inside Docker,
# or deployed on an automated server — without needing to change any code.


# --------------------------------------------------------------------------
# LOGGER
# --------------------------------------------------------------------------

LOGGER = setup_logger("get_games_from_tv", level=logging.INFO)

# A logger is a Python object (an instance of logging.Logger) that records
# messages like INFO, WARNING, and ERROR while the script runs.
#
# We create a *module-level* logger — meaning a single shared LOGGER object
# at the top of the file. All functions can simply call LOGGER.info(...),
# LOGGER.error(...), etc., without creating new loggers themselves.
#
# `setup_logger(name, level)` is a helper that builds and configures the logger.
# - `name="get_games_from_tv"`: the name given to this logger, making it easy to
#   identify its messages in Docker logs, Airflow UI, or monitoring tools.
# - `level=logging.INFO`: sets the minimum severity of messages to capture.
#   (INFO = normal runtime events; DEBUG = very detailed troubleshooting output.)
#
# By default, the logging level is set to INFO — meaning you'll see normal
# high-level events like startup, batch results, and game updates. If you want
# more granular logs (like individual API calls or PGN parsing), you can set a
# DEBUG-level override using an environment variable like this:
#
#     LOG_LEVEL=DEBUG python main.py
#
# In short: this LOGGER gives the whole script a clean, consistent way to
# record events without manual print() statements.

# --------------------------------------------------------------------------
# Numeric environment variables with *sane fallbacks*
# --------------------------------------------------------------------------

TIME_LIMIT: Final[int] = int(
    os.getenv("TIME_LIMIT", 30)
)  # Max number of seconds to keep fetching games before stopping the entire ingestion run.

SLEEP_INTERVAL: Final[int] = int(
    os.getenv("SLEEP_INTERVAL", 5)
)  # Number of seconds to sleep between batches of channel fetches (light pacing between loops).

RATE_LIMIT_PAUSE: Final[int] = int(
    os.getenv("RATE_LIMIT_PAUSE", 900)
)  # Voluntary cooldown (in seconds) if MAX_GAMES is reached — self-throttling to avoid server rate-limiting (NOT triggered by 429 errors).

MAX_GAMES: Final[int] = int(
    os.getenv("MAX_GAMES", 5000)
)  # Max number of games to ingest before triggering a RATE_LIMIT_PAUSE cooldown.

# These configuration values control how long the ingestion loop runs,
# how often it sleeps, and how it handles rate limits.

# TIME_LIMIT: Final[int] means:
#   "TIME_LIMIT is an integer that should be considered constant after it's set."

# The = int(os.getenv("TIME_LIMIT", 30)) part:
# - Calls os.getenv("TIME_LIMIT", 30):
#      • Looks for an environment variable called "TIME_LIMIT".
#      • If it finds one, uses its value.
#      • If it doesn't find one, uses 30 instead.
# - Then int(...) converts that value (which comes in as a string) into an actual integer.

# Why the fallbacks matter:
# - Local development: the script can run immediately, even if you haven't
#   manually set up every environment variable. Defaults make it easy to test.
#
# - Docker / CI pipelines: you can inject environment variables at runtime
#   (e.g., with `--env` flags or Docker Compose env files) to override the defaults
#   without touching the codebase.
#
# - Airflow: when KnightShift runs as a DAG, you can fine-tune these parameters
#   dynamically using **Airflow Variables**, which are editable from the web UI.
#
#   To update one:
#     1. Open Airflow’s UI at http://localhost:8080
#     2. Go to **Admin → Variables → + Add a new record**
#     3. Set the key to something like TIME_LIMIT and the value to a number (e.g., 300)
#
#   Your DAG can then read that variable using:
#       TIME_LIMIT = int(Variable.get("TIME_LIMIT", 30))
#
#   This works even if the Airflow "Admin → Config" section is hidden for security reasons.
#   You don’t need to edit the code, rebuild containers, or restart anything —
#   just change the value in the UI, and the next DAG run will pick it up automatically.

# --------------------------------------------------------------------------
# Channel list
# --------------------------------------------------------------------------

# Predefined TV channels on Lichess, each corresponding to a specific variant (bullet, blitz, etc.).
# We mark the tuple as `Final` so downstream code doesn't accidentally append/delete channels.
#
# Each channel has its own live game stream via the Lichess API (e.g., /api/tv/blitz, /api/tv/rapid).
# The pipeline explicitly loops through these channels.
#
# We use a *tuple* (instead of a list) because a tuple is immutable — once created,
# its contents can't be changed. This protects the list of channels from being modified
# by mistake while the script is running, keeping the behavior predictable and safe.

CHANNELS: Final[Sequence[str]] = (
    "bullet",
    "blitz",
    "classical",
    "rapid",
    "chess960",
    "antichess",  # Capture-to-win variant
    "atomic",  # Pieces explode on capture
    "horde",  # One side has a ‘horde’ of pawns vs. regular army
    "crazyhouse",  # Captured pieces can be dropped back in
    "bot",  # Engine vs. engine showdowns
    "computer",  # Human vs. computer on Lichess
    "kingOfTheHill",  # Win by bringing king to the center
    "threeCheck",  # Win by giving three checks
    "ultraBullet",
    "racingKings",  # Race your king to the opposite side
)

# Keeping this channel list as *simple data* (a constant tuple) — not scattered across the code —
# makes it easy to see, maintain, and modify all in one place.
#
# If Lichess ever adds new TV channels, you can just update this one CHANNELS tuple,
# without hunting through the rest of the code for hardcoded channel names.
#
# This design makes the ingestion logic *generic*: the streaming functions don’t care
# *which* channels exist — they just loop over whatever is listed here.
#
# In short: treating channels as clean, centralized data (instead of mixing them into
# procedural code) keeps KnightShift flexible, future-proof, and easy to extend.


# ──────────────────────────────────────────────────────────────────────────────
#   DATABASE SETUP
# ──────────────────────────────────────────────────────────────────────────────
#
# Goal → hand the rest of the script a clean SQLAlchemy connection to Postgres.
#
# How credentials are loaded
# --------------------------
# • `load_db_credentials()` **always** fetches a JSON secret from
#   **AWS Secrets Manager** (`DB_SECRET_NAME`, default "LichessDBCreds").
# • If the script is running inside Docker (`RUNNING_IN_DOCKER=true`)
#   it replaces the secret’s `PGHOST` with `"db"` so the connection points
#   at the Postgres service on the internal compose network.
# • If the secret call fails, the helper raises `RuntimeError`; there is
#   no fallback to local `PG*` env-vars in this version of the function.
#
# Why we still set PG* env-vars in docker-compose.yml
# ---------------------------------------------------
# Other containers (psql CLI, Airflow’s metadata DB URL, etc.) *do*
# read those variables.  Our ingestion script, however, relies solely
# on the AWS secret + the optional host override.
#
# Workflow (4 logical steps)
# --------------------------
# 1️⃣  `CREDS`  ←  load_db_credentials()          # dict of user/pass/host/…
# 2️⃣  `ENGINE` ←  create_engine(get_database_url(CREDS))
# 3️⃣  `SESSION` ← sessionmaker(bind=ENGINE)()    # transaction workspace
# 4️⃣  `TV_GAMES_TBL` ← Table(…)                  # explicit Core schema
#
# We use SQLAlchemy **Core** for schema/query clarity, plus a light touch
# of the ORM (`Session`, `sessionmaker`) for automatic ACID transactions.
#
# SQLAlchemy offers two main styles:
#   • **Core** – explicitly define tables and columns, and issue structured SQL commands.
#     (This keeps full control over the database structure and is ideal for pipelines that prioritize
#      clarity, control, and performance — like KnightShift.)
#
#   • **ORM** – map full Python classes to database rows, treating the database more like a Python object graph.
#     (Useful for complex applications with lots of relational logic, but heavier and less direct.)
#
# In this pipeline, we intentionally favor **Core**:
# - The schema (chess games table) is simple and stable.
# - Direct control over SQL makes debugging, scaling, and migrations easier.
# - Avoids unnecessary complexity from ORM features we don't need.
#
# Either way, SQLAlchemy automatically handles connection pooling, type checking,
# transaction safety (ACID), and SQL generation behind the scenes.

# ──────────────────────────────────────────────────────────────────────────────
# 1️  LOAD CREDENTIALS  (helper function)
# ──────────────────────────────────────────────────────────────────────────────

CREDS = load_db_credentials()

# `load_db_credentials()` comes from src/utils/db_utils.py. It knows where to look
# for (env-vars or AWS Secrets Manager) and hands back a tidy dict of:
#     {"user": "...", "password": "...", "host": "...", ...}
#
# (Note: parentheses `()` actually *run* the function and assign its **returned value** — not the function itself — to `CREDS`.)

# ──────────────────────────────────────────────────────────────────────────────
# 2  BUILD THE ENGINE  (a reusable connection object)
# ──────────────────────────────────────────────────────────────────────────────

ENGINE = create_engine(get_database_url(CREDS))

# In Python, an *object* bundles both **state** (data it holds) and **behavior** (methods it can perform).

# Here, `ENGINE` is a SQLAlchemy *Engine object*. It does three important things:
#   • Remembers our database connection settings (user, password, host, port, database name).
#   • Manages a **pool of reusable connections** to Postgres (saving time by avoiding constant reconnects).
#   • Exposes methods that translate Python commands into raw SQL and send them to the database.

# `create_engine()` is a built-in SQLAlchemy function:
# - It takes a **database connection URL** — not a website address, but a special string
#   that describes *how* to connect to the database (what driver, what user, what host, etc.).
#
# - Example format:
#     "postgresql+pg8000://username:password@host:port/database"
#
#   (It looks like a website URL, but it’s really just a **standard way to bundle connection settings**
#    into one readable string.)

# We pass `create_engine()` a connection URL built by our helper `get_database_url(CREDS)`,
# which formats the correct username, password, host, port, and database name from the credentials.

# ➔ Bottom line:
# The `ENGINE` acts like a central, long-lived gateway for sending SQL from our Python code to Postgres efficiently and safely.


# ──────────────────────────────────────────────────────────────────────────────
# 3️  OPEN A SESSION  (your ACID-aware workspace)
# ──────────────────────────────────────────────────────────────────────────────

SESSION: Session = sessionmaker(
    bind=ENGINE
)()  # ← build the factory, then immediately create one Session

# A SQLAlchemy *Session* is like a temporary workspace for database operations:
#   • You can stage multiple INSERTs, UPDATEs, or DELETEs inside it.
#   • `.commit()` saves all changes together atomically (all-or-nothing).
#   • `.rollback()` cancels any staged changes if something goes wrong.

# ➔ In this script:
# - We don't manually call `.commit()` or `.rollback()`.
# - Each call to `upsert_game()` **wraps its own database operation in a mini-transaction**.
# - Even so, having a Session **is still essential**: it guarantees every insert/update follows ACID rules.

# ➔ Syntax breakdown:

# 1. `sessionmaker(bind=ENGINE)` → builds a **factory** — an object ready to create new Sessions.
#    (It’s like pre-configuring a machine with connection settings but not running it yet.)
#
# 2. Adding `()` — `sessionmaker(bind=ENGINE)()` → **immediately calls the factory** to create **one** real Session.
#
# ➔ Why this matters here:
# - We only need **one** Session instance for the whole script.
# - `upsert_game()` handles transactions cleanly within that single Session.
# - No need to create a new Session for every database action — reuse is clean and safe.

# ➔ Bottom line:
# - `SESSION` is the final, ready-to-use database workspace.
# - It stays open for the lifetime of the ingestion run, safely handling all game upserts.


# ──────────────────────────────────────────────────────────────────────────────
# 4  DESCRIBE THE TABLE  (schema definition)
# ──────────────────────────────────────────────────────────────────────────────

METADATA = MetaData()

# MetaData = a "catalog" that collects the structure of all tables we define in Python.
#
# SQLAlchemy uses a special object called *MetaData* to keep track of the tables
# and database structures you define in Python.
#
# It stores *schema data* — table names, columns, types, and constraints — but doesn't
# send anything to the database yet. It's just a blueprint in memory.
#
# Later, when we insert or query, SQLAlchemy uses this MetaData to understand
# how to map Python code to real database tables.
#
# ➔ In larger projects, you might define many tables (e.g., users, ratings, games),
# and they would all be registered into a **single shared MetaData object**.
# This lets SQLAlchemy manage everything cleanly — one central catalog, multiple tables.
#
# ---------------------------------------------------------------------------
# How we are actually using it in this script:
#
# 1. We create one `MetaData()` object (called METADATA).
#
# 2. We define the `TV_GAMES_TBL` table and register it inside this METADATA.
#    (This links the table structure to the catalog.)
#
# 3. When we call database helpers like `upsert_game(SESSION, TV_GAMES_TBL, db_row)`,
#    SQLAlchemy automatically looks at TV_GAMES_TBL → sees it belongs to METADATA →
#    and uses the stored schema (columns, types) to generate correct SQL.
#
# 4. We never manually query the METADATA object — it works silently behind the scenes.
#    It ensures that every insert, update, or query happens with the correct table layout.
#
# 5. If needed, we could later call `METADATA.create_all(ENGINE)` to create the table(s)
#    in Postgres based on this Python definition — but in this script, we assume the table
#    already exists and just use the metadata for *mapping* and *validation*.
#
# Final result: METADATA ensures that our Python-side definition of the chess-games table
# always matches the real database, without needing handwritten SQL.

# `Table(...)` is a *declarative recipe* — it defines the table layout in Python.
# We are *not* sending anything to Postgres yet. We're just describing:
#     • the table's name
#     • what columns it has
#     • what types and constraints those columns follow
#
# --- SYNTAX BREAKDOWN ---
#
# Table(
#     <table_name_in_db>,     # a string: name of the real table inside Postgres
#     <metadata_object>,      # our METADATA catalog that collects all tables
#     <column_definitions...> # one Column(...) call per field
# )
#
# Each `Column(...)` inside the Table does three things:
#   1. Gives the database column a name (first argument, like "id" or "white").
#   2. Assigns a SQL data type (second argument, like String, Integer, Date).
#   3. Optionally sets extra rules (like `primary_key=True`).

TV_GAMES_TBL = Table(
    "tv_channel_games",
    METADATA,
    Column("id_game", String, primary_key=True),
    Column("val_event_name", String),
    Column("val_site_url", String),
    Column("dt_game", Date),
    Column("id_user_white", String),
    Column("id_user_black", String),
    Column("val_result", String),
    Column("dt_game_utc", Date),
    Column("tm_game_utc", Time),
    Column("val_elo_white", Integer),
    Column("val_elo_black", Integer),
    Column("val_title_white", String),
    Column("val_title_black", String),
    Column("val_variant", String),
    Column("val_time_control", String),
    Column("val_opening_eco_code", String),
    Column("val_termination", String),
    Column("val_moves_pgn", String),
    Column("val_opening_name", String),
    Column("tm_ingested", DateTime),
    Column("ind_validated", Integer),
    Column("val_validation_notes", String),
    Column("tm_validated", DateTime),
    Column("ind_profile_updated", Integer),
)

# --- WHAT OUR TV_GAMES_TBL DOES ---
#
# 1. "tv_channel_games" → This table will be named "tv_channel_games" in Postgres.
# 2. METADATA → It registers this table in our in-memory catalog, so SQLAlchemy knows about it.
# 3. Column(...) definitions → It lays out 18 fields.
#
# --- IMPORTANT NOTES ---
#
# • This definition lives purely in Python memory for now.
# • Postgres won't see anything until we start inserting.
# • When we use `upsert_game()`, it uses TV_GAMES_TBL to know:
#     - What columns exist
#     - What types they expect
#     - How to format our insert/update queries
#
# --- FINAL THOUGHT ---
#
# Defining tables this way makes the pipeline **self-documented**:
# you can read this code and instantly know what data your database expects,
# without digging through messy SQL migration files or admin panels.

# At runtime, when SQLAlchemy first needs this table (e.g., on the first insert),
# it will compare the Python definition to what’s in Postgres and create the table
# if it doesn’t yet exist.  From there, every insert/update we do through SESSION
# automatically respects this schema.

# -------------------------------------------------------------------------------
# Why this structured database setup matters
# -------------------------------------------------------------------------------

# • Centralized helper function loads DB credentials from AWS Secrets Manager (with a PGHOST override if running inside Docker).
# • One Engine object is shared across all operations → fewer DB connections, cleaner code.
# • A single Session manages each batch of writes safely → small, atomic ACID transactions.
# • Table structure is defined once in Python → no scattered raw SQL strings.
#
# ➔ Result:
# A database layer that’s easy to read, easy to extend, and reliable
# for continuous chess-game ingestion.


# ──────────────────────────────────────────────────────────────────────────
#   Lichess API session
# ──────────────────────────────────────────────────────────────────────────

# --- BIG PICTURE ---
#
# This block sets up a reusable connection ("session") to the **Lichess API**.
# Instead of opening a brand-new HTTP connection for every single request (slow!),
# we create one `requests.Session()` and reuse it across many API calls.
#
# This is important because:
# - Lichess streams games continuously — we don't just send one request, we stay connected.
# - Reusing a session keeps headers (like our API key) automatically attached to every request,
#   meaning we stay authenticated without manually resending credentials each time.
# - It's more efficient and robust: lower overhead (fewer TCP handshakes) and better retry handling
#   if connections are interrupted.

HTTP = requests.Session()

# `requests.Session()` creates a new **HTTP session object** — a tool that manages reusable connections to a server.
#
# ➔ What is a connection?
# - When your program talks to a server (like Lichess), it must first **open a network connection**:
#     • Behind the scenes, this sets up a TCP/IP "tunnel" between your computer and the server.
#     • Through this tunnel, data is sent back and forth (requests you send, responses you receive).
# - Once the request is finished, if you're not using a session, **Python closes that tunnel** immediately.
#
# ➔ Without a session:
# - Every `requests.get()` or `requests.post()`:
#     1. Opens a new TCP connection (slow, some overhead).
#     2. Sends the request.
#     3. Gets the response.
#     4. Closes the connection right after.
# - If you send 100 requests, Python opens/closes the connection 100 separate times.
#
# ➔ With a session:
# - You **open the tunnel once** with `requests.Session()`.
# - Then you can send many requests through the same open tunnel.
# - The Session:
#     • Keeps the connection open between requests (saving time and resources).
#     • Automatically attaches important settings (like headers, cookies, auth tokens) to every request — no need to set them again.
#
# ➔ Why it matters here:
# - Lichess TV is a **live-streaming** API — it keeps sending us data continuously.
# - Reusing a Session lets us stay connected and efficient, without breaking the stream or wasting time.
#
# We store the Session object in a variable called `HTTP` (all caps because it’s used globally across the script).

HTTP.headers.update(
    {
        "Content-Type": "application/x-www-form-urlencoded",  # Data format for the request body
        "Authorization": f"Bearer {get_lichess_token()}",  # Our Lichess API key
    }
)

# `.headers` is a dictionary inside the Session.
# It holds **default headers** that are automatically attached to every request this session sends.
#
# `.update({...})` adds or updates multiple headers at once — setting the defaults we want.

# ➔ What we set here:
#   • "Content-Type": tells the server what kind of data we're sending.
#     - `application/x-www-form-urlencoded` means the body will be simple "key=value&key=value" text,
#       not JSON or binary — which is exactly what the Lichess API expects for form data.
#
#   • "Authorization": proves to Lichess who we are.
#     - `get_lichess_token()` fetches our secret API token from environment settings (like a password).
#     - `Bearer {token}` is the format Lichess requires: the word "Bearer" + a space + the token.
#       (This is standard in most OAuth-secured APIs.)

# --- WHY THIS MATTERS ---
#
# • Now, **every time** we call `HTTP.get()` or `HTTP.post()`, these headers are **automatically** included.
# • We don't have to manually pass them every time — saving effort and preventing mistakes.
# • Without the Authorization header, the server would reject us with a `401 Unauthorized` error.
# • Setting these headers once at the start keeps the Session "identity" and "data format" consistent
#   across hundreds or thousands of streamed requests.
#
# ➔ Big picture:
#   Instead of starting a new conversation from scratch every time ("Hello, I am user X, here is my key..."),
#   the session **remembers your credentials and speaking style** (headers) — like a polite ongoing conversation.
#
# In short:
# ➔ This block **prepares our Session to securely and correctly talk to Lichess** — without us having to remember
# to manually repeat ourselves every time.


# ──────────────────────────────────────────────────────────────────────────
#   Helper functions
# ──────────────────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────────────────
# Helper: _process_game_block — parse one PGN chunk and write it to Postgres
# ──────────────────────────────────────────────────────────────────────────
#
# What this helper does:
# • Accepts a batch of *raw PGN lines* (bytes) for a **single chess game**.
# • Parses the raw bytes → builds a structured dictionary (metadata + moves).
# • Reshapes it into a DB-ready row (matching the tv_channel_games table).
# • Calls `upsert_game()` to either:
#     → INSERT a new row (if the game ID is new),
#     → or UPDATE the existing row (if the game ID already exists).
# • Updates the `added` or `updated` tracking list depending on the outcome.
#
# Key terms:
#   PGN          – Portable Game Notation (standard text format for recording chess games).
#   upsert       – "insert if new, update if already there" (saves or updates without duplicating).
#   Session      – our active SQLAlchemy session (handles safe transactions to the database).
#   TV_GAMES_TBL – the SQLAlchemy `Table` object describing the tv_channel_games table structure.
#
# Important details:
# • Returns nothing (`-> None`) — it only produces *side effects*:
#     → writes to the database
#     → updates the in-memory tracking lists (`added`, `updated`).
#
# • The leading underscore (`_process_game_block`) is a Python convention meaning:
#   "This is a *private helper* — meant for internal use inside this file/module only."
#   (Python won’t enforce this rule, but it's a strong signal to other developers.)


def _process_game_block(
    pgn_lines: List[bytes],  # raw PGN bytes for ONE game
    added: List[str],  # list of IDs we successfully inserted
    updated: List[str],  # list of IDs we updated in place
) -> None:
    game = parse_pgn_lines(pgn_lines)

    # 1️⃣  Parse the raw PGN into a Python dict (headers, moves, etc.)
    # Imported from src/utils/pgn_parser.py

    if "site" not in game:
        return

    # 2️⃣  Sanity-check: if parsing failed (no "site" URL) → skip this game.

    db_row = build_game_data(game)
    # 3️⃣  Shape the dict to match our table schema.
    # Imported from src/db/game_upsert.py

    was_updated = upsert_game(SESSION, TV_GAMES_TBL, db_row)

    # 4️⃣  Upsert the game into Postgres.
    #     • If the game ID already exists → update the existing row (was_updated = True).
    #     • If the game ID is new → insert a fresh row (was_updated = False).
    #
    # `upsert_game()` handles both cases automatically:
    # - It checks if the game ID already exists.
    # - It decides whether to INSERT or UPDATE.
    # - It returns True if an UPDATE occurred, False if an INSERT occurred.

    (updated if was_updated else added).append(db_row["id"])

    # 5️⃣  Record the outcome: keep stats for the calling loop.
    #
    # This is a **one-line if-else**, also called a **ternary expression** in Python.
    # - If `was_updated` is True → append the game ID to the `updated` list.
    # - Otherwise → append the game ID to the `added` list.
    #
    # Even though this is the **last line** of the function,
    # it’s **NOT** a `return` statement — it's just a **normal action**.
    # (Functions don't have to end with `return` unless you want to send something back.)
    #
    # This line **modifies** one of the input lists (`added` or `updated`),
    # using their `.append()` method to add the game's ID.


def _stream_channel(channel: str, added: List[str], updated: List[str]) -> None:
    """Fetch a batch of games from one TV channel, handle retries & rate‑limits."""

    # Define a helper function to stream games from a single TV channel on Lichess.
    # The underscore at the beginning (_stream_channel) signals that this is a "private" function —
    # meaning it’s intended for internal use inside this file, not for outside code to call directly.

    # Arguments:
    # - channel (str): the name of the TV channel to stream (like "blitz", "bullet", etc.)
    # - added (List[str]): a list that will store IDs of newly added (inserted) games
    # - updated (List[str]): a list that will store IDs of games that were updated (already existed)

    # This function doesn’t return anything — it performs actions (streaming, parsing, inserting).

    url = f"https://lichess.org/api/tv/{channel}"

    # Build the URL to connect to the Lichess TV API.
    # Use an f-string to dynamically insert the channel name into the URL.
    # For example, if channel="blitz", the URL becomes:
    #    https://lichess.org/api/tv/blitz

    params = {"clocks": False, "opening": True}

    # Define additional parameters to customize the API response:

    # - clocks=False: don't include move-by-move clock times in the PGN (we don't need them)
    # - opening=True: include the opening name and ECO code for each game (useful metadata)

    for attempt in range(1, 4):
        # Try up to 3 times to connect to the Lichess TV API.

        resp = HTTP.get(url, params=params, stream=True)

        # --- POTENTIAL WAIT SPOT ---
        # Waiting here briefly while the server sends the PGN batch.
        # (Usually <1 second unless the network is slow.)

        # ➔ Send a GET request to the Lichess TV API (`url`) with query parameters (`params`),
        #    and `stream=True` so we can **read lines immediately** as they arrive.

        # `resp` is a `requests.Response` object containing a **batch** of PGN text lines
        # for the current best games on this one TV channel (like blitz, bullet, etc.).

        # ─────────────────────────────────────────────────────────────────────────────
        # How this Lichess endpoint behaves:
        # ─────────────────────────────────────────────────────────────────────────────
        #
        # • It sends a **finite batch** of games — NOT a continuous real-time stream.
        #   (Default: up to 10 games per call, maximum: 30 if you request it.)
        #
        # • After sending the full batch, the **server closes the connection** automatically.
        #   (Only the connection closes — our HTTP session (`HTTP`) stays open for reuse.)
        #
        # • `_parse_stream(resp, added, updated)` immediately reads and processes this batch —
        #   no idle waiting, no long-lived connections.
        #
        # • Example:
        #     → If each of 16 channels provides ~10 games,
        #     → one sweep collects ~160 games in seconds.
        #     → In two or three sweeps, we can easily ingest hundreds of games under a 30-second TIME_LIMIT.
        #
        # • Why `stream=True` matters:
        #     → It lets us **start processing lines instantly** as they arrive,
        #     → without waiting for the entire batch to finish downloading.
        #     → This keeps memory usage tiny even if lots of games are sent.
        #
        # • Channel pacing:
        #     → After one batch finishes, we immediately move to the next channel.
        #     → Only `SLEEP_INTERVAL` and global TIME_LIMIT/MAX_GAMES control overall timing.
        #
        # • (Optional tweak:
        #     → To fetch up to 30 games per channel instead of 10, simply set `params["nb"] = 30` before calling `.get()`.)

        if resp.status_code == 429:  # too many requests → bail out
            # If Lichess returns HTTP status 429, it means we've been rate-limited
            # (we sent too many requests in a short period).
            # In that case, we immediately log an error and exit the script.

            LOGGER.error("Rate‑limit (429) on '%s' – exiting", channel)

            # Record an error message in the logs to help diagnose the problem later.

            sys.exit(1)

            # Exit the entire script with exit code 1 (general failure).
            # It's better to stop cleanly than to keep retrying and make it worse.

        if resp.ok:
            # If the response was successful (status code 200–299), we're good.
            # Break out of the retry loop and move on to processing the stream.
            break

        # If we reach here, it means the response was NOT ok (but not 429 either).
        # Maybe a server error like 500, or bad gateway 502, or temporary network glitch.

        LOGGER.warning(
            "Channel '%s' returned %s (%s/3) – retrying in 5 s",
            channel,
            resp.status_code,
            attempt,
        )

        # Log a warning message that shows:
        # - Which channel failed (like "blitz")
        # - What HTTP status code we got back (like 502)
        # - Which retry attempt this was (like 1, 2, or 3)

        # The "%s" parts inside the string are called *format specifiers*.
        # Each "%s" means: "insert a value here when the message is actually logged."
        # It does *not* immediately insert the value — it waits until the logger decides
        # that the message should actually be output (for example, based on log level).

        # After the string, we pass extra arguments: (channel, resp.status_code, attempt).
        # These are inserted into the "%s" placeholders **in order** — first value fills the first %s,
        # second value fills the second %s, third value fills the third %s.

        # IMPORTANT: Even if the value is a number (like status_code = 502),
        # "%s" will automatically convert it to a string behind the scenes — no manual conversion needed.

        # Example:

        # Suppose:
        #   channel = "blitz"
        #   resp.status_code = 502
        #   attempt = 1
        #
        # Then the final log message will look like:
        #   "Channel 'blitz' returned 502 (1/3) – retrying in 5 s"

        # Why not just use f-strings (f"...{channel}...") here?
        #
        # Because this %s-style formatting *delays* string assembly until it's actually needed.
        # - If the logger decides to ignore this message (for example, if the log level is set higher),
        #   Python saves time by *never building the full string* at all.
        # - This makes logging slightly faster and more efficient in large systems.

        # Short version: "%s" placeholders + passing arguments separately is an older,
        # but very efficient and still very common way to format logs in Python.

        time.sleep(5)

        # --- EXPLICIT WAIT ---
        # Sleep 5 seconds before retrying (in case of server hiccup or temporary network errors)...
        # This gives Lichess (or the network) time to recover if it was a temporary problem.

    else:
        # ➔ Important: this `else` belongs to the `for` loop — not to any `if`.
        #
        # ➔ How `for-else` works:
        # - The `else` block only runs if the `for` loop finishes **without hitting a break**.
        # - If the loop did break early (e.g., after a successful response), the `else` is skipped.
        #
        # ➔ In our case:
        # - We try up to 3 times to fetch the TV channel.
        # - But **all 3 tries** failed ("not OK but not 429") — no break happened.
        # - So, we fall into this `else` block.
        #
        # ➔ Meaning:
        # - We failed to get a successful response after 3 attempts.
        # - No point retrying anymore — log an error and exit early.

        LOGGER.error("Could not connect to '%s' after retries", channel)

        # Log a final error message showing which channel we failed to connect to after retrying.

        return

        # Exit the function early because we couldn’t get a working API connection.
        # We don't want to try parsing a broken or missing response.

    _parse_stream(resp, added, updated)

    # If we reach this line, it means we successfully connected to the Lichess API
    # and received a valid HTTP response (status 200).
    #
    # At this point:
    # - `resp` is the good HTTP response containing a finite batch of PGN game data.
    #
    # Now we call the helper `_parse_stream()` to read the PGN lines **one by one**,
    # detect complete games, and upsert each one into the database.
    #
    # What we pass:
    # - `resp`: the raw response object containing the streamed PGN data.
    # - `added` and `updated`:
    #      ➔ These two lists were **created in `run_tv_ingestion()`** at the beginning of each batch:
    #
    #          added, updated = [], []
    #
    #      ➔ They are **empty lists** at the start of each batch, handed down to `_stream_channel()`,
    #         and now handed further into `_parse_stream()`.
    #
    #      ➔ As `_parse_stream()` processes each complete game, it will:
    #          - Append the game's ID to `added` if it was newly inserted.
    #          - Append the game's ID to `updated` if it already existed and was updated.
    #
    # ➔ Purpose:
    # - These lists **collect game IDs across the entire batch**, so at the end of the batch
    #   we can easily log how many games were added and how many were updated.


def _parse_stream(
    resp: requests.Response, added: List[str], updated: List[str]
) -> None:
    """Parse and upsert games from a PGN batch."""

    # What the API returns
    # ---------------------
    # • `/api/tv/{channel}` gives a **snapshot** of the best ongoing games —
    #   up to 10 games by default, or 30 if we pass `nb=30`.
    # • Lichess sends the full batch almost instantly, then
    #   **closes the connection**.
    # • There is no continuous feed — just a one-time payload.

    # Why we set stream=True
    # -----------------------
    # • Normally, when you make a request, Python waits until the **entire response** downloads
    #   before letting you read anything (even if the server is still sending data).
    #
    # • `stream=True` tells Python:
    #     "Don't wait for the whole response — let me start reading it **line-by-line immediately** as it arrives."
    #
    # • This matters because:
    #     → The Lichess TV API sends a *batch* of PGN game data.
    #     → With `stream=True`, we can start processing the PGN lines **while the server is still finishing the batch**.
    #     → We don’t have to wait for all ~10–30 games to fully download before we begin parsing.
    #
    # • Is it critical here?
    #     → Not really — the batches are small (10–30 games), so memory isn't a big concern.
    #     → But using `stream=True` is still a good habit:
    #         - Keeps memory usage low no matter the batch size.
    #         - Makes behavior consistent if the server ever sends larger batches later.
    #         - Lets us *start parsing sooner*, reducing perceived latency slightly.
    #
    # ➔ Bottom line:
    #   - `stream=True` doesn’t make things run out-of-order or asynchronously.
    #   - It just **allows** us to begin reading immediately, *as soon as the server starts sending data*,
    #     instead of waiting for the full response.

    # How control flows between helpers
    # ----------------------------------
    # 1. `_stream_channel()` opens the connection (GET request + retries).
    # 2. As soon as it gets a **200 OK** response, it calls `_parse_stream(resp, …)`.
    #    `_stream_channel()` then **waits**.
    # 3. `_parse_stream()` drains the response line-by-line,
    #    detects complete games, and upserts them.
    # 4. Once all lines are processed (typically <1 second),
    #    `_parse_stream()` returns and `_stream_channel()` continues
    #    to the next channel.

    # Big Picture
    # ------------
    # • Even though the actual games last minutes in real life,
    #   we are only pulling quick, moment-in-time snapshots.
    # • That’s why we can sweep through ~16 channels and ingest hundreds
    #   of games in under 30 seconds.
    # • Note: Some games may be **incomplete** (still in progress);
    #   we insert them anyway, and later snapshots automatically update
    #   the same rows when new data arrives.

    # -------------------------------------------------------------------
    # What happens next (inside the loop):
    # -------------------------------------------------------------------
    #
    # • Read the response **one line at a time** (`resp.iter_lines()`).
    #
    # • Gradually **accumulate lines** into a temporary `pgn_block` list —
    #   each block will hold the full PGN text for **one game** (headers + moves).
    #
    # • Watch for the first move line ("1. ..."):
    #     → When we see it, it means the current PGN block is complete.
    #     → At that moment, call `_process_game_block(pgn_block, added, updated)`:
    #         - Parse the complete PGN block into structured metadata.
    #         - Upsert (insert or update) the game in the database.
    #         - Track whether it was newly added or updated.
    #
    # • Then **clear** the pgn_block and start buffering the next game (temporarily holding
    # incoming lines until a full game is ready).
    #
    # ➔ In short:
    #   - Read line → accumulate → detect full game → process → reset → repeat.
    #   - Keep building up `added` and `updated` lists to track results.

    pgn_block: list[bytes] = []

    # Create an empty list `pgn_block` to temporarily store the PGN lines for a single game.
    # Each "block" of PGN describes one complete chess game — headers + moves.
    #
    # Type hint: list[bytes] means it's a list where each item is a raw line of bytes (not strings yet).
    # We keep the raw bytes until needed because the Lichess API streams data line-by-line.

    for raw in resp.iter_lines():
        # --- TINY INCREMENTAL WAIT ---
        # Might pause for a few milliseconds if lines haven't fully arrived yet.
        # (Streaming responses allow immediate reading, but slight network buffering can occur.)

        # Loop over each line of the HTTP response.
        #
        # `iter_lines()` reads the response *one line at a time*,
        # instead of downloading the full payload into memory at once.
        #
        # ➔ Each `raw` is one line of PGN data (in bytes), ready to decode.

        if not raw:
            continue

            # Skip empty lines.
            #
            # Blank lines can appear naturally between PGN blocks or inside the payload.
            # They don't carry any game data, so we simply ignore them.

        line = raw.decode().strip()

        # Convert the raw bytes into a regular text string using UTF-8 decoding.
        #
        # Computers don’t store text directly — they store **bytes** (numbers).
        # UTF-8 is a standard set of rules that explains how to turn those bytes into real letters and symbols.
        #
        # The server sends the PGN data as bytes.
        # `.decode()` uses UTF-8 rules to "translate" the bytes back into readable text (like "1. e4 e5").
        #
        # After decoding, we call strip() to clean up any extra spaces or invisible characters.
        #
        # Then call strip() to remove any extra spaces, tabs, or invisible characters
        # from the beginning and end of the line.

        LOGGER.debug("PGN %s", line)

        # Log the decoded line at DEBUG level (very detailed, low-priority messages for troubleshooting).
        #
        # "%s" is a placeholder that gets replaced by `line`.
        # (This style lets the logger delay building the final string until needed — slightly more efficient.)
        #
        # Note: DEBUG logs won't actually show up unless the logging level is set to DEBUG mode.

        pgn_block.append(raw)

        # ── Why we decode but still store raw bytes ──────────────────────────────
        #
        # • Earlier, we decoded `raw` into `line` (text) only for two lightweight reasons:
        #     – To detect the start of the moves (`line.startswith("1. ")`),
        #       which signals that the header is complete and a full game is ready.
        #     – To log readable lines for debugging (`LOGGER.debug("PGN %s", line)`).
        #
        # • However, when **storing** the game data for later parsing,
        #   we deliberately keep the original `raw` bytes — *not* the decoded `line`.
        #
        #   – By keeping the raw bytes:
        #       • We **delegate responsibility** for decoding *and* error handling
        #         to the official PGN parser — the component specifically built
        #         to handle these edge cases safely.

        # ── Buffering strategy ─────────────────────────────────────────────────
        # • We accumulate lines in `pgn_block` until we see the first move
        #   ("1. e4 e5", etc.).  At that point the header is complete, so the
        #   whole game is ready to parse and upsert.
        # • This is short-lived *buffering* (discarded after each game),
        #   not long-term caching.

        if line.startswith("1. "):
            # If this line starts with "1. ", it's the first move of the game.
            # Since we already buffered all the header lines (and just added this move line),
            # we now have the **full PGN block** (headers + moves) ready to process.

            _process_game_block(pgn_block, added, updated)

            # Call the helper `_process_game_block` to parse the collected PGN block,
            # transform it into structured data, and insert or update it in the database.

            pgn_block.clear()

            # After processing this game, clear the `pgn_block` list
            # so the **next iteration** of the loop can start buffering a new game.
            #
            # (This is NOT the end of the function — we're still looping through the response lines.)


# ──────────────────────────────────────────────────────────────────────────
#   Main ingestion loop
# ──────────────────────────────────────────────────────────────────────────


def run_tv_ingestion() -> None:
    """Top-level loop that keeps polling every TV channel until we run out of time."""

    # ------------------------------------------------------------------
    # What this function does
    # ------------------------------------------------------------------
    #
    # • Starts a stopwatch (`start = time.time()`).
    # • While that stopwatch is under TIME_LIMIT seconds:
    #       1. Create fresh `added` / `updated` lists for batch stats.
    #       2. For each channel in CHANNELS:
    #            – Call _stream_channel(), which:
    #                 » Grabs a *snapshot* (not a live feed) of up-to-date games.
    #                 » Hands the response to _parse_stream() for immediate upsert.
    #       3. Log how many games we inserted / updated in this sweep.
    #       4. If the running total ≥ MAX_GAMES, pause RATE_LIMIT_PAUSE seconds,
    #          then reset the counter so we don’t hammer the API.
    #       5. Sleep SLEEP_INTERVAL seconds before the next sweep.
    #
    # • The loop exits cleanly when either:
    #       – CLOCK: total wall-time ≥ TIME_LIMIT,   or
    #       – (indirectly) the Python process is asked to stop.

    start = time.time()

    # Record the current time when the ingestion starts (in seconds since the **Unix epoch**).
    #
    # ➔ The "epoch" means January 1, 1970, 00:00:00 UTC — the universal reference point for all timestamps.
    #
    # `time.time()` returns a large floating-point number (e.g., 1714331771.492),
    # which represents the total number of seconds that have passed since that moment.
    #
    # We'll later compare this to the current time to measure how long the script has been running.

    total = 0

    # Initialize a counter to keep track of how many games we have ingested so far in this session.

    while time.time() - start < TIME_LIMIT:
        # Keep looping as long as the amount of time passed since `start`
        # is less than the allowed TIME_LIMIT (e.g., 30 seconds, 300 seconds, etc.).

        added, updated = [], []

        # For each loop (batch), reset the `added` and `updated` lists to empty.
        #
        # These lists will temporarily store the IDs of games added or updated during this batch.
        # We reset them each time to keep clean batch-level statistics.

        for ch in CHANNELS:
            # Loop over each TV channel in the predefined CHANNELS list.
            # (bullet, blitz, classical, rapid, chess960, etc.)
            # We will fetch and process games separately for each channel during this batch.

            LOGGER.info("Fetching channel '%s'…", ch)

            # Log an INFO-level message showing which channel we are about to fetch games from.

            _stream_channel(ch, added, updated)

            # Call the helper function `_stream_channel` to:

            # - Connect to the Lichess API for this specific channel.
            # - Stream live games.
            # - Parse each complete game and insert or update it into the database.
            #
            # As games are processed, the `added` and `updated` lists are populated
            # with the IDs of inserted and updated games.

        LOGGER.info("Batch done – %d added, %d updated", len(added), len(updated))

        # After fetching all channels in this batch, log how many games were added and updated in total.
        #
        # len(added) → number of games we inserted
        # len(updated) → number of games we updated (already existed)

        total += len(added) + len(updated)

        # Add the number of games processed in this batch to the running total.
        # (total keeps counting across all batches in this run.)

        if total >= MAX_GAMES:
            # If we have ingested too many games (reached the MAX_GAMES limit):

            LOGGER.info(
                "Reached %d games → cooling‑off for %d s", MAX_GAMES, RATE_LIMIT_PAUSE
            )

            # Log a message saying we've hit the maximum and will pause.

            time.sleep(RATE_LIMIT_PAUSE)

            # Sleep for RATE_LIMIT_PAUSE seconds (e.g., 900 seconds = 15 minutes)
            # to respect the server and avoid being rate-limited.

            total = 0

            # After the pause, reset the total counter back to 0
            # to start counting the next round of games fresh.

        LOGGER.info("Sleeping %d s before next batch…", SLEEP_INTERVAL)

        # If we haven't hit MAX_GAMES, still pause briefly between batches
        # to avoid hammering the API and give breathing room between rounds.

        time.sleep(SLEEP_INTERVAL)

        # Sleep for SLEEP_INTERVAL seconds (e.g., 5 seconds) before starting the next batch.

    LOGGER.info("TIME_LIMIT (%s s) reached – stopping ingestion", TIME_LIMIT)

    # Once the overall time limit is exceeded, exit the while-loop
    # and log that the ingestion session is complete.


# ──────────────────────────────────────────────────────────────────────────
# ️  CLI entry‑point
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # This is the standard Python way to say:
    # "Only run the code below if this file is being executed directly — not when it is imported."
    #
    # - `__name__` is a special built-in Python variable.
    #
    # This protects the script:
    # - Importing the file does nothing (no side effects like starting ingestion).
    # - Ingestion only starts when *something else chooses to call* `run_tv_ingestion()`.

    run_tv_ingestion()

    # Manually start the ingestion process by calling the main function.
    # This launches the full ingestion loop: connect to Lichess TV, fetch games, store in the database.
