import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from repositories.account_repository import AccountRepository
from models.access_level import AccessLevel

repo = AccountRepository()

try:
    repo.get_account_by_name("InitialAdmin")
except ValueError:
    repo.create_account(
        "InitialAdmin",
        "AIDDI",
        AccessLevel.ADMIN,
    )
    print("Created admin account")
else:
    print("Admin already exists")
