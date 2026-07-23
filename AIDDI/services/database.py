import os
from dataclasses import dataclass
from urllib.parse import quote_plus

from dotenv import load_dotenv
import psycopg
from psycopg import Connection


load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    url: str


def _build_url_from_parts() -> str:
    name = os.getenv("POSTGRES_DB", "").strip()
    user = os.getenv("POSTGRES_USER", "").strip()
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "localhost").strip()
    port = os.getenv("POSTGRES_PORT", "5432").strip()

    missing = [
        key
        for key, value in {
            "POSTGRES_DB": name,
            "POSTGRES_USER": user,
            "POSTGRES_PASSWORD": password,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Missing PostgreSQL configuration: "
            + ", ".join(missing)
            + ". Add these values to .env or set DATABASE_URL."
        )

    return (
        "postgresql://"
        f"{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{quote_plus(name)}"
    )


def get_database_config() -> DatabaseConfig:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        database_url = _build_url_from_parts()
    return DatabaseConfig(url=database_url)


def connect() -> Connection:
    return psycopg.connect(get_database_config().url)


def check_connection() -> bool:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)