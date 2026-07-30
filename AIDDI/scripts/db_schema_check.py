import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.database import connect


REQUIRED_TABLES = {
    "accounts",
    "profiles",
    "profile_documents",
    "observations",
    "growth_plans",
    "knowledge_base_sources",
    "knowledge_base_index_runs",
    "knowledge_base_index_errors",
    "teams",
    "team_members",
    "team_diagnostic_reports",
    "schema_migrations",
}


def main() -> None:
    try:
        conn = connect()
    except Exception as exc:
        raise SystemExit(
            "Could not connect to PostgreSQL. Start the database with "
            "`docker compose up -d postgres`, then run this command again.\n"
            f"Connection error: {exc}"
        ) from exc

    with conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            existing = {row[0] for row in cursor.fetchall()}

    missing = sorted(REQUIRED_TABLES - existing)
    if missing:
        raise SystemExit(
            "Database schema is missing required table(s): "
            + ", ".join(missing)
            + ". Run `uv run python scripts/db_migrate.py`."
        )

    print("Database schema check successful.")


if __name__ == "__main__":
    main()
