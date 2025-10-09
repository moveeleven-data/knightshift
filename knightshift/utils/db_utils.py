# ==============================================================================
# db_utils.py  –  Tiny helper for DB and secret lookups
#
# Centralizes:
#   • Postgres connection info
#   • AWS Secrets Manager plumbing
#   • Lichess API token retrieval
# ==============================================================================

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ROOT_ENV, override=False)  # env values override file

_SECRET_NAME: str = os.getenv("DB_SECRET_NAME", "LichessDBCreds")
_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-2")
_DOCKER_MODE: bool = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"


# ------------------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------------------


def _bool_env(var_name: str, default: str = "false") -> bool:
    """Convert TRUE / true / 1 style env vars to bool."""
    return os.getenv(var_name, default).strip().lower() in {"1", "true", "yes"}


# ------------------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------------------


def load_db_credentials(
    secret_name: str = _SECRET_NAME,
    region_name: str = _REGION,
) -> Dict[str, str]:
    """
    Fetch Postgres credentials JSON from AWS Secrets Manager.

    Notes
    -----
    • If running in Docker Compose (*RUNNING_IN_DOCKER=true*),
      override ``PGHOST`` with ``db`` to point at the Postgres service.
    """
    client = boto3.session.Session().client("secretsmanager", region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        creds: Dict[str, str] = json.loads(response["SecretString"])
    except ClientError as exc:
        raise RuntimeError(f"Failed to load secret `{secret_name}`") from exc

    if _DOCKER_MODE:
        creds["PGHOST"] = "db"  # must match service name in docker-compose.yml

    return creds


def get_database_url(creds: Dict[str, str]) -> str:
    """
    Build a SQLAlchemy psycopg2 connection URL from credentials.

    Example
    -------
    postgresql+psycopg2://user:password@localhost:5432/knightshift
    """
    return (
        "postgresql+psycopg2://{PGUSER}:{PGPASSWORD}" "@{PGHOST}:{PGPORT}/{PGDATABASE}"
    ).format(
        PGUSER=creds["PGUSER"],
        PGPASSWORD=creds["PGPASSWORD"],  # pragma: allowlist secret
        PGHOST=creds.get("PGHOST", "localhost"),
        PGPORT=creds.get("PGPORT", "5432"),
        PGDATABASE=creds["PGDATABASE"],
    )


def get_lichess_token() -> Optional[str]:
    """Return the bearer token for Lichess API calls (or None)."""
    return os.getenv("LICHESS_TOKEN")
