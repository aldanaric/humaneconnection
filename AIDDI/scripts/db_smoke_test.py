import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.database import check_connection


def main() -> None:
    try:
        connected = check_connection()
    except Exception as exc:
        raise SystemExit(f"PostgreSQL connection failed: {exc}") from exc

    if connected:
        print("PostgreSQL connection successful.")


if __name__ == "__main__":
    main()