import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.database import connect


MIGRATIONS_DIR = PROJECT_ROOT / "database" / "migrations"


def ensure_migrations_table(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )


def applied_versions(cursor) -> set[str]:
    cursor.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cursor.fetchall()}


def migration_version(path: Path) -> str:
    return path.stem.split("_", 1)[0]


def main() -> None:
    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migrations:
        raise SystemExit(f"No migrations found in {MIGRATIONS_DIR}")

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
            ensure_migrations_table(cursor)
            applied = applied_versions(cursor)

            for path in migrations:
                version = migration_version(path)
                if version in applied:
                    print(f"Skipping migration {path.name}; already applied.")
                    continue

                print(f"Applying migration {path.name}...")
                cursor.execute(path.read_text(encoding="utf-8"))
                cursor.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (version,),
                )
                print(f"Applied migration {path.name}.")

            conn.commit()

    print("Database migrations complete.")


if __name__ == "__main__":
    main()
