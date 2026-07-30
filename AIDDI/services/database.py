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


def _get_config_value(key: str, default: str = "") -> str:
    value = os.getenv(key)
    if value is not None:
        return value

    try:
        import streamlit as st

        secret_value = st.secrets.get(key, default)
    except Exception:
        secret_value = default

    return str(secret_value)


def _build_url_from_parts() -> str:
    name = _get_config_value("POSTGRES_DB").strip()
    user = _get_config_value("POSTGRES_USER").strip()
    password = _get_config_value("POSTGRES_PASSWORD")
    host = _get_config_value("POSTGRES_HOST", "localhost").strip()
    port = _get_config_value("POSTGRES_PORT", "5432").strip()

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
    database_url = _get_config_value("DATABASE_URL").strip()
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
