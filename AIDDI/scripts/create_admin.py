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
