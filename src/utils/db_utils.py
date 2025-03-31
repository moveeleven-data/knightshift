import os
import json

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


# Load env vars from file
load_dotenv()

def load_db_credentials(
    secret_name=os.getenv("DB_SECRET_NAME", "LichessDBCreds"),
    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-2"),
):
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        print("Failed to load secret from AWS:", e)
        raise e

    creds = json.loads(response["SecretString"])

    # Optionally override inside Docker
    if creds["PGHOST"] == "host.docker.internal" and os.getenv("RUNNING_IN_DOCKER"):
        print("Inside Docker, overriding PGHOST to IP")
        creds["PGHOST"] = "192.168.65.254"

    return creds


def get_database_url(creds):
    return (
        f"postgresql+pg8000://{creds['PGUSER']}:{creds['PGPASSWORD']}"
        f"@{creds['PGHOST']}:{creds.get('PGPORT', '5432')}/{creds['PGDATABASE']}"
    )


def get_lichess_token():
    return os.getenv("LICHESS_TOKEN")
